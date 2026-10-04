"""Org-secret reader lists, declared vs live — shared by drift and plan (#318).

`otterdog apply` never live-patches an org secret whose committed value is a
``'********'`` dummy (``models/secret.py``: ``include_for_live_patch`` returns
``not self.has_dummy_secret()``), and nine of this org's ten org secrets are
dummies. So the ``selected_repositories`` list on such a secret is
documentation: adding a repository to it is green in review, plans clean, and
is never granted. The consumer's workflows then resolve the secret to an empty
string with no error. That happened to ``revkit`` (#312) and ``stepv`` (#317),
and nothing said so until the daily drift run opened an
``org-secret-repositories`` issue days later (#313).

ONE comparison, two callers. :func:`comparable_secrets` and
:func:`diff_secret_repositories` are the differ behind the drift layer's
``org-secret-repositories`` family (``controls.py``) — and this module's plan
report runs the very same functions at review time, in the same shape as the
#259 "Declared App slugs" section: read-only, with the token the plan job
already minted, reported in the plan comment and never in an exit code.

What "comparable" means is the drift family's rule, unchanged: a declared
secret that exists live with visibility ``selected``. A missing secret is
otterdog's own add diff; a live secret with another visibility has no reader
list to compare (the drift ``org-secret-visibility`` family owns that).

Token (verified for #318): ``GET /orgs/{org}/actions/secrets`` and
``GET /orgs/{org}/actions/secrets/{name}/repositories`` need the App's
*Organization → Secrets* read, which the org-management App holds (it writes
org secrets at apply) and which drift's controls leg already exercises with the
SAME full installation token `plan.yml` mints. A downstream org whose App lacks
it gets a 403 here, which degrades the section to "could not read", never a
finding and never a failed job.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .app_actors import rate_limit_reason
from .github_client import ApiError, GitHubClient
from .inventory import DeclaredOrgSecret, extract_declared_org_secrets

_SELECTED = "selected"


@dataclass(frozen=True)
class SecretRepositoriesDiff:
    """One ``selected`` org secret's reader list, declared vs live."""

    name: str
    #: Declared readers the live secret does not grant — a consumer whose
    #: workflows resolve the secret to an empty string.
    config_only: tuple[str, ...]
    #: Live readers nobody declared — an unreviewed reader.
    live_only: tuple[str, ...]
    #: Whether the committed value is a dummy, i.e. whether `apply` is blind to
    #: this secret entirely and the divergence needs a hand call to close.
    dummy_value: bool

    @property
    def diverges(self) -> bool:
        return bool(self.config_only or self.live_only)


def comparable_secrets(
    declared: Mapping[str, DeclaredOrgSecret], live: Mapping[str, Mapping]
) -> list[DeclaredOrgSecret]:
    """The declared secrets that HAVE a live reader list, in name order."""
    return [
        secret
        for name, secret in sorted(declared.items())
        if name in live and live[name].get("visibility") == _SELECTED
    ]


def diff_secret_repositories(
    client: GitHubClient, org: str, secret: DeclaredOrgSecret
) -> SecretRepositoriesDiff:
    """Read one secret's live reader list and split it from the declared one.

    Raises :class:`ApiError` when the list cannot be read — each caller decides
    its own degradation (drift withholds the whole family's issue; the plan
    report marks just this secret as not checked).
    """
    actual = set(client.list_org_secret_repositories(org, secret.name))
    wanted = set(secret.selected_repositories)
    return SecretRepositoriesDiff(
        name=secret.name,
        config_only=tuple(sorted(wanted - actual)),
        live_only=tuple(sorted(actual - wanted)),
        dummy_value=secret.dummy_value,
    )


# ---------------------------------------------------------------------------
# The plan-time check
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SecretRepositoriesReport:
    org: str
    compared: tuple[SecretRepositoriesDiff, ...] = ()
    #: ``(name, why)`` for a declared ``selected`` secret with no live list.
    not_compared: tuple[tuple[str, str], ...] = ()
    #: ``(name, detail)`` for a reader list that could not be read.
    undetermined: tuple[tuple[str, str], ...] = ()
    #: Why the org's secret list itself could not be read, else ``None``.
    unreadable: str | None = None

    @property
    def divergent(self) -> tuple[SecretRepositoriesDiff, ...]:
        return tuple(diff for diff in self.compared if diff.diverges)


def _describe(exc: ApiError) -> str:
    limited = rate_limit_reason(exc)
    return f"{exc} — {limited}" if limited else str(exc)


def check_reader_lists(
    jsonnet_text: str, client: GitHubClient, *, org: str
) -> SecretRepositoriesReport:
    """Compare every comparable declared secret's reader list against live."""
    declared = extract_declared_org_secrets(jsonnet_text)
    try:
        live_secrets = client.list_org_secrets(org)
    except ApiError as exc:
        return SecretRepositoriesReport(org=org, unreadable=_describe(exc))
    live = {raw["name"]: raw for raw in live_secrets if isinstance(raw, dict) and raw.get("name")}

    compared: list[SecretRepositoriesDiff] = []
    undetermined: list[tuple[str, str]] = []
    for secret in comparable_secrets(declared, live):
        try:
            compared.append(diff_secret_repositories(client, org, secret))
        except ApiError as exc:
            undetermined.append((secret.name, _describe(exc)))

    not_compared: list[tuple[str, str]] = []
    for name, secret in sorted(declared.items()):
        if secret.visibility != _SELECTED:
            continue
        if name not in live:
            not_compared.append((name, "not live yet — the plan above adds it"))
        elif live[name].get("visibility") != _SELECTED:
            not_compared.append((name, f"live visibility is `{live[name].get('visibility')}`"))

    return SecretRepositoriesReport(
        org=org,
        compared=tuple(compared),
        not_compared=tuple(not_compared),
        undetermined=tuple(undetermined),
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

_HEADING = "### Declared org-secret readers"

_PREAMBLE = (
    "Who may read each `selected` org secret, committed config vs live, read "
    "with the token this run minted. `plan` cannot show this: otterdog skips "
    "any org secret whose committed value is a `'********'` dummy for live "
    "patching, so `apply` **never writes the reader list** of such a secret — "
    "a repository added to it is green here and never granted, and its "
    "workflows read the secret as an empty string with no error "
    "([#318](https://github.com/vig-os/org-config/issues/318)). The same "
    "comparison runs daily as the drift layer's `org-secret-repositories` "
    "check."
)


def _put(org: str, name: str, repo: str, method: str) -> str:
    return (
        f'gh api -X {method} "/orgs/{org}/actions/secrets/{name}/repositories/'
        f'$(gh api /repos/{org}/{repo} --jq .id)"'
    )


def _who_fixes(diff: SecretRepositoriesDiff) -> str:
    if diff.dummy_value:
        return "**no** — dummy value, never live-patched: by hand, below"
    return "yes — `apply` reconciles a real-valued secret's list"


def _table(diffs: list[tuple[SecretRepositoriesDiff, str]]) -> list[str]:
    lines = ["| Secret | Repository | Does `apply` fix it? |", "| --- | --- | --- |"]
    lines += [f"| `{diff.name}` | `{repo}` | {_who_fixes(diff)} |" for diff, repo in diffs]
    return lines


def _commands(org: str, diffs: list[tuple[SecretRepositoriesDiff, str]], method: str) -> list[str]:
    manual = [(diff, repo) for diff, repo in diffs if diff.dummy_value]
    if not manual:
        return []
    return ["", "```sh", *(_put(org, d.name, repo, method) for d, repo in manual), "```"]


def render_markdown(report: SecretRepositoriesReport) -> str:
    """The fragment folded into the plan comment and the job summary."""
    # Every block below opens with its own blank separator line.
    lines = [_HEADING, "", _PREAMBLE]

    if report.unreadable is not None:
        lines += [
            "",
            f"**Not a finding — could not read the org secrets of `{report.org}`** "
            f"({report.unreadable}), so nothing is claimed here about their reader "
            "lists. This is a harness gap, not a verdict — treat them as unverified.",
        ]
        return "\n".join(lines) + "\n"

    checked = len(report.compared)
    granted = [(d, repo) for d in report.divergent for repo in d.config_only]
    extra = [(d, repo) for d in report.divergent for repo in d.live_only]

    if not granted and not extra and not report.undetermined:
        plural = "" if checked == 1 else "s"
        lines += [
            "",
            f"All {checked} `selected` org secret{plural} on `{report.org}` grant exactly "
            "the repositories the config declares. Nothing here needs a hand grant.",
        ]
    if granted:
        lines += [
            "",
            "**Declared, not granted live.** These repositories are in the committed "
            "`selected_repositories` but cannot read the secret. For a dummy-valued "
            "secret `apply` will **not** grant them — not on this merge, not on any "
            "later one — so an org owner runs the grant by hand. A repository this "
            "change also declares does not exist until `apply` creates it: grant it "
            "after that apply.",
            "",
            *_table(granted),
            *_commands(report.org, granted, "PUT"),
        ]
    if extra:
        lines += [
            "",
            "**Granted live, not declared.** These repositories can read the secret "
            "and no committed config says they should — an unreviewed reader. Declare "
            "them, or revoke the grant (`apply` will not revoke it for a dummy-valued "
            "secret either):",
            "",
            *_table(extra),
            *_commands(report.org, extra, "DELETE"),
        ]
    if report.undetermined:
        lines += [
            "",
            "**Not a finding — these reader lists could not be checked.** The read "
            "failed, so nothing is claimed about them.",
            "",
            *(f"- `{name}`: {detail}" for name, detail in report.undetermined),
        ]
    if report.not_compared:
        lines += [
            "",
            "Declared `selected` but not compared (no live reader list to read): "
            + "; ".join(f"`{name}` — {why}" for name, why in report.not_compared)
            + ".",
        ]

    lines += ["", f"_Checked {checked} `selected` org secret(s) for `{report.org}`._"]
    return "\n".join(lines) + "\n"


def render_degraded_markdown(reason: str) -> str:
    """The fragment when the check itself could not run at all."""
    return (
        f"{_HEADING}\n\n{_PREAMBLE}\n\n"
        f"**The org-secret reader lists could not be checked** on this run: "
        f"{reason}. This is a harness gap, not a verdict — treat them as "
        f"unverified.\n"
    )
