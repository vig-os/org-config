"""L1 tests for the inventory sweep — undeclared / missing repos + unmanaged.

The sweep (ADR-0002 undeclared-repo lifecycle, issue #21) compares the live org
repo inventory against the declared set from the committed otterdog config and
turns each divergence into a `DriftRecord` feeding the SAME reconcile()/issue
lifecycle. Declared-set extraction is a pure, offline literal read of the
committed jsonnet, verified here against the known committed set.
"""

from __future__ import annotations

from drift_layer.inventory import (
    extract_declared_repos,
    missing_resource,
    sweep_inventory,
    undeclared_resource,
)


def test_extract_declared_repos_matches_committed_set(
    declared_jsonnet: str, declared_repos: frozenset[str]
) -> None:
    declared = extract_declared_repos(declared_jsonnet)
    assert declared == set(declared_repos)


def test_extract_ignores_ruleset_secret_variable_constructors() -> None:
    # newRepoRuleset / newRepoSecret / newRepoVariable share the `newRepo`
    # prefix but must never be mistaken for a repository declaration.
    text = """
    orgs.newRepo('real-repo') {
      rulesets: [
        orgs.newRepoRuleset('Main protection') {},
      ],
      secrets: [ orgs.newRepoSecret('TOKEN') {} ],
      variables: [ orgs.newRepoVariable('CACHE') {} ],
    }
    """
    assert extract_declared_repos(text) == {"real-repo"}


def test_extract_ignores_commented_out_declarations() -> None:
    text = """
    orgs.newRepo('live-one') {}
    // orgs.newRepo('commented-out') {}
    """
    assert extract_declared_repos(text) == {"live-one"}


def test_sweep_all_declared_present_is_clean() -> None:
    records = sweep_inventory(
        "vig-os",
        declared={"a", "b"},
        live=["a", "b"],
        unmanaged=set(),
    )
    assert records == []


def test_sweep_flags_undeclared_live_repo() -> None:
    records = sweep_inventory(
        "vig-os",
        declared={"a"},
        live=["a", "rogue"],
        unmanaged=set(),
    )
    assert len(records) == 1
    (rec,) = records
    assert rec.org == "vig-os"
    assert rec.resource == undeclared_resource("rogue")
    assert rec.resource == "repository-inventory:rogue"
    assert "rogue" in rec.title
    assert "Undeclared" in rec.title


def test_sweep_flags_declared_but_absent_repo_with_distinct_title() -> None:
    records = sweep_inventory(
        "vig-os",
        declared={"a", "ghost"},
        live=["a"],
        unmanaged=set(),
    )
    assert len(records) == 1
    (rec,) = records
    assert rec.resource == missing_resource("ghost")
    assert rec.resource == "repository-inventory-missing:ghost"
    assert "ghost" in rec.title
    # Distinct title from the undeclared finding.
    assert (
        rec.title
        != sweep_inventory("vig-os", declared=set(), live=["ghost"], unmanaged=set())[0].title
    )


def test_undeclared_and_missing_fingerprints_are_distinct() -> None:
    undeclared = sweep_inventory("vig-os", declared=set(), live=["x"], unmanaged=set())[0]
    missing = sweep_inventory("vig-os", declared={"x"}, live=[], unmanaged=set())[0]
    assert undeclared.fingerprint != missing.fingerprint
    # And distinct from a settings-drift resource of the same repo (namespaced).
    from drift_layer.models import DriftRecord  # noqa: PLC0415

    settings = DriftRecord(
        org="vig-os", resource='repository[name="x"]', change_type="change", detail=""
    )
    assert undeclared.fingerprint != settings.fingerprint


def test_unmanaged_repo_exempt_from_undeclared_flag() -> None:
    records = sweep_inventory(
        "vig-os",
        declared={"a"},
        live=["a", "external-mirror"],
        unmanaged={"external-mirror"},
    )
    assert records == []


def test_unmanaged_repo_exempt_from_missing_flag() -> None:
    # A name listed as unmanaged is out of declarative scope in both directions.
    records = sweep_inventory(
        "vig-os",
        declared={"a", "legacy-sandbox"},
        live=["a"],
        unmanaged={"legacy-sandbox"},
    )
    assert records == []


def test_sweep_reports_both_kinds_together_sorted() -> None:
    records = sweep_inventory(
        "vig-os",
        declared={"keep", "ghost"},
        live=["keep", "rogue"],
        unmanaged=set(),
    )
    resources = {r.resource for r in records}
    assert undeclared_resource("rogue") in resources
    assert missing_resource("ghost") in resources
    assert len(records) == 2
