"""Core value types for the drift layer.

Pure data, no I/O. The parser produces :class:`DriftRecord`s from otterdog plan
output; the reconciler turns records + live issues into :class:`IssueAction`s
that the injected GitHub client executes at the edge (ADR-0007).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace

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
    # Inventory-sweep findings (issue #21) carry a purpose-built title instead of
    # the generic ``Drift: <resource>`` — e.g. "Undeclared repository: foo". The
    # ``resource`` still drives the fingerprint, so identity/dedup is unchanged.
    title_override: str | None = None

    @property
    def fingerprint(self) -> str:
        """Deterministic per-resource key (org + resource), truncated SHA-256.

        The ``resource`` is a namespaced identity: settings drift uses otterdog
        block headers (``repository[name="x"]``); the inventory sweep uses
        ``repository-inventory:<name>`` / ``repository-inventory-missing:<name>``.
        Distinct namespaces never collide, so all findings share one dedup
        keyspace and the single reconcile()/issue lifecycle (ADR-0002).
        """
        digest = hashlib.sha256(f"{self.org}\0{self.resource}".encode()).hexdigest()
        return digest[:16]

    @property
    def title(self) -> str:
        """Issue title: the override if set, else ``Drift: <resource>``."""
        return self.title_override or f"Drift: {self.resource}"

    def with_expected(self, *, expected: bool) -> DriftRecord:
        """Return a copy with the ``expected`` flag set (records are frozen)."""
        return replace(self, expected=expected)


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
    """Minimal view of a live GitHub issue the reconciler needs.

    ``labels`` lets the CLI partition open drift issues into the settings-drift
    and inventory-sweep populations (the latter carries the ``inventory`` label),
    so a sweep failure leaves inventory issues untouched (issue #21 degradation).
    """

    number: int
    title: str
    body: str
    state: str = "open"
    labels: tuple[str, ...] = ()


@dataclass(frozen=True)
class IssueAction:
    """A single reconciliation step for the GitHub client to execute."""

    kind: str  # "open" | "update" | "close"
    fingerprint: str
    title: str = ""
    body: str = ""
    comment: str = ""
    number: int | None = None
