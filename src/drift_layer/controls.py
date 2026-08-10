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
stdlib-only, ``uvx``-light tool does not have (ADR-0005).

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
from dataclasses import dataclass, field
from pathlib import Path

from .github_client import ApiError, GitHubClient
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
    """

    key: str
    scope: str
    title: str
    endpoint: str = ""
    path: str = ""
    expect: object = UNSET
    repository: str | None = None
    tolerated: object = UNSET
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


def select_path(document: object, path: str) -> object:
    """Read a dotted key path out of a decoded JSON document.

    Returns :data:`MISSING` when any segment is absent or the walk hits a
    non-mapping — never a guess. ``False`` and ``None`` are returned verbatim:
    they are legitimate live values, and conflating either with absence would
    turn a schema change into a fabricated drift finding.
    """
    current = document
    for segment in path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return MISSING
        current = current[segment]
    return current


def evaluate_controls(
    config: ControlsConfig,
    client: GitHubClient,
    *,
    org: str,
) -> ControlsResult:
    """Assert every row of the table against live state through ``client``.

    Responses are memoized per resolved endpoint, so the six rows reading
    ``GET /orgs/{org}`` cost one request. Each row lands in exactly one bucket:
    matched (clean), matched the tolerated value (clean plus a note), diverged
    (a drift record), or unreadable (unresolved plus a note — never a record and
    never clean; see the module docstring). ``unassertable`` rows are documented
    in the notes and never touch the client.
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
    expected = _render(control.expect)

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

    rendered = _render(actual)
    if _equal(actual, control.expect):
        result.clean_fingerprints.add(fingerprint)
        result.outcomes.append(
            ControlOutcome(
                key=control.key, scope=scope, status=OK, expected=expected, actual=rendered
            )
        )
        return

    if control.has_tolerated and _equal(actual, control.tolerated):
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


def _record(control: Control, *, org: str, endpoint: str, actual: object) -> DriftRecord:
    return DriftRecord(
        org=org,
        resource=control_resource(control),
        change_type=CHANGE_TYPE,
        detail=_control_detail(control, endpoint=endpoint, actual=actual),
        title_override=f"Unmanaged control drift: {control.title}",
    )


def _control_detail(control: Control, *, endpoint: str, actual: object) -> str:
    lines = [
        f"endpoint:  GET {endpoint}",
        f"path:      {control.path}",
        f"expected:  {_render(control.expect)}",
    ]
    if control.has_tolerated:
        lines.append(f"tolerated: {_render(control.tolerated)}")
    lines.append(f"actual:    {_render(actual)}")
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


def _render(value: object) -> str:
    return "absent" if value is MISSING or value is UNSET else repr(value)


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
    if kind == ASSERT_KIND and (not endpoint or not field_path or expect is UNSET):
        return None

    return Control(
        key=key,
        scope=scope,
        title=raw.get("title") or key,
        endpoint=endpoint,
        path=field_path,
        expect=expect,
        repository=repository if scope == _REPO_SCOPE else None,
        tolerated=raw.get("tolerated", UNSET),
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
