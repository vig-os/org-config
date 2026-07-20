"""L1 unit tests for the otterdog plan parser over recorded fixtures."""

from __future__ import annotations

from drift_layer.parser import parse_plan


def test_pr41_yields_one_record_per_resource(plan_pr41: str) -> None:
    parsed = parse_plan(plan_pr41)
    assert parsed.org == "vig-os"
    # 17 changes in the trailer == 17 resource-level divergences.
    assert parsed.summary is not None
    assert (parsed.summary.add, parsed.summary.change, parsed.summary.delete) == (0, 17, 0)
    assert len(parsed.records) == 17
    assert all(r.change_type == "change" for r in parsed.records)


def test_pr41_resource_headers_parsed_verbatim(plan_pr41: str) -> None:
    parsed = parse_plan(plan_pr41)
    resources = {r.resource for r in parsed.records}
    assert 'repo_ruleset[name="Dev protection", repository=devkit]' in resources
    assert 'branch_protection_rule[pattern="main", repository=tessera]' in resources
    assert 'repository[name="vs-dolt"]' in resources


def test_pr41_detail_captures_nested_block(plan_pr41: str) -> None:
    parsed = parse_plan(plan_pr41)
    vsdolt = next(r for r in parsed.records if r.resource == 'repository[name="vs-dolt"]')
    assert "code_scanning_default_languages" in vsdolt.detail
    assert '"javascript"          -> "javascript-typescript"' in vsdolt.detail
    assert vsdolt.detail.startswith('  ~ repository[name="vs-dolt"] {')
    assert vsdolt.detail.rstrip().endswith("~ }")


def test_pr42_single_change(plan_pr42: str) -> None:
    parsed = parse_plan(plan_pr42)
    assert len(parsed.records) == 1
    (record,) = parsed.records
    assert record.resource == 'repository[name="vs-dolt"]'
    assert record.change_type == "change"
    assert parsed.summary is not None
    assert parsed.summary.change == 1


def test_empty_plan_has_no_records(plan_empty: str) -> None:
    parsed = parse_plan(plan_empty)
    assert parsed.records == []
    assert parsed.org == "vig-os"
    assert parsed.summary is not None
    assert parsed.summary.total == 0


def test_mixed_symbols_map_to_change_types(plan_mixed: str) -> None:
    parsed = parse_plan(plan_mixed)
    by_resource = {r.resource: r.change_type for r in parsed.records}
    assert by_resource['repository[name="new-repo"]'] == "add"
    assert by_resource['branch_protection_rule[pattern="main", repository=devkit]'] == "forced"
    assert by_resource['repo_ruleset[name="Legacy protection", repository=tessera]'] == "delete"
    assert parsed.summary is not None
    assert (parsed.summary.add, parsed.summary.change, parsed.summary.delete) == (1, 1, 1)


def test_preamble_noise_is_ignored(plan_pr42: str) -> None:
    # The uv "Downloading .../Installed" preamble must never become a record.
    parsed = parse_plan(plan_pr42)
    assert all("Downloading" not in r.resource for r in parsed.records)
    assert all("Installed" not in r.resource for r in parsed.records)
