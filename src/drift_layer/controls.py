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
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

# Namespaced fingerprint prefix — a sibling of the plan's block headers and the
# sweep's ``repository-inventory:``, so all three populations share one dedup
# keyspace without ever colliding (see DriftRecord.fingerprint).
RESOURCE_PREFIX = "unmanaged-control"

_ORG_SCOPE = "org"
_REPO_SCOPE = "repo"
_SCOPES = (_ORG_SCOPE, _REPO_SCOPE)

ASSERT_KIND = "assert"
UNASSERTABLE_KIND = "unassertable"


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
