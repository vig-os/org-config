"""Reconcile drift records against live issues into a desired issue set.

Pure function core (ADR-0007): given the drift records for a run and the
currently-open drift issues, produce the exact set of open/update/close actions
that realises ADR-0002's lifecycle — exactly one deduplicated ``drift`` +
``critical`` issue per divergence, updated-not-duplicated on recurrence, closed
on resolution. No I/O here; the injected client executes the returned actions.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from .models import FINGERPRINT_MARKER, DriftRecord, Issue, IssueAction

DRIFT_LABELS: tuple[str, ...] = ("drift", "critical")

# Inventory-sweep findings (issue #21) carry an extra ``inventory`` label so the
# CLI can partition them into their own issue population — a sweep failure then
# leaves them untouched while settings drift still reconciles (explicit
# degradation).
INVENTORY_LABEL = "inventory"
INVENTORY_LABELS: tuple[str, ...] = (*DRIFT_LABELS, INVENTORY_LABEL)

# Unmanaged-control findings (issue #116) are the third population: controls
# otterdog has no schema field for, asserted directly against the live API. The
# extra label partitions them like the sweep's, and additionally lets the CLI
# withhold individual rows that could not be read (per-row degradation).
UNMANAGED_LABEL = "unmanaged-control"
UNMANAGED_LABELS: tuple[str, ...] = (*DRIFT_LABELS, UNMANAGED_LABEL)

_MARKER_RE = re.compile(r"<!-- drift-fingerprint: (?P<fp>[0-9a-f]+) -->")

# Inventory records use a namespaced resource (see inventory.py); their evidence
# is a sweep finding, not a plan diff.
_INVENTORY_RESOURCE_PREFIX = "repository-inventory"

# Unmanaged-control records use their own namespace (see controls.py); their
# evidence is a live API reading, and there is no plan diff at all.
_UNMANAGED_RESOURCE_PREFIX = "unmanaged-control"


def extract_fingerprint(body: str) -> str | None:
    """Return the fingerprint embedded in an issue body, or None if absent."""
    match = _MARKER_RE.search(body or "")
    return match.group("fp") if match else None


_ISSUE_ONLY = (
    "This is **issue-only** (ADR-0002): nothing is auto-reverted — a human "
    "decides whether to revert the change or adopt it into config, then "
    "closes this issue (it also closes automatically once the divergence "
    "is resolved)."
)

_CONFIG_INTRO = f"The live GitHub state diverges from the committed Otterdog config. {_ISSUE_ONLY}"

# Deliberately NOT the wording above: an unmanaged control has no jsonnet field
# to diverge from, so claiming a config divergence would send the triager
# hunting for a setting that does not exist. The asserted value in
# unmanaged-controls.toml is the only record of what was intended.
_ASSERTION_INTRO = (
    "The live GitHub control diverges from the value asserted for it in "
    "`unmanaged-controls.toml`. Otterdog has no schema field for this control, "
    f"so it appears in no plan diff — the assertion table is its only "
    f"declaration. {_ISSUE_ONLY}"
)


def render_body(record: DriftRecord, *, now: str) -> str:
    """Render the issue body for a divergence (carries the hidden fingerprint)."""
    marker = FINGERPRINT_MARKER.format(fingerprint=record.fingerprint)
    if record.resource.startswith(_UNMANAGED_RESOURCE_PREFIX):
        evidence_label, intro = "Live API assertion", _ASSERTION_INTRO
    elif record.resource.startswith(_INVENTORY_RESOURCE_PREFIX):
        evidence_label, intro = "Inventory finding", _CONFIG_INTRO
    else:
        evidence_label, intro = "Plan diff", _CONFIG_INTRO
    return "\n".join(
        [
            marker,
            f"## Drift detected: `{record.resource}`",
            "",
            f"- **Organization:** `{record.org}`",
            f"- **Change type:** `{record.change_type}`",
            f"- **Last observed:** {now}",
            "",
            intro,
            "",
            f"<details><summary>{evidence_label}</summary>",
            "",
            "```text",
            record.detail,
            "```",
            "",
            "</details>",
        ]
    )


def _recurrence_comment(now: str) -> str:
    return f"Drift still present as of {now}. Refreshed the report above."


def _resolution_comment(now: str, issue: Issue) -> str:
    """Audit-trail close comment, naming the signal that actually cleared.

    An unmanaged-control issue closes because the live API now returns the
    asserted value, not because a plan diff disappeared; the label identifies
    the population, so the wording stays honest without changing reconcile().
    """
    if UNMANAGED_LABEL in issue.labels:
        source = "the live API assertion now matches the declared value"
    else:
        source = "the divergence no longer appears in the plan (config and live state reconciled)"
    return f"Drift resolved as of {now}: {source}. Closing automatically."


def reconcile(
    records: Iterable[DriftRecord],
    issues: Iterable[Issue],
    *,
    now: str,
) -> list[IssueAction]:
    """Diff desired drift (records) against open drift issues into actions.

    - ``expected`` records are dropped (allow-listed, never surfaced).
    - A divergence with no matching open issue -> ``open``.
    - A divergence whose issue already exists -> ``update`` (refresh body + a
      timestamped recurrence comment); never a duplicate.
    - An open drift issue with no matching current divergence -> ``close`` (with
      a resolution comment).
    Actions are deterministically ordered: closes, then opens, then updates,
    each sorted by fingerprint, so output is stable for tests and logs.
    """
    desired: dict[str, DriftRecord] = {}
    for record in records:
        if record.expected:
            continue
        # Last write wins if a resource somehow appears twice; identity is stable.
        desired[record.fingerprint] = record

    current: dict[str, Issue] = {}
    for issue in issues:
        fp = extract_fingerprint(issue.body)
        if fp is not None:
            current[fp] = issue

    opens: list[IssueAction] = []
    updates: list[IssueAction] = []
    closes: list[IssueAction] = []

    for fp, record in desired.items():
        body = render_body(record, now=now)
        if fp in current:
            updates.append(
                IssueAction(
                    kind="update",
                    fingerprint=fp,
                    title=record.title,
                    body=body,
                    comment=_recurrence_comment(now),
                    number=current[fp].number,
                )
            )
        else:
            opens.append(
                IssueAction(
                    kind="open",
                    fingerprint=fp,
                    title=record.title,
                    body=body,
                )
            )

    for fp, issue in current.items():
        if fp not in desired:
            closes.append(
                IssueAction(
                    kind="close",
                    fingerprint=fp,
                    number=issue.number,
                    comment=_resolution_comment(now, issue),
                )
            )

    closes.sort(key=lambda a: a.fingerprint)
    opens.sort(key=lambda a: a.fingerprint)
    updates.sort(key=lambda a: a.fingerprint)
    return closes + opens + updates
