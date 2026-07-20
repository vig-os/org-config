"""L1 tests for the expected-drift allow-list."""

from __future__ import annotations

from pathlib import Path

from drift_layer.allowlist import apply_allowlist, load_allowlist, load_unmanaged
from drift_layer.parser import parse_plan


def test_load_allowlist_reads_entries(allowlist_path: Path) -> None:
    entries = load_allowlist(allowlist_path)
    assert len(entries) == 1
    assert entries[0].resource == 'repository[name="vs-dolt"]'
    assert "code_scanning" in entries[0].reason


def test_missing_allowlist_is_empty(tmp_path: Path) -> None:
    assert load_allowlist(None) == []
    assert load_allowlist(tmp_path / "nope.toml") == []


def test_apply_flags_only_matching_resource(plan_pr41: str, allowlist_path: Path) -> None:
    parsed = parse_plan(plan_pr41)
    entries = load_allowlist(allowlist_path)
    flagged = apply_allowlist(parsed.records, entries)
    expected = [r for r in flagged if r.expected]
    assert len(expected) == 1
    assert expected[0].resource == 'repository[name="vs-dolt"]'
    # Every other divergence stays reportable.
    assert sum(1 for r in flagged if not r.expected) == 16


def test_apply_with_no_entries_flags_nothing(plan_pr42: str) -> None:
    parsed = parse_plan(plan_pr42)
    flagged = apply_allowlist(parsed.records, [])
    assert all(not r.expected for r in flagged)


def test_load_unmanaged_reads_repository_names(allowlist_path: Path) -> None:
    names = load_unmanaged(allowlist_path)
    assert names == {"legacy-sandbox", "external-mirror"}


def test_load_unmanaged_missing_is_empty(tmp_path: Path) -> None:
    assert load_unmanaged(None) == set()
    assert load_unmanaged(tmp_path / "nope.toml") == set()
