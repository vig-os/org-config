"""Inventory sweep: live org repos vs the declared otterdog config (issue #21).

Pure core (ADR-0007): no I/O. The CLI injects the live repo names (from the
GitHub client, ``GET /orgs/{org}/repos``) and the committed config text; this
module extracts the declared set and turns each divergence into a
:class:`DriftRecord` that feeds the SAME reconcile()/issue lifecycle as
settings drift (ADR-0002).

Declared-set extraction — why a literal read, not a jsonnet evaluation.
    The committed ``vig-os.jsonnet`` declares every repository with a literal
    ``orgs.newRepo('<name>')`` and fully overrides the base template's
    ``_repositories`` (``::``, not ``+::``), so repo *names* are never computed
    and nothing leaks in from the base template. A strict literal extraction is
    therefore provably equivalent to a full evaluation here — verified once
    against ``go-jsonnet`` (the dev-shell ``jsonnet``), which yields the exact
    same 16-name set (see ``tests/test_inventory``). Keeping it a pure, offline,
    stdlib-only read (no ``jsonnet``/otterdog subprocess) preserves the L1 pure
    core, stays testable against the real committed file, and avoids putting the
    native-lib-fragile jsonnet toolchain on the drift workflow's runtime path.
    A wrong declared set is worse than a slow one, so the extraction is
    deliberately strict (anchored on the ``newRepo`` constructor, comments
    stripped) and asserted against the known set in the test suite.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from .allowlist import load_unmanaged
from .models import DriftRecord

# `orgs.newRepo('<name>')` — the otterdog repository constructor. The `\(` right
# after `newRepo` is what distinguishes it from `newRepoRuleset(` /
# `newRepoSecret(` / `newRepoVariable(`, which share the `newRepo` prefix.
_NEW_REPO_RE = re.compile(r"\bnewRepo\(\s*'(?P<name>[^']+)'\s*\)")

# `orgs.newOrgSecret('<NAME>')` — the ORG secret constructor, deliberately not
# `newRepoSecret(`: repo-scoped secrets live inside repository blocks and belong
# to a different scope entirely (ten of them are committed today).
_NEW_ORG_SECRET_RE = re.compile(r"\bnewOrgSecret\(\s*'(?P<name>[^']+)'\s*\)")
_VISIBILITY_RE = re.compile(r"\bvisibility:\s*'(?P<value>[^']*)'")
_SELECTED_REPOS_RE = re.compile(r"\bselected_repositories\+?:\s*\[")
_QUOTED_RE = re.compile(r"'(?P<value>[^']*)'")

# Strip `//` line comments before matching so a commented-out example
# declaration can never inject a phantom declared repo.
_LINE_COMMENT_RE = re.compile(r"//.*$")

_UNDECLARED_PREFIX = "repository-inventory"
_MISSING_PREFIX = "repository-inventory-missing"

# The vendored `newOrgSecret` default (otterdog-defaults.libsonnet), so a
# declaration that omits `visibility` is read exactly as otterdog evaluates it.
_DEFAULT_VISIBILITY = "public"

# otterdog's schema says `public` where the REST API says `all`; the model does
# the same translation on both read and write (organization_secret.py).
_VISIBILITY_TO_LIVE = {"public": "all"}


def undeclared_resource(name: str) -> str:
    """Namespaced fingerprint resource for a live-but-undeclared repo."""
    return f"{_UNDECLARED_PREFIX}:{name}"


def missing_resource(name: str) -> str:
    """Namespaced fingerprint resource for a declared-but-absent repo."""
    return f"{_MISSING_PREFIX}:{name}"


def extract_declared_repos(jsonnet_text: str) -> set[str]:
    """Extract the declared repo names from committed otterdog config text.

    Strict literal read of every ``orgs.newRepo('<name>')`` constructor, with
    ``//`` line comments stripped first. See the module docstring for why this
    is faithful (and preferable to a jsonnet evaluation) for this config.
    """
    names: set[str] = set()
    for raw_line in jsonnet_text.splitlines():
        line = _LINE_COMMENT_RE.sub("", raw_line)
        names.update(m.group("name") for m in _NEW_REPO_RE.finditer(line))
    return names


@dataclass(frozen=True)
class DeclaredOrgSecret:
    """One committed ``orgs.newOrgSecret(...)`` declaration's live-visible half.

    Secret *values* are never comparable (the API does not return them and nine
    of the ten committed declarations carry a `'********'` dummy), so the
    declaration's assertable content is exactly who may read it.
    """

    name: str
    visibility: str = _DEFAULT_VISIBILITY
    selected_repositories: tuple[str, ...] = ()

    @property
    def live_visibility(self) -> str:
        """The declared visibility in the REST API's own vocabulary."""
        return _VISIBILITY_TO_LIVE.get(self.visibility, self.visibility)


def extract_declared_org_secrets(jsonnet_text: str) -> dict[str, DeclaredOrgSecret]:
    """Extract the declared org secrets from committed otterdog config text.

    Same strict-literal doctrine as :func:`extract_declared_repos` (see the
    module docstring), extended from ``newRepo`` to ``newOrgSecret``: comments
    are stripped first, each block is read from its constructor to its matching
    closing brace, and only literal ``visibility`` / ``selected_repositories``
    entries are taken. Faithful because the vendored ``newOrgSecret`` supplies
    plain literal defaults and nothing in the committed file computes either
    field, so the text IS the evaluated value — and ``jsonnetfmt --test`` is an
    L0 gate, so the block shape cannot drift underneath the reader.
    """
    secrets: dict[str, DeclaredOrgSecret] = {}
    name: str | None = None
    depth = 0
    visibility = _DEFAULT_VISIBILITY
    selected: list[str] = []
    in_list = False

    for raw_line in jsonnet_text.splitlines():
        line = _LINE_COMMENT_RE.sub("", raw_line)
        if name is None:
            match = _NEW_ORG_SECRET_RE.search(line)
            if match is None:
                continue
            name = match.group("name")
            visibility, selected, in_list = _DEFAULT_VISIBILITY, [], False
            depth = line.count("{") - line.count("}")
            if depth <= 0:  # `newOrgSecret('X') {}` on one line
                secrets[name] = DeclaredOrgSecret(name=name)
                name = None
            continue

        if in_list:
            selected.extend(m.group("value") for m in _QUOTED_RE.finditer(line))
            in_list = "]" not in line
        else:
            list_match = _SELECTED_REPOS_RE.search(line)
            if list_match is not None:
                tail = line[list_match.end() :]
                selected.extend(m.group("value") for m in _QUOTED_RE.finditer(tail))
                in_list = "]" not in tail
            else:
                visibility_match = _VISIBILITY_RE.search(line)
                if visibility_match is not None:
                    visibility = visibility_match.group("value")

        depth += line.count("{") - line.count("}")
        if depth <= 0:
            secrets[name] = DeclaredOrgSecret(
                name=name, visibility=visibility, selected_repositories=tuple(selected)
            )
            name = None

    return secrets


def sweep_inventory(
    org: str,
    *,
    declared: set[str],
    live: Iterable[str],
    unmanaged: set[str],
) -> list[DriftRecord]:
    """Compare live repos against the declared set into inventory drift records.

    - A live repo not declared (and not ``unmanaged``) -> an *undeclared* record.
    - A declared repo absent from live (and not ``unmanaged``) -> a *missing*
      record with a distinct title/fingerprint (creation is apply's job; silent
      absence is drift, ADR-0002).
    - ``unmanaged`` names (``managed: false`` allow-list) are out of declarative
      scope in both directions and never produce a record.
    """
    live_set = set(live)
    scoped = unmanaged

    undeclared = sorted((live_set - declared) - scoped)
    missing = sorted((declared - live_set) - scoped)

    records: list[DriftRecord] = []
    for name in undeclared:
        records.append(
            DriftRecord(
                org=org,
                resource=undeclared_resource(name),
                change_type="undeclared",
                detail=_undeclared_detail(org, name),
                title_override=f"Undeclared repository: {name}",
            )
        )
    for name in missing:
        records.append(
            DriftRecord(
                org=org,
                resource=missing_resource(name),
                change_type="absent",
                detail=_missing_detail(org, name),
                title_override=f"Declared repository absent from org: {name}",
            )
        )
    return records


def build_inventory_records(
    config_jsonnet_text: str,
    live_repos: Iterable[str],
    *,
    org: str,
    allowlist_path: str | None,
) -> list[DriftRecord]:
    """Edge helper: declared config + live repos + allow-list -> sweep records."""
    declared = extract_declared_repos(config_jsonnet_text)
    unmanaged = load_unmanaged(allowlist_path)
    return sweep_inventory(org, declared=declared, live=live_repos, unmanaged=unmanaged)


def _undeclared_detail(org: str, name: str) -> str:
    return (
        f"Repository `{org}/{name}` exists in the live organization but is not "
        f"declared in the committed Otterdog config.\n\n"
        f"Resolve by either:\n"
        f"  - adopting it into config (add `orgs.newRepo('{name}')`, reconciled "
        f"by apply), or\n"
        f"  - marking it intentionally out of scope in drift-allowlist.toml "
        f"(`[[unmanaged]]`, ADR-0002 `managed: false`)."
    )


def _missing_detail(org: str, name: str) -> str:
    return (
        f"Repository `{name}` is declared in the committed Otterdog config but "
        f"does not exist in the live `{org}` organization.\n\n"
        f"Creating it is apply's job; its silent absence is drift (ADR-0002). "
        f"Resolve by running apply to create it, or removing the declaration if "
        f"the repository is no longer wanted."
    )
