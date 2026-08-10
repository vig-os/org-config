"""L1 tests for the reconciler — the ADR-0002 drift lifecycle.

Acceptance (issue #20 / M3): induced drift opens exactly one issue; a second
run updates it (never duplicates); reverting closes it.
"""

from __future__ import annotations

from drift_layer.allowlist import apply_allowlist, load_allowlist
from drift_layer.models import DriftRecord, Issue
from drift_layer.parser import parse_plan
from drift_layer.reconcile import (
    DRIFT_LABELS,
    extract_fingerprint,
    reconcile,
    render_body,
)

NOW = "2026-07-17 03:00 UTC"


def _record(resource: str, org: str = "vig-os", change: str = "change") -> DriftRecord:
    return DriftRecord(org=org, resource=resource, change_type=change, detail="  ~ x {\n  ~ }")


def test_fingerprint_is_stable_and_resource_scoped() -> None:
    a = _record('repository[name="vs-dolt"]', change="change")
    b = _record('repository[name="vs-dolt"]', change="delete")  # different diff, same resource
    c = _record('repository[name="other"]')
    assert a.fingerprint == b.fingerprint  # keyed on org+resource only
    assert a.fingerprint != c.fingerprint
    assert len(a.fingerprint) == 16


def test_labels_are_drift_and_critical() -> None:
    assert DRIFT_LABELS == ("drift", "critical")


def test_render_body_roundtrips_fingerprint() -> None:
    record = _record('repository[name="vs-dolt"]')
    body = render_body(record, now=NOW)
    assert extract_fingerprint(body) == record.fingerprint
    assert "Drift detected" in body
    assert record.detail in body


def test_induced_drift_opens_exactly_one_issue() -> None:
    records = [_record('repository[name="vs-dolt"]')]
    actions = reconcile(records, [], now=NOW)
    assert len(actions) == 1
    (action,) = actions
    assert action.kind == "open"
    assert action.title == 'Drift: repository[name="vs-dolt"]'
    assert extract_fingerprint(action.body) == records[0].fingerprint
    assert action.number is None


def test_second_run_updates_not_duplicates() -> None:
    record = _record('repository[name="vs-dolt"]')
    existing = Issue(
        number=42,
        title=record.title,
        body=render_body(record, now="2026-07-16 03:00 UTC"),
    )
    actions = reconcile([record], [existing], now=NOW)
    assert len(actions) == 1
    (action,) = actions
    assert action.kind == "update"
    assert action.number == 42
    assert action.comment  # timestamped recurrence comment
    assert NOW in action.body


def test_revert_closes_the_issue() -> None:
    record = _record('repository[name="vs-dolt"]')
    existing = Issue(number=42, title=record.title, body=render_body(record, now=NOW))
    # No records this run == the divergence is gone.
    actions = reconcile([], [existing], now=NOW)
    assert len(actions) == 1
    (action,) = actions
    assert action.kind == "close"
    assert action.number == 42
    assert action.comment


def test_expected_records_never_open_issues() -> None:
    record = _record('repository[name="vs-dolt"]').with_expected(expected=True)
    actions = reconcile([record], [], now=NOW)
    assert actions == []


def test_issues_without_marker_are_ignored() -> None:
    # An unrelated hand-filed issue (no fingerprint marker) must not be closed.
    unrelated = Issue(number=7, title="something else", body="no marker here")
    actions = reconcile([], [unrelated], now=NOW)
    assert actions == []


def test_mixed_run_opens_updates_and_closes_together() -> None:
    keep = _record('repository[name="vs-dolt"]')  # recurs -> update
    new = _record('repository[name="brand-new"]')  # new -> open
    gone = _record('repository[name="resolved"]')  # was open, now absent -> close
    existing = [
        Issue(number=1, title=keep.title, body=render_body(keep, now="old")),
        Issue(number=2, title=gone.title, body=render_body(gone, now="old")),
    ]
    actions = reconcile([keep, new], existing, now=NOW)
    kinds = {(a.kind, a.number) for a in actions}
    assert ("close", 2) in kinds
    assert ("update", 1) in kinds
    assert any(a.kind == "open" and a.number is None for a in actions)
    # Deterministic ordering: closes, then opens, then updates.
    assert [a.kind for a in actions] == ["close", "open", "update"]


def test_pr41_against_empty_issues_opens_all_non_expected(plan_pr41: str, allowlist_path) -> None:
    parsed = parse_plan(plan_pr41)
    records = apply_allowlist(parsed.records, load_allowlist(allowlist_path))
    actions = reconcile(records, [], now=NOW)
    # 17 divergences minus the 1 allow-listed vs-dolt == 16 opened issues.
    assert len(actions) == 16
    assert all(a.kind == "open" for a in actions)
    fingerprints = {a.fingerprint for a in actions}
    assert len(fingerprints) == 16  # all distinct, one per resource


def test_render_body_on_an_unmanaged_control_names_the_live_assertion() -> None:
    # The evidence is a live API reading, not a plan diff: claiming the live
    # state "diverges from the committed Otterdog config" would send the
    # triager looking for a jsonnet field that does not exist.
    record = DriftRecord(
        org="vig-os",
        resource="unmanaged-control:org:sha-pinning",
        change_type="assert-failed",
        detail="expected:  True\nactual:    False",
        title_override="Unmanaged control drift: SHA-pinned actions required org-wide",
    )
    body = render_body(record, now=NOW)
    assert "Live API assertion" in body
    assert "Plan diff" not in body
    assert "Inventory finding" not in body
    assert "unmanaged-controls.toml" in body
    assert "committed Otterdog config" not in body
    assert extract_fingerprint(body) == record.fingerprint


def test_resolution_comment_on_a_control_issue_cites_the_assertion() -> None:
    record = DriftRecord(
        org="vig-os",
        resource="unmanaged-control:org:sha-pinning",
        change_type="assert-failed",
        detail="",
    )
    issue = Issue(
        number=8,
        title=record.title,
        body=render_body(record, now="old"),
        labels=("drift", "critical", "unmanaged-control"),
    )
    (action,) = reconcile([], [issue], now=NOW)
    assert action.kind == "close"
    assert "live API assertion" in action.comment
    assert "plan" not in action.comment
