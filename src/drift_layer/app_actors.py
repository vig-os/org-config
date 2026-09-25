"""Plan-time App-slug checks: ask the engine's token what otterdog will ask (#259).

`plan` is this repository's L2 review gate, and for one class of change it is
green on config `apply` cannot write. Otterdog's READ path never calls
``GET /apps/{slug}`` — it maps a live ``actor_id`` back to a slug from
``GET /orgs/{org}/installations`` (``models/github_organization.py:555-558``,
``:755-765``) — so the plan renders an App actor correctly and the failure
surfaces only on the live, mutating `apply` (#256).

The check has no false positives and needs no new credential: for every
App-shaped actor in the EVALUATED config, make the call `apply` will make, with
the credential `apply` will use, at review time.

    GET /apps/{slug}   Authorization: Bearer <the plan job's installation token>
      200        -> apply can write this actor
      403 / 404  -> apply WILL fail on any add or change of that resource
      403 + rate-limit headers -> the limiter refused, not the resource;
                                  the check could not be made; NOT a finding
      anything else -> the check could not be made; NOT a finding

The cheaper predicate — "the actor is an App *and* is not already live" — is
falsified by this org's own config: ten App bypass actors across ten rulesets
apply fine because both Apps are public, and a ruleset patch re-sends the WHOLE
bypass list (``models/repo_ruleset.py:63-71`` ->
``models/ruleset.py:635-652``), so an already-live unreadable App 403s on the
next change too.

Four write-path sites, three of them fatal
------------------------------------------
``grep -rn get_app_ids`` over otterdog 1.5.0 (the ADR-0005 pin) returns four
consumers of ``GET /apps/{app_slug}``. They do not fail the same way, so the
report does not present them the same way:

===================================  ==========================================
``models/ruleset.py:649``            ruleset ``bypass_actors`` — ``RuntimeError``,
                                     the patch fails (the #256 case)
``models/ruleset.py:177-189``        ruleset ``required_status_checks`` —
                                     ``RuntimeError``, the patch fails
``models/branch_protection_rule.py:348``  branch-protection status checks —
                                     ``RuntimeError``, the patch fails
``models/environment.py:244``        environment ``reviewers`` — **caught and
                                     skipped** (``providers/github/__init__.py:502-506``)
===================================  ==========================================

The fourth is worse than the reported bug: `apply` SUCCEEDS with the App
reviewer silently dropped, leaving a protection that was never written and a
permanent phantom plan diff.

Each site's actor grammar is transcribed from that code, escapes included, so
the check fires on exactly what otterdog would look up:

- **ruleset bypass actor** — ``#role`` / ``@team`` are resolved elsewhere;
  anything else is an App, with a ``:bypass_mode`` suffix split off first. There
  is **no** ``isdigit()`` escape here, so a numeric actor is a slug lookup too
  (``models/ruleset.py:626-649``).
- **ruleset status check** — only an entry containing ``:`` whose prefix is not
  ``any``, contains no space and is not all digits (``models/ruleset.py:181-185``;
  the digits branch is upstream #695, and it is NOT shared with bypass actors).
- **branch-protection status check** — an entry containing ``:`` contributes its
  prefix unless it is ``any``, *numeric prefixes included*; an entry with no
  ``:`` contributes the IMPLICIT ``github-actions``
  (``models/branch_protection_rule.py:339-348``). This is the site where the
  ruleset's numeric form is a 404 rather than an escape.
- **environment reviewer** — ``@name`` is a user, ``@org/team`` a team, anything
  else an App (``providers/github/__init__.py:487-506``). No ``:`` suffix.

Second, independent class: declared but not installed
-----------------------------------------------------
The write path is only half of it. On the READ path otterdog maps a live App
actor back to a slug through ONE source — ``GET /orgs/{org}/installations``
(``models/github_organization.py:555-558``, ``:761-777``) — so a declared App
that is not an installation on that org can never read back as written:

- a ruleset **bypass actor** is dropped outright (``models/ruleset.py:541-548``
  logs *"fail to map integration actor"* and ``continue``s, with no numeric
  fallback), so `plan` proposes to add it on every run and `apply` never
  converges;
- a ruleset **status check** degrades to its numeric ``<id>:context`` form
  (``models/ruleset.py:145-151``), which is the same permanent phantom diff by a
  different mechanism — this repo learned it as #69 / #130-#141.

That check is INDEPENDENT of the ``/apps/`` one, not an ``elif``: a slug can be
readable and uninstalled, or installed and unreadable, and each has its own
consequence.

It is deliberately NOT applied to the other two sites. A branch-protection
status check with no prefix resolves to the implicit ``github-actions``, which is
a first-party App and never an org installation — this org's own config declares
it (tessera's two rules) and plans clean, so asking for an installation there
would fire on green config, which is the exact failure mode #256 rejected. The
environment-reviewer read path was not traced, so nothing is claimed about it.

Scope, said out loud: both classes read the **declared** config. A bypass actor
that exists LIVE but is not declared is a standing unreported bypass, and
catching it needs a live ruleset read (which a Free-plan private repo refuses
anyway) — it is not covered here.

Purity (ADR-0007 L1): extraction is a pure function over the evaluated document
and never touches the network. The document itself is produced token-free —
`plan.yml` evaluates the committed jsonnet with otterdog's own
``jsonnet_evaluate_file``, the exact call ``GitHubOrganization.load_from_file``
makes (``models/github_organization.py:536``) — so the only credentialed step is
the ``/apps/`` read itself.

Known and suppressed
--------------------
A slug can be unresolvable **by design**: a private App owned by a sibling org,
on a ruleset that is already live and correct and cannot be repaired until
upstream `eclipse-csi/otterdog#772` lands. Reported as a finding on every pull
request that would be a permanent red banner nobody can act on — the standing
noise that trains a reviewer to wave plans through, which is the failure #262
names. A ``[[app_actor]]`` entry in ``drift-allowlist.toml`` (slug + reason)
moves such a slug out of the findings and into a *known, suppressed* table that
still names it and prints the reason, so the suppression is visible and
reviewable rather than silent — the same governance shape as ``[[expected]]``
and ``[[unmanaged]]``.

Advisory, never fatal: the finding belongs in the plan report and the job
summary, never in an exit code. Every entry point here returns a report; the CLI
mode exits 0 unconditionally, including when the check could not be made at all.
That is not a claim that nothing downstream depends on this job: `Plan` is not a
required check *in this repository* (ADR-0007 Axis D, #236), but the only
consumer org makes its plan context a required check on `main` (#268), so every
step this module is wired into must be fail-soft.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import quote

from .github_client import ApiError, GitHubClient, TruncatedResponseError

SITE_RULESET_BYPASS_ACTOR = "ruleset-bypass-actor"
SITE_RULESET_STATUS_CHECK = "ruleset-status-check"
SITE_BRANCH_PROTECTION_STATUS_CHECK = "branch-protection-status-check"
SITE_ENVIRONMENT_REVIEWER = "environment-reviewer"

STATE_RESOLVED = "resolved"
STATE_UNRESOLVABLE = "unresolvable"
STATE_UNDETERMINED = "undetermined"

# The two statuses that answer the question asked. Everything else — 401 (the
# credential itself is bad), 0 (no answer at all), 5xx, or a truncated 200 —
# means the check could not be made, which is reported as such and never as a
# finding: a false "apply will fail" costs more than a missing one (#258/#264).
#
# With ONE exception inside 403, and it is the likeliest one: GitHub answers 403
# both for "Resource not accessible by integration" (the #256 true positive) and
# for rate-limit exhaustion, with the same `Forbidden` reason phrase — and the
# step that runs immediately before this check is a full org read on the same
# token, which is the single most likely way to arrive at the limit. Only the
# response headers separate them, so a 403 carrying `retry-after` or
# `x-ratelimit-remaining: 0` is classified UNDETERMINED by the rule above
# rather than rendered as "apply WILL fail on these".
_UNRESOLVABLE_STATUSES = frozenset({403, 404})


@dataclass(frozen=True)
class Site:
    """One otterdog field that resolves an App slug, and how it fails."""

    key: str
    label: str
    #: Whether an unresolvable slug aborts the patch, or is silently dropped.
    fails_apply: bool
    #: Where in otterdog 1.5.0 the write-path lookup happens.
    source: str
    #: Whether the READ path needs the App to be an org installation. False
    #: where a non-installed App is the correct, plan-clean spelling (the
    #: implicit `github-actions` of a branch-protection check) or where the
    #: read path was not traced.
    read_needs_installation: bool = False


SITES: dict[str, Site] = {
    SITE_RULESET_BYPASS_ACTOR: Site(
        key=SITE_RULESET_BYPASS_ACTOR,
        label="ruleset bypass actor",
        fails_apply=True,
        source="models/ruleset.py:649",
        read_needs_installation=True,
    ),
    SITE_RULESET_STATUS_CHECK: Site(
        key=SITE_RULESET_STATUS_CHECK,
        label="ruleset required status check",
        fails_apply=True,
        source="models/ruleset.py:177-189",
        read_needs_installation=True,
    ),
    SITE_BRANCH_PROTECTION_STATUS_CHECK: Site(
        key=SITE_BRANCH_PROTECTION_STATUS_CHECK,
        label="branch-protection required status check",
        fails_apply=True,
        source="models/branch_protection_rule.py:348",
    ),
    SITE_ENVIRONMENT_REVIEWER: Site(
        key=SITE_ENVIRONMENT_REVIEWER,
        label="environment reviewer",
        fails_apply=False,
        source="models/environment.py:244",
    ),
}


@dataclass(frozen=True, order=True)
class ActorSite:
    """One declared App slug at one place in the evaluated config."""

    slug: str
    site: str
    #: ``None`` for an org-level ruleset — it belongs to no repository.
    repo: str | None
    #: Ruleset name, environment name, or branch-protection pattern.
    resource: str

    @property
    def fails_apply(self) -> bool:
        return SITES[self.site].fails_apply

    @property
    def read_needs_installation(self) -> bool:
        return SITES[self.site].read_needs_installation

    def where(self) -> str:
        """Human location, e.g. ``alpha`` ruleset ``Main protection``."""
        scope = f"`{self.repo}`" if self.repo else "org-level"
        return f"{scope} {SITES[self.site].label} `{self.resource}`"


@dataclass(frozen=True)
class Installations:
    """The org's App installations — otterdog's only id->slug source on read."""

    #: Case-folded ``app_slug`` values.
    slugs: frozenset[str]
    #: Whether the whole list was read. A partial list must never be compared
    #: against: every absent slug would read as "not installed".
    complete: bool
    detail: str = ""


@dataclass(frozen=True)
class SlugOutcome:
    """What the engine's own credential answered for one slug."""

    slug: str
    state: str
    #: HTTP status, or ``None`` when the request never got an answer.
    status: int | None
    detail: str
    sites: tuple[ActorSite, ...]
    #: Whether the slug is an installation on the org — ``None`` when it was not
    #: checked (no site needs it) or could not be (the list was not read whole).
    installed: bool | None = None
    #: The ``[[app_actor]]`` allow-list reason, when this slug is a documented
    #: known-unresolvable one. ``None`` means it is not allow-listed.
    allowlisted_reason: str | None = None

    @property
    def is_finding(self) -> bool:
        """Whether this outcome is a finding rather than known and accepted."""
        return (self.state == STATE_UNRESOLVABLE or self.installed is False) and (
            self.allowlisted_reason is None
        )


@dataclass(frozen=True)
class AppSlugReport:
    org: str
    outcomes: tuple[SlugOutcome, ...]
    #: Degradation notes — reads that could not be completed, or not attempted.
    notes: tuple[str, ...] = ()
    installations: Installations | None = None

    @property
    def unresolvable(self) -> tuple[SlugOutcome, ...]:
        """Slugs `apply` cannot write — allow-listed ones excluded."""
        return tuple(
            o
            for o in self.outcomes
            if o.state == STATE_UNRESOLVABLE and o.allowlisted_reason is None
        )

    @property
    def undetermined(self) -> tuple[SlugOutcome, ...]:
        return tuple(o for o in self.outcomes if o.state == STATE_UNDETERMINED)

    @property
    def not_installed(self) -> tuple[SlugOutcome, ...]:
        """Declared slugs the org has no installation for (the #262 class)."""
        return tuple(
            o for o in self.outcomes if o.installed is False and o.allowlisted_reason is None
        )

    @property
    def suppressed(self) -> tuple[SlugOutcome, ...]:
        """Findings an ``[[app_actor]]`` entry documents as known (#259).

        Reported, with the reason, under their own heading — never folded into
        the clean case, because a suppression a reader cannot see is a silent
        one.
        """
        return tuple(
            o
            for o in self.outcomes
            if o.allowlisted_reason is not None
            and (o.state == STATE_UNRESOLVABLE or o.installed is False)
        )


# ---------------------------------------------------------------------------
# Extraction (pure)
# ---------------------------------------------------------------------------


def _items(container: object, key: str) -> list[dict]:
    """The list at ``key``, tolerating an absent key and an explicit ``null``."""
    if not isinstance(container, dict):
        return []
    value = container.get(key)
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _strings(container: object, key: str) -> list[str]:
    if not isinstance(container, dict):
        return []
    value = container.get(key)
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _bypass_actor_slug(actor: str) -> str | None:
    """The App slug a ruleset bypass actor resolves to, or ``None``.

    ``models/ruleset.py:626-649``: ``#`` is a repository role and ``@`` a team;
    anything else is an App, with a ``:bypass_mode`` suffix split off first.
    Deliberately no ``isdigit()`` escape — this site has none, so a numeric
    actor is looked up as a slug and 404s.
    """
    if actor.startswith(("#", "@")):
        return None
    slug = actor.split(":", 1)[0]
    return slug or None


def _ruleset_status_check_slug(check: str) -> str | None:
    """The App slug a RULESET status check resolves to, or ``None``.

    ``models/ruleset.py:181-185``: a prefix is looked up only when it exists and
    is not ``any``, contains no space, and is not all digits (the numeric form is
    upstream #695's escape and the canonical spelling in this repo, #69).
    """
    if ":" not in check:
        return None
    prefix = check.split(":", 1)[0]
    if prefix == "any" or " " in prefix or prefix.isdigit():
        return None
    return prefix or None


def _branch_protection_status_check_slug(check: str) -> str | None:
    """The App slug a BRANCH-PROTECTION status check resolves to, or ``None``.

    ``models/branch_protection_rule.py:339-348``: no ``:`` means the implicit
    ``github-actions``; a prefix is looked up unless it is ``any``, with **no**
    numeric escape — which is why a ruleset's ``15368:`` spelling 404s here.
    """
    if ":" not in check:
        return "github-actions"
    prefix = check.split(":", 1)[0]
    return None if prefix == "any" else (prefix or None)


def _environment_reviewer_slug(reviewer: str) -> str | None:
    """The App slug an environment reviewer resolves to, or ``None``.

    ``providers/github/__init__.py:487-506``: ``@name`` is a user, ``@org/team``
    a team, anything else an App. No ``:bypass_mode`` grammar on this field.
    """
    return None if reviewer.startswith("@") else (reviewer or None)


def _ruleset_sites(ruleset: dict, repo: str | None) -> list[ActorSite]:
    name = str(ruleset.get("name", ""))
    sites: list[ActorSite] = []
    for actor in _strings(ruleset, "bypass_actors"):
        slug = _bypass_actor_slug(actor)
        if slug:
            sites.append(ActorSite(slug, SITE_RULESET_BYPASS_ACTOR, repo, name))
    for check in _strings(ruleset.get("required_status_checks"), "status_checks"):
        slug = _ruleset_status_check_slug(check)
        if slug:
            sites.append(ActorSite(slug, SITE_RULESET_STATUS_CHECK, repo, name))
    return sites


def extract_app_actor_sites(config: object) -> list[ActorSite]:
    """Every App-shaped actor in an evaluated otterdog org document.

    Pure: takes the document otterdog's own evaluator produces and returns the
    sites, deduplicated and deterministically ordered. Never reads a file,
    never calls out.
    """
    sites: list[ActorSite] = []
    for ruleset in _items(config, "rulesets"):
        sites.extend(_ruleset_sites(ruleset, None))

    for repo in _items(config, "repositories"):
        name = str(repo.get("name", ""))
        for ruleset in _items(repo, "rulesets"):
            sites.extend(_ruleset_sites(ruleset, name))
        for rule in _items(repo, "branch_protection_rules"):
            pattern = str(rule.get("pattern", ""))
            for check in _strings(rule, "required_status_checks"):
                slug = _branch_protection_status_check_slug(check)
                if slug:
                    sites.append(
                        ActorSite(slug, SITE_BRANCH_PROTECTION_STATUS_CHECK, name, pattern)
                    )
        for environment in _items(repo, "environments"):
            env_name = str(environment.get("name", ""))
            for reviewer in _strings(environment, "reviewers"):
                slug = _environment_reviewer_slug(reviewer)
                if slug:
                    sites.append(ActorSite(slug, SITE_ENVIRONMENT_REVIEWER, name, env_name))

    return sorted(set(sites))


# ---------------------------------------------------------------------------
# The check (one GET per unique slug)
# ---------------------------------------------------------------------------


def read_installations(client: GitHubClient, org: str) -> Installations:
    """Read the org's App installations, or say why the list is not usable.

    ``GET /orgs/{org}/installations`` is the sole id->slug source otterdog's
    read path has, and the engine's token reads it on every plan already, so
    this needs no new grant. One page of 100 via
    :meth:`RestGitHubClient.get_json`, which REFUSES a response advertising a
    further page (#258) — and ``total_count`` is compared as well, because a
    partial list would make every absent slug look uninstalled. otterdog's own
    read does NOT paginate here (``org_client.py:484-491`` uses the non-paged
    ``request_json``, which also sends no ``per_page``), so otterdog itself
    drops installations past GitHub's default page size of 30 — below this
    check's own 100, so between 31 and 100 it drops actors this check cannot
    predict and stays correct to say nothing (#269); that is reported, not
    mirrored.
    """
    try:
        document = client.get_json(f"/orgs/{quote(org, safe='')}/installations")
    except ApiError as exc:
        limited = rate_limit_reason(exc)
        detail = f"{exc} — {limited}" if limited else str(exc)
        return Installations(frozenset(), complete=False, detail=detail)
    if not isinstance(document, dict) or not isinstance(document.get("installations"), list):
        return Installations(
            frozenset(), complete=False, detail="the response carried no `installations` list"
        )
    entries = [entry for entry in document["installations"] if isinstance(entry, dict)]
    slugs = frozenset(
        str(entry["app_slug"]).casefold() for entry in entries if entry.get("app_slug")
    )
    total = document.get("total_count")
    if isinstance(total, int) and total > len(entries):
        return Installations(
            slugs,
            complete=False,
            detail=(
                f"`total_count` is {total} but only {len(entries)} installation(s) came back — "
                f"the list is partial, so absence from it proves nothing"
            ),
        )
    return Installations(slugs, complete=True)


def check_app_slugs(
    config: object,
    client: GitHubClient,
    *,
    org: str,
    allowlist: Mapping[str, str] | None = None,
) -> AppSlugReport:
    """Run both App-slug checks over the evaluated config.

    1. ``GET /apps/{slug}`` per UNIQUE slug — the answer is a property of the
       slug and the credential, not of the site, so one call covers every site
       that declares it, and every such site rides along on the outcome.
    2. Membership of ``GET /orgs/{org}/installations`` — one call for the whole
       org, and only for slugs declared at a site whose READ path needs it.

    The two are INDEPENDENT: a slug can fail either, both, or neither.

    ``allowlist`` maps a case-folded slug to the documented reason it is known to
    be unresolvable (``[[app_actor]]`` in ``drift-allowlist.toml``). Such a slug
    is still checked and still reported — under *known, suppressed*, with the
    reason — but is not a finding.
    """
    allowed = {slug.casefold(): reason for slug, reason in (allowlist or {}).items()}
    sites = extract_app_actor_sites(config)
    by_slug: dict[str, list[ActorSite]] = {}
    for site in sites:
        by_slug.setdefault(site.slug, []).append(site)

    notes: list[str] = []
    installations: Installations | None = None
    if any(site.read_needs_installation for site in sites):
        installations = read_installations(client, org)
        if not installations.complete:
            notes.append(f"could not verify org installations for `{org}`: {installations.detail}")

    outcomes: list[SlugOutcome] = []
    for slug, slug_sites in by_slug.items():
        state, status, detail = _resolve(client, slug)
        if state == STATE_UNDETERMINED:
            notes.append(f"could not resolve `{slug}`: {detail}")
        installed: bool | None = None
        if (
            installations is not None
            and installations.complete
            and any(site.read_needs_installation for site in slug_sites)
        ):
            installed = slug.casefold() in installations.slugs
        outcomes.append(
            SlugOutcome(
                slug=slug,
                state=state,
                status=status,
                detail=detail,
                sites=tuple(slug_sites),
                installed=installed,
                allowlisted_reason=allowed.get(slug.casefold()),
            )
        )
    return AppSlugReport(
        org=org, outcomes=tuple(outcomes), notes=tuple(notes), installations=installations
    )


def rate_limit_reason(exc: ApiError) -> str | None:
    """Why this refusal is the rate limiter rather than the resource, or ``None``.

    GitHub's primary limit answers ``403`` with ``x-ratelimit-remaining: 0`` and
    a secondary limit answers ``403`` with ``retry-after``; a permission refusal
    carries neither and its reason phrase is identical, so the headers are the
    only separator. Read from :attr:`ApiError.headers`, which the client carries
    for exactly this caller.
    """
    retry_after = exc.headers.get("retry-after")
    if retry_after:
        return f"a secondary rate limit (`retry-after: {retry_after}`)"
    if exc.headers.get("x-ratelimit-remaining") == "0":
        reset = exc.headers.get("x-ratelimit-reset")
        resets = f", resets at `{reset}`" if reset else ""
        return f"the primary rate limit (`x-ratelimit-remaining: 0`{resets})"
    return None


def _resolve(client: GitHubClient, slug: str) -> tuple[str, int | None, str]:
    """One ``GET /apps/{slug}`` classified into a state.

    The slug is percent-encoded: it comes from committed config, and a path
    segment assembled from config data is never pasted into a URL unescaped.
    """
    path = f"/apps/{quote(slug, safe='')}"
    try:
        client.get_json(path)
    except TruncatedResponseError as exc:
        # A 200 that answered only part of a collection. `/apps/{slug}` is a
        # single object and never paginates, so this means something upstream
        # changed shape — report it, never read it as a refusal.
        return STATE_UNDETERMINED, None, str(exc)
    except ApiError as exc:
        limited = rate_limit_reason(exc)
        if limited is not None:
            # The limiter refused, not the permission boundary. Reporting this
            # as "apply will fail on these" would be a false diagnosis of the
            # config, on the run most likely to produce it.
            return (
                STATE_UNDETERMINED,
                (exc.status or None),
                f"{exc} — {limited}, so this is the limiter refusing, not the slug",
            )
        if exc.status in _UNRESOLVABLE_STATUSES:
            return STATE_UNRESOLVABLE, exc.status, str(exc)
        return STATE_UNDETERMINED, (exc.status or None), str(exc)
    return STATE_RESOLVED, 200, ""


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

_HEADING = "### Declared App slugs"

_PREAMBLE = (
    "Two checks otterdog makes and `plan` does not, run with the token this "
    "run minted: `apply` writes every App-shaped actor by resolving its slug "
    "through `GET /apps/{slug}`, and otterdog's read path maps a live App "
    "actor back to a slug only through `GET /orgs/{org}/installations`. "
    "Neither is exercised by the plan above, so config that fails either is "
    "green on review ([#259](https://github.com/vig-os/org-config/issues/259)). "
    "Both checks read the **declared** config only — an actor that exists live "
    "but is not declared needs a live ruleset read and is not covered."
)


def _rows(sites: tuple[ActorSite, ...], outcome: SlugOutcome, *, fails_apply: bool) -> list[str]:
    return [
        f"| `{outcome.slug}` | `{outcome.status}` | {site.where()} |"
        for site in sites
        if site.fails_apply is fails_apply
    ]


def render_markdown(report: AppSlugReport) -> str:
    """The fragment folded into the plan comment and the job summary.

    Heading level `###` so it nests under the report's `## Otterdog plan` — and
    the two failure modes are never mixed into one table: three sites abort the
    patch, the fourth leaves `apply` green with the actor missing.
    """
    lines = [_HEADING, "", _PREAMBLE, ""]
    checked = len(report.outcomes)

    failing = [(o, _rows(o.sites, o, fails_apply=True)) for o in report.unresolvable]
    failing = [(o, rows) for o, rows in failing if rows]
    dropped = [(o, _rows(o.sites, o, fails_apply=False)) for o in report.unresolvable]
    dropped = [(o, rows) for o, rows in dropped if rows]

    installations_unread = report.installations is not None and not report.installations.complete

    if (
        not failing
        and not dropped
        and not report.undetermined
        and not report.not_installed
        and not report.suppressed
        and not installations_unread
    ):
        plural = "" if checked == 1 else "s"
        lines.append(
            f"All {checked} declared App slug{plural} resolved, and every one whose "
            f"read path needs it is installed on `{report.org}`. Nothing here blocks `apply`."
        )
        return "\n".join(lines) + "\n"

    if failing:
        lines += [
            "**`apply` will fail on these.** The patch raises "
            "`failed retrieving app node id` and the resource is not written — "
            "including on a later change to a resource that is already live, "
            "because a patch re-sends the whole list.",
            "",
            "| Slug | `GET /apps/{slug}` | Declared at |",
            "| --- | --- | --- |",
        ]
        for _, rows in failing:
            lines += rows
        lines.append("")

    if dropped:
        lines += [
            "**These are silently dropped.** `apply` SUCCEEDS with the actor "
            "missing (otterdog logs a warning and skips it), leaving a "
            "protection that was never written and a permanent phantom plan "
            "diff.",
            "",
            "| Slug | `GET /apps/{slug}` | Declared at |",
            "| --- | --- | --- |",
        ]
        for _, rows in dropped:
            lines += rows
        lines.append("")

    if report.not_installed:
        lines += [
            f"**Declared, but not installed on `{report.org}`.** otterdog resolves a "
            "live App actor back to a slug only through "
            "`GET /orgs/{org}/installations`, so a declaration naming an App the "
            "org has no installation for can never read back as written: a "
            "ruleset bypass actor is **dropped outright** on read, a ruleset "
            "status check reads back in its numeric `<id>:context` form. Either "
            "way `plan` proposes the same change on every run and `apply` never "
            "converges. Install the App on the organization, or change the "
            "declaration.",
            "",
            "| Slug | Declared at |",
            "| --- | --- |",
        ]
        for outcome in report.not_installed:
            lines += [
                f"| `{outcome.slug}` | {site.where()} |"
                for site in outcome.sites
                if site.read_needs_installation
            ]
        lines.append("")

    if report.suppressed:
        lines += [
            "**Known and suppressed.** Each of these is recorded in "
            "`drift-allowlist.toml` as unresolvable by design, so it is named "
            "here with its reason rather than reported as a finding. Removing "
            "the entry is how it becomes one again.",
            "",
            "| Slug | Why it is accepted | Declared at |",
            "| --- | --- | --- |",
        ]
        for outcome in report.suppressed:
            reason = outcome.allowlisted_reason or "no reason recorded"
            lines += [f"| `{outcome.slug}` | {reason} | {site.where()} |" for site in outcome.sites]
        lines.append("")

    if report.undetermined:
        lines += [
            "**Not a finding — these could not be checked.** The read failed "
            "for a reason other than the slug (a bad credential, a rate limit, "
            "an upstream error), so nothing is claimed about them.",
            "",
        ]
        lines += [f"- `{o.slug}`: {o.detail}" for o in report.undetermined]
        lines.append("")

    if installations_unread and report.installations is not None:
        lines += [
            "**Not a finding — the org's App installations could not be read** "
            f"({report.installations.detail}), so nothing is claimed here about "
            "which declared Apps are installed.",
            "",
        ]

    lines.append(f"_Checked {checked} declared App slug(s) for `{report.org}`._")
    return "\n".join(lines) + "\n"


def render_degraded_markdown(reason: str) -> str:
    """The fragment when the check itself could not run at all.

    Said out loud rather than swallowed: a silent omission reads exactly like a
    clean result, and this step must never fail the job to signal it.
    """
    return (
        f"{_HEADING}\n\n{_PREAMBLE}\n\n"
        f"**The declared App slugs could not be checked** on this run: "
        f"{reason}. This is a harness gap, not a verdict — treat the slugs as "
        f"unverified.\n"
    )


def render_json(report: AppSlugReport) -> dict:
    """The machine-readable twin of the fragment (plain JSON types only)."""
    return {
        "org": report.org,
        "checked": len(report.outcomes),
        "unresolvable": len(report.unresolvable),
        "undetermined": len(report.undetermined),
        "not_installed": len(report.not_installed),
        "suppressed": len(report.suppressed),
        "installations_read": (
            None if report.installations is None else report.installations.complete
        ),
        "notes": list(report.notes),
        "slugs": [
            {
                "slug": outcome.slug,
                "state": outcome.state,
                "status": outcome.status,
                "detail": outcome.detail,
                "installed": outcome.installed,
                "allowlisted_reason": outcome.allowlisted_reason,
                "sites": [
                    {
                        "site": site.site,
                        "repo": site.repo,
                        "resource": site.resource,
                        "fails_apply": site.fails_apply,
                        "read_needs_installation": site.read_needs_installation,
                    }
                    for site in outcome.sites
                ],
            }
            for outcome in report.outcomes
        ],
    }
