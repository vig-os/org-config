"""Unmanaged-controls assertion table: live controls otterdog cannot model.

Several org- and repo-level GitHub controls have no field in the otterdog schema
— Actions SHA-pinning, the fork-PR approval policy, the new-repository security
defaults, the secret-scanning extras — so they are invisible to the plan AND to
the inventory sweep: they can be flipped in the UI and nothing notices. This
module loads a declarative table of those controls (``unmanaged-controls.toml``,
governance state edited through the normal PR flow like ``drift-allowlist.toml``)
so the drift run can assert each one directly against the live REST API
(issue #116).

Pure core (ADR-0007 L1): loading, endpoint templating and field selection are
offline; the evaluation leg takes an injected client and never opens a socket of
its own. Each row addresses its field with a **dotted key path** into the decoded
JSON, deliberately not a jq expression — jq would be a runtime dependency this
stdlib-only, ``uvx``-light tool does not have (ADR-0005). Two segment forms reach
into JSON *lists* (issue #205), because the controls that matter most live there:
``rules[type=required_status_checks]`` selects the one element carrying a field,
and ``required_status_checks[].context`` projects a field out of every element,
which a row then asserts as an unordered set with ``compare = "set"``. Both
degrade rather than guess — see :func:`select_path`.

Row identity is the TOML ``key`` (plus the scope), never the live value, so the
fingerprint of a finding is stable across runs and the reconciler's
update-not-duplicate lifecycle works unchanged (ADR-0002).

PER-ROW DEGRADATION (the load-bearing design point). ``reconcile()`` closes
every open issue whose fingerprint is absent from the records it is given, so a
row that could not be READ must not be reported clean — that would
phantom-resolve a genuine open finding on a transient 403. :class:`ControlsResult`
therefore separates *clean* from *unresolved* fingerprints: the CLI withholds the
unresolved rows' issues from the reconcile input, so one unreadable row degrades
only itself while every other row still reconciles. That is strictly better than
the inventory sweep's all-or-nothing ``None``, and it is possible only because a
row's fingerprint is derivable from the table without reading the API at all.
"""

from __future__ import annotations

import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .github_client import ApiError, GitHubClient
from .inventory import extract_declared_org_secrets
from .models import DriftRecord

# Namespaced fingerprint prefix — a sibling of the plan's block headers and the
# sweep's ``repository-inventory:``, so all three populations share one dedup
# keyspace without ever colliding (see DriftRecord.fingerprint).
RESOURCE_PREFIX = "unmanaged-control"

_ORG_SCOPE = "org"
_REPO_SCOPE = "repo"
_SCOPES = (_ORG_SCOPE, _REPO_SCOPE)

ASSERT_KIND = "assert"
UNASSERTABLE_KIND = "unassertable"

# How a row's live value is compared with its declared one. ``exact`` is the
# literal comparison every row used before #205; ``set`` compares two lists
# order- and duplicate-insensitively, for live collections GitHub returns in no
# guaranteed order (a ruleset's required status checks).
COMPARE_EXACT = "exact"
COMPARE_SET = "set"
_COMPARE_MODES = (COMPARE_EXACT, COMPARE_SET)

# Per-row verdicts, reported by `--controls-report` and the workflow summary.
OK = "OK"
TOLERATED = "TOLERATED"
DRIFT = "DRIFT"
UNRESOLVED = "UNRESOLVED"
SKIPPED = "SKIPPED"

# Every unmanaged-control finding is a `drift`+`critical` issue; the change type
# names how it was found, distinct from the plan's add/change/forced/delete.
CHANGE_TYPE = "assert-failed"


class _Sentinel:
    """Distinguishable stand-in for "no value" (``None``/``False`` are data)."""

    def __init__(self, label: str) -> None:
        self._label = label

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return self._label


# "The row declares no such value" — an absent `expect`/`tolerated`. Distinct
# from MISSING below and from a declared `false`, which is a real assertion.
UNSET = _Sentinel("<unset>")

# "The live response has no such field" — a 200 whose schema does not carry the
# asserted path. Never equal to any declared literal, so it can only degrade.
MISSING = _Sentinel("<missing>")


@dataclass(frozen=True)
class Control:
    """One directly-asserted live control: where to read it and what to expect.

    ``expect`` is the desired value and ``tolerated`` an optional second accepted
    value for a known, tracked divergence — so the table records what SHOULD be
    true even where reality is currently allowed to differ, and the row goes
    green by itself once the divergence is fixed. Any third value is drift.

    ``compare = "set"`` makes both declared values unordered sets rather than
    literals: GitHub returns a ruleset's required status checks in no guaranteed
    order, so an exact comparison would report drift every time the UI
    reshuffled them.
    """

    key: str
    scope: str
    title: str
    endpoint: str = ""
    path: str = ""
    expect: object = UNSET
    repository: str | None = None
    tolerated: object = UNSET
    compare: str = COMPARE_EXACT
    kind: str = ASSERT_KIND
    reason: str = ""
    refs: tuple[str, ...] = ()
    recheck: str = ""

    @property
    def has_tolerated(self) -> bool:
        """Whether the row declares a tolerated (known-divergence) value."""
        return self.tolerated is not UNSET

    @property
    def assertable(self) -> bool:
        """Whether the row is evaluated at all (``kind = "unassertable"`` is not)."""
        return self.kind == ASSERT_KIND


@dataclass(frozen=True)
class OrgSecretsPolicy:
    """Switches for the generated org-secret assertion families.

    Unlike a ``[[control]]`` row these expectations are not literals in the
    table: they are derived from the committed otterdog config at run time, so
    the config stays the single source of truth for who may read which secret.
    """

    enabled: bool = False
    assert_visibility: bool = True
    assert_selected_repositories: bool = True
    assert_no_undeclared: bool = True
    reason: str = ""


@dataclass(frozen=True)
class ControlsConfig:
    """The whole parsed table: explicit rows plus the generated families."""

    controls: list[Control]
    org_secrets: OrgSecretsPolicy | None = None


@dataclass(frozen=True)
class ControlOutcome:
    """One row's verdict, for the report table and the run summary."""

    key: str
    scope: str  # "org" or the repository name
    status: str
    expected: str = ""
    actual: str = ""


@dataclass(frozen=True)
class ControlsResult:
    """What the assertion leg found, split by what the reconciler may act on.

    ``records`` are the rows that failed and must open/refresh an issue;
    ``clean_fingerprints`` the rows that were read and passed, whose issues may
    be closed; ``unresolved_fingerprints`` the rows that could not be read at
    all, whose issues must be left exactly as they are.
    """

    records: list[DriftRecord] = field(default_factory=list)
    clean_fingerprints: set[str] = field(default_factory=set)
    unresolved_fingerprints: set[str] = field(default_factory=set)
    notes: list[str] = field(default_factory=list)
    outcomes: list[ControlOutcome] = field(default_factory=list)


def load_controls(path: str | Path | None) -> ControlsConfig:
    """Load the assertion table from a TOML file.

    A missing/None path yields an empty config, so the leg is simply skipped
    where no table is committed (``load_allowlist`` precedent). Rows that could
    not be evaluated as written — no ``key``, an unknown ``scope``, a
    repo-scoped row naming no ``repository``, or an assertable row missing its
    ``endpoint``/``path``/``expect`` — are dropped rather than half-asserted: a
    malformed row must never manufacture a security finding.
    """
    if path is None:
        return ControlsConfig(controls=[])
    p = Path(path)
    if not p.exists():
        return ControlsConfig(controls=[])
    data = tomllib.loads(p.read_text())

    controls: list[Control] = []
    for raw in data.get("control", []):
        control = _parse_control(raw)
        if control is not None:
            controls.append(control)

    org_secrets = _parse_org_secrets(data.get("org_secrets"))
    return ControlsConfig(controls=controls, org_secrets=org_secrets)


def control_resource(control: Control) -> str:
    """Namespaced fingerprint resource for a control row.

    ``unmanaged-control:org:<key>`` at org scope, ``unmanaged-control:<repo>:<key>``
    at repo scope — so the same control asserted at both scopes stays two
    distinct findings with two distinct issues.
    """
    scope = control.repository if control.scope == _REPO_SCOPE else _ORG_SCOPE
    return f"{RESOURCE_PREFIX}:{scope}:{control.key}"


def resolve_endpoint(control: Control, *, org: str) -> str:
    """Fill the ``{org}``/``{repo}`` placeholders of a row's endpoint."""
    return control.endpoint.format(org=org, repo=control.repository or "")


def control_fingerprint(control: Control, *, org: str) -> str:
    """The row's issue fingerprint, derivable WITHOUT reading the live API.

    This is what makes per-row degradation possible: the CLI can identify the
    open issue belonging to an unreadable row and withhold it from reconcile.
    """
    return DriftRecord(
        org=org, resource=control_resource(control), change_type=CHANGE_TYPE, detail=""
    ).fingerprint


_MATCH = "match"
_PROJECT = "project"


@dataclass(frozen=True)
class _Segment:
    """One parsed path step: a key, optionally with a list operator."""

    key: str
    op: str = ""
    match_key: str = ""
    match_value: str = ""


def select_path(document: object, path: str) -> object:
    """Read a path out of a decoded JSON document.

    Three segment forms, all jq-free (ADR-0005):

    ``key``
        Descend into a mapping, as every row did before #205.
    ``key[field=literal]``
        Descend into a **list** and select the one element whose ``field``
        equals ``literal`` — how GitHub keys the members of a collection
        (a ruleset's ``rules`` by ``type``, a ruleset by ``name``).
    ``key[]``
        Project the remaining path over every element of a list, yielding a
        list of the values — how a set-valued row normalises
        ``required_status_checks`` to bare contexts.

    An empty key applies the operator to the document itself, for the endpoints
    that answer with a list at the root (``/repos/{o}/{r}/rules/branches/main``).

    Returns :data:`MISSING` for anything the path does not address **uniquely**:
    an absent segment, a walk through a non-mapping, a malformed path, a match
    with zero or several hits, a projection over a non-list, and a projection
    that any single element cannot satisfy. Never a guess — two rulesets can
    contribute a rule of the same type to one branch, and picking either would
    fabricate or hide a security finding, while a partial projection would
    compare as a shorter set and read as drift or, worse, as clean.

    ``False`` and ``None`` are returned verbatim: they are legitimate live
    values, and conflating either with absence would turn a schema change into a
    fabricated drift finding.
    """
    segments = _parse_path(path)
    if segments is None:
        return MISSING
    return _walk(document, segments)


def _parse_path(path: str) -> tuple[_Segment, ...] | None:
    """Parse a path into segments, or ``None`` if it is malformed."""
    raws = _split_outside_brackets(path)
    if raws is None:
        return None
    segments = []
    for raw in raws:
        segment = _parse_segment(raw)
        if segment is None:
            return None
        segments.append(segment)
    return tuple(segments)


def _split_outside_brackets(path: str) -> list[str] | None:
    """Split on ``.``, but never inside brackets.

    Status-check contexts are free text — ``CodeQL Analysis (python)``,
    ``build.test`` — so a naive ``path.split(".")`` would tear a match literal
    in half and silently address something else.
    """
    if not path:
        return None
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for char in path:
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth < 0:
                return None
        elif char == "." and depth == 0:
            parts.append("".join(current))
            current = []
            continue
        current.append(char)
    if depth != 0:
        return None
    parts.append("".join(current))
    return parts


def _parse_segment(raw: str) -> _Segment | None:
    open_at = raw.find("[")
    if open_at < 0:
        return _Segment(key=raw) if raw and "]" not in raw else None
    if not raw.endswith("]"):
        return None
    key, inner = raw[:open_at], raw[open_at + 1 : -1]
    if "[" in inner or "]" in inner:
        return None
    if not inner:
        return _Segment(key=key, op=_PROJECT)
    match_key, separator, match_value = inner.partition("=")
    if not separator or not match_key:
        return None
    return _Segment(key=key, op=_MATCH, match_key=match_key, match_value=match_value)


def _walk(current: object, segments: tuple[_Segment, ...]) -> object:
    for index, segment in enumerate(segments):
        if segment.key:
            if not isinstance(current, dict) or segment.key not in current:
                return MISSING
            current = current[segment.key]
        if segment.op == _MATCH:
            current = _unique_match(current, segment)
            if current is MISSING:
                return MISSING
        elif segment.op == _PROJECT:
            return _project(current, segments[index + 1 :])
    return current


def _unique_match(current: object, segment: _Segment) -> object:
    if not isinstance(current, list):
        return MISSING
    matches = [
        element
        for element in current
        if isinstance(element, dict)
        and _matches_literal(element.get(segment.match_key), segment.match_value)
    ]
    return matches[0] if len(matches) == 1 else MISSING


def _matches_literal(value: object, literal: str) -> bool:
    """Match a path literal against a live **string** only.

    Coercing would make ``[id=1]`` match a live ``true`` — the same conflation
    :func:`_equal` refuses on the value side.
    """
    return isinstance(value, str) and value == literal


def _project(current: object, rest: tuple[_Segment, ...]) -> object:
    if not isinstance(current, list):
        return MISSING
    projected = []
    for element in current:
        value = _walk(element, rest)
        if value is MISSING:
            return MISSING  # all-or-nothing; see select_path
        projected.append(value)
    return projected


def _as_comparable_set(value: object) -> frozenset[tuple[str, object]] | None:
    """Normalise a list of primitives into an order-insensitive set.

    Elements are tagged by type so the set keeps :func:`_equal`'s discipline:
    ``true`` and ``1`` are different members, never the same one. Returns
    ``None`` — "not comparable as a set" — for a non-list, or for a list holding
    anything a row cannot have declared in TOML as a bare value (a dict, most
    often a row that forgot its ``[].context`` projection).
    """
    if not isinstance(value, list):
        return None
    items: set[tuple[str, object]] = set()
    for element in value:
        tagged = _tag(element)
        if tagged is None:
            return None
        items.add(tagged)
    return frozenset(items)


def _tag(element: object) -> tuple[str, object] | None:
    if isinstance(element, bool):
        return ("bool", element)
    if isinstance(element, int | float):
        return ("number", element)
    if isinstance(element, str):
        return ("str", element)
    return None


@dataclass(frozen=True)
class _SecretFamily:
    """One generated org-secret assertion: its switch, identity and comparison."""

    switch: str
    subject: str
    intro: str
    control: Control
    compare: Callable[[dict, dict, GitHubClient, str], list[str]]


def evaluate_controls(
    config: ControlsConfig,
    client: GitHubClient,
    *,
    org: str,
    config_jsonnet_text: str | None = None,
) -> ControlsResult:
    """Assert every row of the table against live state through ``client``.

    Responses are memoized per resolved endpoint, so the six rows reading
    ``GET /orgs/{org}`` cost one request. Each row lands in exactly one bucket:
    matched (clean), matched the tolerated value (clean plus a note), diverged
    (a drift record), or unreadable (unresolved plus a note — never a record and
    never clean; see the module docstring). ``unassertable`` rows are documented
    in the notes and never touch the client.

    The generated org-secret families run last and only when the policy is
    enabled AND the committed config text is available: their expectations come
    from the jsonnet, not from literals in the table, so the config stays the
    single source of truth for who may read which secret.
    """
    result = ControlsResult()
    cache: dict[str, object | ApiError] = {}

    for control in config.controls:
        if not control.assertable:
            why = control.reason or "no readable endpoint"
            recheck = f" (recheck {control.recheck})" if control.recheck else ""
            result.notes.append(f"{control.key}: unassertable by design — {why}{recheck}")
            result.outcomes.append(
                ControlOutcome(key=control.key, scope=_scope_label(control), status=SKIPPED)
            )
            continue
        _evaluate_control(control, client, org=org, cache=cache, result=result)

    policy = config.org_secrets
    if policy is not None and policy.enabled and config_jsonnet_text is not None:
        _evaluate_org_secrets(
            policy, client, org=org, jsonnet_text=config_jsonnet_text, result=result
        )

    return result


def _evaluate_control(
    control: Control,
    client: GitHubClient,
    *,
    org: str,
    cache: dict[str, object | ApiError],
    result: ControlsResult,
) -> None:
    endpoint = resolve_endpoint(control, org=org)
    fingerprint = control_fingerprint(control, org=org)
    scope = _scope_label(control)
    as_set = control.compare == COMPARE_SET
    expected = _render(control.expect, as_set=as_set)

    if endpoint not in cache:
        try:
            cache[endpoint] = client.get_json(endpoint)
        except ApiError as exc:
            cache[endpoint] = exc
    document = cache[endpoint]

    if isinstance(document, ApiError):
        result.unresolved_fingerprints.add(fingerprint)
        result.notes.append(f"{control.key}: {_degradation_note(document, endpoint)}")
        result.outcomes.append(
            ControlOutcome(
                key=control.key,
                scope=scope,
                status=UNRESOLVED,
                expected=expected,
                actual=f"HTTP {document.status}" if document.status else "no response",
            )
        )
        return

    actual = select_path(document, control.path)
    if actual is MISSING:
        # A 200 whose schema no longer carries the path: GitHub moved the field.
        # Reporting that as drift would fabricate a security finding.
        result.unresolved_fingerprints.add(fingerprint)
        result.notes.append(
            f"{control.key}: field `{control.path}` absent from {endpoint} — schema moved; "
            f"update the row rather than trusting this reading"
        )
        result.outcomes.append(
            ControlOutcome(
                key=control.key, scope=scope, status=UNRESOLVED, expected=expected, actual="absent"
            )
        )
        return

    if as_set:
        live = _as_comparable_set(actual)
        if live is None:
            # The path resolved, but not to something a set can be built from:
            # the row is addressing raw objects (a forgotten `[].context`) or the
            # field stopped being a list. Comparing either would report a
            # permanent false drift, so the row degrades and says which.
            result.unresolved_fingerprints.add(fingerprint)
            result.notes.append(
                f"{control.key}: `{control.path}` on {endpoint} is not a list of comparable "
                f'values — a `compare = "set"` row needs a projection such as `[].context`'
            )
            result.outcomes.append(
                ControlOutcome(
                    key=control.key,
                    scope=scope,
                    status=UNRESOLVED,
                    expected=expected,
                    actual="not a set",
                )
            )
            return
        matches_expect = live == _as_comparable_set(control.expect)
        matches_tolerated = control.has_tolerated and live == _as_comparable_set(control.tolerated)
    else:
        matches_expect = _equal(actual, control.expect)
        matches_tolerated = control.has_tolerated and _equal(actual, control.tolerated)

    rendered = _render(actual, as_set=as_set)
    if matches_expect:
        result.clean_fingerprints.add(fingerprint)
        result.outcomes.append(
            ControlOutcome(
                key=control.key, scope=scope, status=OK, expected=expected, actual=rendered
            )
        )
        return

    if matches_tolerated:
        # Known, tracked divergence: clean (no issue), but never silent.
        result.clean_fingerprints.add(fingerprint)
        result.notes.append(
            f"{control.key}: tolerated divergence — live `{rendered}`, desired `{expected}`"
            + (f" ({', '.join(control.refs)})" if control.refs else "")
        )
        result.outcomes.append(
            ControlOutcome(
                key=control.key, scope=scope, status=TOLERATED, expected=expected, actual=rendered
            )
        )
        return

    result.records.append(_record(control, org=org, endpoint=endpoint, actual=actual))
    result.outcomes.append(
        ControlOutcome(
            key=control.key, scope=scope, status=DRIFT, expected=expected, actual=rendered
        )
    )


def _evaluate_org_secrets(
    policy: OrgSecretsPolicy,
    client: GitHubClient,
    *,
    org: str,
    jsonnet_text: str,
    result: ControlsResult,
) -> None:
    """Assert live org-secret metadata against the committed declarations.

    Otterdog cannot police these: nine of the ten committed secrets carry a
    ``'********'`` dummy value, so its plan skips them for live patching and a
    widened visibility or a hand-edited reader list never shows up as a diff.
    Each family yields at most ONE aggregate record whose body lists every
    offender — stable identity, volatile body, exactly what the reconciler's
    update-in-place lifecycle is built for.
    """
    declared = extract_declared_org_secrets(jsonnet_text)
    families = [f for f in _ORG_SECRET_FAMILIES if getattr(policy, f.switch)]
    if not families:
        return

    try:
        live_secrets = client.list_org_secrets(org)
    except ApiError as exc:
        for family in families:
            _degrade_family(
                family, org=org, note=f"org-secret list unreadable ({exc})", result=result
            )
        return

    live = {raw["name"]: raw for raw in live_secrets if isinstance(raw, dict) and raw.get("name")}
    for family in families:
        try:
            offenders = family.compare(declared, live, client, org)
        except ApiError as exc:
            _degrade_family(
                family, org=org, note=f"{family.subject} unreadable ({exc})", result=result
            )
            continue
        _report_family(family, offenders, org=org, reason=policy.reason, result=result)


def _degrade_family(family: _SecretFamily, *, org: str, note: str, result: ControlsResult) -> None:
    result.unresolved_fingerprints.add(control_fingerprint(family.control, org=org))
    result.notes.append(f"{family.control.key}: {note}")
    result.outcomes.append(
        ControlOutcome(
            key=family.control.key,
            scope=_ORG_SCOPE,
            status=UNRESOLVED,
            expected="as declared",
            actual="unreadable",
        )
    )


def _report_family(
    family: _SecretFamily,
    offenders: list[str],
    *,
    org: str,
    reason: str,
    result: ControlsResult,
) -> None:
    control = family.control
    if not offenders:
        result.clean_fingerprints.add(control_fingerprint(control, org=org))
        result.outcomes.append(
            ControlOutcome(
                key=control.key,
                scope=_ORG_SCOPE,
                status=OK,
                expected="as declared",
                actual="as declared",
            )
        )
        return

    detail = "\n".join([family.intro, "", *offenders] + (["", reason.strip()] if reason else []))
    result.records.append(
        DriftRecord(
            org=org,
            resource=control_resource(control),
            change_type=CHANGE_TYPE,
            detail=detail,
            title_override=f"Unmanaged control drift: {control.title}",
        )
    )
    result.outcomes.append(
        ControlOutcome(
            key=control.key,
            scope=_ORG_SCOPE,
            status=DRIFT,
            expected="as declared",
            actual=f"{len(offenders)} divergence(s)",
        )
    )


def _compare_visibility(
    declared: dict[str, object], live: dict[str, dict], client: GitHubClient, org: str
) -> list[str]:
    offenders = []
    for name, secret in sorted(declared.items()):
        if name not in live:
            continue  # a missing secret is otterdog's own add/delete diff
        actual = live[name].get("visibility")
        if actual != secret.live_visibility:
            offenders.append(f"- {name}: declared `{secret.live_visibility}`, live `{actual}`")
    return offenders


def _compare_selected_repositories(
    declared: dict[str, object], live: dict[str, dict], client: GitHubClient, org: str
) -> list[str]:
    offenders = []
    for name, secret in sorted(declared.items()):
        if name not in live or live[name].get("visibility") != "selected":
            continue  # only a `selected` secret HAS a reader list to compare
        actual = set(client.list_org_secret_repositories(org, name))
        wanted = set(secret.selected_repositories)
        extra = sorted(actual - wanted)
        absent = sorted(wanted - actual)
        if extra or absent:
            offenders.append(f"- {name}: live-only {extra or '[]'}, config-only {absent or '[]'}")
    return offenders


def _compare_undeclared(
    declared: dict[str, object], live: dict[str, dict], client: GitHubClient, org: str
) -> list[str]:
    return [f"- {name}" for name in sorted(set(live) - set(declared))]


def _family_control(key: str, title: str) -> Control:
    """A synthetic row so a generated family shares the table's identity rules."""
    return Control(key=key, scope=_ORG_SCOPE, title=title)


_ORG_SECRET_FAMILIES: tuple[_SecretFamily, ...] = (
    _SecretFamily(
        switch="assert_visibility",
        subject="org-secret visibility",
        intro=(
            "Live org-secret visibility diverges from the committed declaration. "
            "A widened visibility hands the credential to repositories nobody "
            "reviewed for it."
        ),
        control=_family_control(
            "org-secret-visibility", "org-secret visibility diverges from the committed config"
        ),
        compare=_compare_visibility,
    ),
    _SecretFamily(
        switch="assert_selected_repositories",
        subject="org-secret reader lists",
        intro=(
            "The repositories a `selected` org secret is shared with diverge from "
            "the committed list. A live-only entry is an unreviewed reader; a "
            "config-only entry is a consumer whose workflows now resolve the "
            "secret to an empty string, with no error."
        ),
        control=_family_control(
            "org-secret-repositories",
            "org-secret reader lists diverge from the committed config",
        ),
        compare=_compare_selected_repositories,
    ),
    _SecretFamily(
        switch="assert_no_undeclared",
        subject="org-secret inventory",
        intro=(
            "Live org secrets with no committed declaration. Each is an "
            "unreviewed credential: nothing records who created it, what reads "
            "it, or when it should be rotated."
        ),
        control=_family_control(
            "org-secret-undeclared", "undeclared org secrets exist in the live organization"
        ),
        compare=_compare_undeclared,
    ),
)


def _record(control: Control, *, org: str, endpoint: str, actual: object) -> DriftRecord:
    return DriftRecord(
        org=org,
        resource=control_resource(control),
        change_type=CHANGE_TYPE,
        detail=_control_detail(control, endpoint=endpoint, actual=actual),
        title_override=f"Unmanaged control drift: {control.title}",
    )


def _control_detail(control: Control, *, endpoint: str, actual: object) -> str:
    as_set = control.compare == COMPARE_SET
    lines = [
        f"endpoint:  GET {endpoint}",
        f"path:      {control.path}",
        f"expected:  {_render(control.expect, as_set=as_set)}",
    ]
    if control.has_tolerated:
        lines.append(f"tolerated: {_render(control.tolerated, as_set=as_set)}")
    lines.append(f"actual:    {_render(actual, as_set=as_set)}")
    if as_set:
        # A dropped required check and an unexpected extra one are different
        # incidents; naming which is which saves the triager a re-read.
        live = _as_comparable_set(actual) or frozenset()
        wanted = _as_comparable_set(control.expect) or frozenset()
        lines.append(f"missing:    {_render_members(wanted - live)}")
        lines.append(f"unexpected: {_render_members(live - wanted)}")
    if control.reason:
        lines += ["", control.reason.strip()]
    if control.refs:
        lines += ["", f"refs: {', '.join(control.refs)}"]
    return "\n".join(lines)


def _degradation_note(error: ApiError, endpoint: str) -> str:
    if error.status == 404:
        return f"endpoint unassertable — {endpoint} returned 404"
    if error.status in (401, 403):
        return f"unreadable (token scope) — {endpoint} returned {error.status}"
    if error.status == 0:
        return f"unreadable — {endpoint} gave no answer ({error})"
    return f"unreadable — {endpoint} returned {error.status}"


def _scope_label(control: Control) -> str:
    return control.repository if control.scope == _REPO_SCOPE else _ORG_SCOPE


def _equal(actual: object, expected: object) -> bool:
    """Strict literal comparison: ``1`` is not ``true``, ``"1"`` is not ``1``."""
    if isinstance(actual, bool) != isinstance(expected, bool):
        return False
    return actual == expected


def _render(value: object, *, as_set: bool = False) -> str:
    if value is MISSING or value is UNSET:
        return "absent"
    if as_set and isinstance(value, list):
        return repr(sorted(value, key=_sort_key))
    return repr(value)


def _render_members(members: frozenset[tuple[str, object]]) -> str:
    return repr(sorted((value for _, value in members), key=_sort_key))


def _sort_key(element: object) -> tuple[str, str]:
    """Total order over mixed primitives, so rendering never raises."""
    return (type(element).__name__, str(element))


def _parse_control(raw: object) -> Control | None:
    if not isinstance(raw, dict):
        return None
    key = raw.get("key")
    scope = raw.get("scope")
    if not key or scope not in _SCOPES:
        return None
    repository = raw.get("repository")
    if scope == _REPO_SCOPE and not repository:
        return None

    kind = raw.get("kind", ASSERT_KIND)
    endpoint = raw.get("endpoint", "")
    field_path = raw.get("path", "")
    expect = raw.get("expect", UNSET)
    tolerated = raw.get("tolerated", UNSET)
    compare = raw.get("compare", COMPARE_EXACT)
    if compare not in _COMPARE_MODES:
        return None
    if kind == ASSERT_KIND:
        if not endpoint or not field_path or expect is UNSET:
            return None
        if _parse_path(field_path) is None:
            return None
        if compare == COMPARE_SET:
            # A declared value that cannot be a set would make the row assert
            # something that can never pass — drop it rather than ship it.
            if _as_comparable_set(expect) is None:
                return None
            if tolerated is not UNSET and _as_comparable_set(tolerated) is None:
                return None

    return Control(
        key=key,
        scope=scope,
        title=raw.get("title") or key,
        endpoint=endpoint,
        path=field_path,
        expect=expect,
        repository=repository if scope == _REPO_SCOPE else None,
        tolerated=tolerated,
        compare=compare,
        kind=kind,
        reason=raw.get("reason", ""),
        refs=tuple(raw.get("refs", ())),
        recheck=raw.get("recheck", ""),
    )


def _parse_org_secrets(raw: object) -> OrgSecretsPolicy | None:
    if not isinstance(raw, dict):
        return None
    return OrgSecretsPolicy(
        enabled=bool(raw.get("enabled", False)),
        assert_visibility=bool(raw.get("assert_visibility", True)),
        assert_selected_repositories=bool(raw.get("assert_selected_repositories", True)),
        assert_no_undeclared=bool(raw.get("assert_no_undeclared", True)),
        reason=raw.get("reason", ""),
    )
