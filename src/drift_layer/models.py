"""Core value types for the drift layer.

Pure data, no I/O. The parser produces :class:`DriftRecord`s from otterdog plan
output; the reconciler turns records + live issues into :class:`IssueAction`s
that the injected GitHub client executes at the edge (ADR-0007).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

# otterdog diff symbol -> canonical change type (see the "Actions are indicated
# with the following symbols" legend every plan prints).
CHANGE_TYPES: dict[str, str] = {
    "+": "add",
    "~": "change",
    "!": "forced",
    "-": "delete",
}

# Hidden HTML marker embedded in every drift issue body; carries the stable
# per-resource fingerprint so recurrence updates the existing issue in place
# instead of opening a duplicate (ADR-0002). Kept invisible in the rendered
# issue but greppable by the reconciler.
FINGERPRINT_MARKER = "<!-- drift-fingerprint: {fingerprint} -->"


@dataclass(frozen=True)
class DriftRecord:
    """One resource-level divergence between committed config and live state.

    ``resource`` is the otterdog block header (e.g.
    ``repository[name="vs-dolt"]``) and is the stable identity of the
    divergence — the fingerprint keys on org + resource only, never on the
    volatile ``detail`` body, so a recurrence with a slightly different diff
    still maps to the same issue.
    """

    org: str
    resource: str
    change_type: str
    detail: str
    expected: bool = False

    @property
    def fingerprint(self) -> str:
        """Deterministic per-resource key (org + resource), truncated SHA-256."""
        digest = hashlib.sha256(f"{self.org}\0{self.resource}".encode()).hexdigest()
        return digest[:16]

    @property
    def title(self) -> str:
        """Issue title following the ``Drift: <resource>`` convention."""
        return f"Drift: {self.resource}"

    def with_expected(self, *, expected: bool) -> DriftRecord:
        """Return a copy with the ``expected`` flag set (records are frozen)."""
        return DriftRecord(
            org=self.org,
            resource=self.resource,
            change_type=self.change_type,
            detail=self.detail,
            expected=expected,
        )


@dataclass(frozen=True)
class PlanSummary:
    """The ``Plan: X to add, Y to change, Z to delete`` trailer counts."""

    add: int
    change: int
    delete: int

    @property
    def total(self) -> int:
        return self.add + self.change + self.delete


@dataclass(frozen=True)
class ParsedPlan:
    """Structured result of parsing one otterdog plan output."""

    org: str
    records: list[DriftRecord] = field(default_factory=list)
    summary: PlanSummary | None = None


@dataclass(frozen=True)
class Issue:
    """Minimal view of a live GitHub issue the reconciler needs."""

    number: int
    title: str
    body: str
    state: str = "open"


@dataclass(frozen=True)
class IssueAction:
    """A single reconciliation step for the GitHub client to execute."""

    kind: str  # "open" | "update" | "close"
    fingerprint: str
    title: str = ""
    body: str = ""
    comment: str = ""
    number: int | None = None
