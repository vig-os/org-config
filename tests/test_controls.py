"""L1 tests for the unmanaged-controls assertion table (issue #116).

The table declares live org/repo controls otterdog cannot model, so they are
invisible to both the plan and the inventory sweep. Loading, endpoint
templating, dotted-path selection and fingerprint namespacing are pure and
offline; nothing here touches the network.
"""

from __future__ import annotations

from pathlib import Path

from drift_layer.controls import (
    MISSING,
    RESOURCE_PREFIX,
    UNSET,
    control_resource,
    load_controls,
    resolve_endpoint,
    select_path,
)
from drift_layer.models import DriftRecord

ORG = "vig-os"


def _by_key(config, key: str, scope: str = "org"):
    (control,) = [c for c in config.controls if c.key == key and c.scope == scope]
    return control


# --- load_controls -------------------------------------------------------------


def test_load_controls_parses_every_declared_key(controls_path: Path) -> None:
    config = load_controls(controls_path)
    assert [c.key for c in config.controls] == [
        "fork-pr-approval",
        "sha-pinning",
        "secret-scanning-validity-checks",
        "two-factor-requirement",
    ]

    plain = _by_key(config, "fork-pr-approval")
    assert plain.scope == "org"
    assert plain.repository is None
    assert plain.title == "Fork-PR approval policy"
    assert plain.endpoint == "/orgs/{org}/actions/permissions/fork-pr-contributor-approval"
    assert plain.path == "approval_policy"
    assert plain.expect == "first_time_contributors"
    assert plain.tolerated is UNSET
    assert plain.kind == "assert"
    assert "asserted" in plain.reason
    assert plain.refs == ()

    tolerated = _by_key(config, "sha-pinning")
    assert tolerated.expect is True
    assert tolerated.tolerated is False  # a literal False, not "absent"
    assert tolerated.refs == ("#120",)

    scoped = _by_key(config, "secret-scanning-validity-checks", scope="repo")
    assert scoped.repository == "devkit"
    assert scoped.path == "security_and_analysis.secret_scanning_validity_checks.status"

    unassertable = _by_key(config, "two-factor-requirement")
    assert unassertable.kind == "unassertable"
    assert unassertable.expect is UNSET
    assert unassertable.endpoint == ""
    assert unassertable.recheck == "quarterly"


def test_load_controls_reads_the_org_secrets_policy(controls_path: Path) -> None:
    policy = load_controls(controls_path).org_secrets
    assert policy is not None
    assert policy.enabled is True
    assert policy.assert_visibility is True
    assert policy.assert_selected_repositories is True
    assert policy.assert_no_undeclared is True
    assert "committed config" in policy.reason


def test_missing_controls_file_is_empty(tmp_path: Path) -> None:
    for config in (load_controls(None), load_controls(tmp_path / "nope.toml")):
        assert config.controls == []
        assert config.org_secrets is None


def test_load_controls_skips_malformed_rows(tmp_path: Path) -> None:
    # A row that cannot be evaluated is dropped rather than half-asserted: a
    # broken row must never manufacture a security finding.
    path = tmp_path / "controls.toml"
    path.write_text(
        """
[[control]]
scope = "org"
endpoint = "/orgs/{org}"
path = "x"
expect = true

[[control]]
key = "bad-scope"
scope = "enterprise"
endpoint = "/orgs/{org}"
path = "x"
expect = true

[[control]]
key = "repo-without-repository"
scope = "repo"
endpoint = "/repos/{org}/{repo}"
path = "x"
expect = true

[[control]]
key = "no-expected-value"
scope = "org"
endpoint = "/orgs/{org}"
path = "x"

[[control]]
key = "good"
scope = "org"
title = "kept"
endpoint = "/orgs/{org}"
path = "x"
expect = true
"""
    )
    config = load_controls(path)
    assert [c.key for c in config.controls] == ["good"]


def test_load_controls_defaults_title_to_the_key(tmp_path: Path) -> None:
    path = tmp_path / "controls.toml"
    path.write_text(
        '[[control]]\nkey = "untitled"\nscope = "org"\n'
        'endpoint = "/orgs/{org}"\npath = "x"\nexpect = true\n'
    )
    (control,) = load_controls(path).controls
    assert control.title == "untitled"


# --- endpoint templating -------------------------------------------------------


def test_resolve_endpoint_templates_org_and_repo(controls_path: Path) -> None:
    config = load_controls(controls_path)
    assert (
        resolve_endpoint(_by_key(config, "fork-pr-approval"), org=ORG)
        == "/orgs/vig-os/actions/permissions/fork-pr-contributor-approval"
    )
    scoped = _by_key(config, "secret-scanning-validity-checks", scope="repo")
    assert resolve_endpoint(scoped, org=ORG) == "/repos/vig-os/devkit"


# --- select_path ---------------------------------------------------------------


def test_select_path_reads_a_top_level_key() -> None:
    assert select_path({"approval_policy": "first_time_contributors"}, "approval_policy") == (
        "first_time_contributors"
    )


def test_select_path_walks_nested_keys() -> None:
    document = {"security_and_analysis": {"secret_scanning": {"status": "enabled"}}}
    assert select_path(document, "security_and_analysis.secret_scanning.status") == "enabled"


def test_select_path_missing_key_is_the_missing_sentinel() -> None:
    assert select_path({"a": {"b": 1}}, "a.c") is MISSING
    assert select_path({"a": {"b": 1}}, "nope") is MISSING


def test_select_path_through_a_non_mapping_is_missing() -> None:
    # A renamed/retyped field must degrade, never be read as a bare value.
    assert select_path({"a": "scalar"}, "a.b") is MISSING
    assert select_path(["not", "a", "mapping"], "a") is MISSING


def test_select_path_preserves_false_and_none_values() -> None:
    # `false` is a legitimate live value and must not be confused with absence.
    assert select_path({"sha_pinning_required": False}, "sha_pinning_required") is False
    assert select_path({"x": None}, "x") is None


# --- fingerprint namespacing ---------------------------------------------------


def test_control_resource_namespaces_org_and_repo_scopes(controls_path: Path) -> None:
    config = load_controls(controls_path)
    assert control_resource(_by_key(config, "sha-pinning")) == f"{RESOURCE_PREFIX}:org:sha-pinning"
    scoped = _by_key(config, "secret-scanning-validity-checks", scope="repo")
    assert control_resource(scoped) == f"{RESOURCE_PREFIX}:devkit:secret-scanning-validity-checks"


def test_control_fingerprints_are_distinct_from_the_other_populations() -> None:
    def record(resource: str) -> DriftRecord:
        return DriftRecord(org=ORG, resource=resource, change_type="assert-failed", detail="")

    org_scoped = record(f"{RESOURCE_PREFIX}:org:sha-pinning")
    repo_scoped = record(f"{RESOURCE_PREFIX}:devkit:sha-pinning")
    settings = record('repository[name="devkit"]')
    inventory = record("repository-inventory:devkit")

    fingerprints = {r.fingerprint for r in (org_scoped, repo_scoped, settings, inventory)}
    assert len(fingerprints) == 4
    # Stable across evaluations: identity is the TOML key, not the live value.
    assert org_scoped.fingerprint == record(f"{RESOURCE_PREFIX}:org:sha-pinning").fingerprint
