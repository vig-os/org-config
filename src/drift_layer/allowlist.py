"""Expected-drift allow-list: mark known-benign divergences as ``expected``.

The allow-list is config-driven (a small TOML the workflow passes), never
hardcoded — ADR-0002's ``managed: false`` / known-artifact policy. A record
whose ``resource`` matches an entry is flagged ``expected`` and excluded from
issue creation by the reconciler. The canonical example is the ``vs-dolt``
``code_scanning_default_languages`` import artifact.

The same file carries the other two allow-lists, for the same governance reason
— an entry is a reviewable PR, so what is tolerated stays versioned:
``[[unmanaged]]`` (repos out of declarative scope, issue #21) and
``[[app_actor]]`` (App slugs the engine's token provably cannot resolve by
design, issue #259).
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .models import DriftRecord


@dataclass(frozen=True)
class ExpectedEntry:
    """One allow-list entry: an exact resource header, plus a documented why."""

    resource: str
    reason: str = ""


def load_allowlist(path: str | Path | None) -> list[ExpectedEntry]:
    """Load allow-list entries from a TOML file.

    A missing/None path yields an empty list (no expected drift). The file
    shape is a list of ``[[expected]]`` tables with a ``resource`` key and an
    optional ``reason``.
    """
    if path is None:
        return []
    p = Path(path)
    if not p.exists():
        return []
    data = tomllib.loads(p.read_text())
    entries: list[ExpectedEntry] = []
    for raw in data.get("expected", []):
        resource = raw.get("resource")
        if not resource:
            continue
        entries.append(ExpectedEntry(resource=resource, reason=raw.get("reason", "")))
    return entries


def apply_allowlist(
    records: Iterable[DriftRecord], entries: Iterable[ExpectedEntry]
) -> list[DriftRecord]:
    """Return records with ``expected`` set where the resource is allow-listed."""
    allowed = {e.resource for e in entries}
    return [record.with_expected(expected=record.resource in allowed) for record in records]


def load_app_actor_allowlist(path: str | Path | None) -> dict[str, str]:
    """Load the known-unresolvable App slugs from a TOML file (issue #259).

    The third section of the same governance file, in the shape of the other
    two: a list of ``[[app_actor]]`` tables with a ``slug`` key and a ``reason``.
    A slug named here is one the engine's installation token provably cannot
    resolve **by design** — the canonical case is a private App owned by a
    sibling org, on a ruleset that is already live and correct and cannot be
    repaired until upstream `eclipse-csi/otterdog#772` lands. Reporting it as a
    finding on every pull request would be a standing red banner nobody can act
    on, which is the noise that trains a reviewer to wave plans through; the
    check still runs and still reports the slug, under "known and suppressed"
    with the reason, so the suppression is visible rather than silent.

    Returns a mapping of case-folded slug -> reason (App slugs are
    case-insensitive). A missing/None path yields an empty mapping.
    """
    if path is None:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    data = tomllib.loads(p.read_text())
    reasons: dict[str, str] = {}
    for raw in data.get("app_actor", []):
        slug = raw.get("slug")
        if slug:
            reasons[str(slug).casefold()] = raw.get("reason", "")
    return reasons


def load_unmanaged(path: str | Path | None) -> set[str]:
    """Load the ``managed: false`` repo names from a TOML file (issue #21).

    The file shape is a list of ``[[unmanaged]]`` tables with a ``repository``
    key (and optional ``reason``). A missing/None path yields an empty set. Repos
    named here are exempt from both undeclared-repo and settings-reconciliation
    flagging, yet stay visible/reviewed in the file (ADR-0002).
    """
    if path is None:
        return set()
    p = Path(path)
    if not p.exists():
        return set()
    data = tomllib.loads(p.read_text())
    names: set[str] = set()
    for raw in data.get("unmanaged", []):
        repository = raw.get("repository")
        if repository:
            names.add(repository)
    return names
