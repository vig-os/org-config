"""Expected-drift allow-list: mark known-benign divergences as ``expected``.

The allow-list is config-driven (a small TOML the workflow passes), never
hardcoded — ADR-0002's ``managed: false`` / known-artifact policy. A record
whose ``resource`` matches an entry is flagged ``expected`` and excluded from
issue creation by the reconciler. The canonical example is the ``vs-dolt``
``code_scanning_default_languages`` import artifact.
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
