"""L1 tests for the unmanaged-controls assertion table (issue #116).

The table declares live org/repo controls otterdog cannot model, so they are
invisible to both the plan and the inventory sweep. Loading, endpoint
templating, dotted-path selection and fingerprint namespacing are pure and
offline; the evaluation runs against an injected fake client, so nothing here
touches the network.
"""

from __future__ import annotations

from pathlib import Path

from drift_layer.controls import (
    DRIFT,
    MISSING,
    OK,
    RESOURCE_PREFIX,
    SKIPPED,
    TOLERATED,
    UNRESOLVED,
    UNSET,
    Control,
    ControlsConfig,
    OrgSecretsPolicy,
    control_resource,
    evaluate_controls,
    load_controls,
    resolve_endpoint,
    select_path,
)
from drift_layer.github_client import ApiError
from drift_layer.models import DriftRecord

ORG = "vig-os"


class FakeApiClient:
    """Maps a resolved endpoint to a canned document or a raised ApiError."""

    def __init__(
        self,
        responses: dict[str, object] | None = None,
        org_secrets: object = None,
        secret_repositories: dict[str, object] | None = None,
    ) -> None:
        self.responses = responses or {}
        self.org_secrets = org_secrets if org_secrets is not None else []
        self.secret_repositories = secret_repositories or {}
        self.requested: list[str] = []

    def get_json(self, path: str) -> object:
        self.requested.append(path)
        return _unwrap(self.responses[path])

    def list_org_secrets(self, org: str) -> list[dict]:
        self.requested.append(f"/orgs/{org}/actions/secrets")
        return _unwrap(self.org_secrets)

    def list_org_secret_repositories(self, org: str, name: str) -> list[str]:
        self.requested.append(f"/orgs/{org}/actions/secrets/{name}/repositories")
        return _unwrap(self.secret_repositories[name])


def _unwrap(response: object) -> object:
    if isinstance(response, ApiError):
        raise response
    return response


def _by_key(config, key: str, scope: str = "org"):
    (control,) = [c for c in config.controls if c.key == key and c.scope == scope]
    return control


def _control(**overrides: object) -> Control:
    fields: dict[str, object] = {
        "key": "sha-pinning",
        "scope": "org",
        "title": "SHA-pinned actions required org-wide",
        "endpoint": "/orgs/{org}/actions/permissions",
        "path": "sha_pinning_required",
        "expect": True,
        "reason": "actions can otherwise be moved under a mutable tag",
    }
    fields.update(overrides)
    return Control(**fields)  # type: ignore[arg-type]


def _evaluate(control: Control, responses: dict[str, object]):
    client = FakeApiClient(responses)
    return evaluate_controls(ControlsConfig(controls=[control]), client, org=ORG), client


PERMISSIONS = "/orgs/vig-os/actions/permissions"


# --- load_controls -------------------------------------------------------------


def test_load_controls_parses_every_declared_key(controls_path: Path) -> None:
    config = load_controls(controls_path)
    assert [c.key for c in config.controls] == [
        "fork-pr-approval",
        "sha-pinning",
        "secret-scanning-validity-checks",
        "main-required-checks",
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

    listed = _by_key(config, "main-required-checks", scope="repo")
    assert listed.compare == "set"
    assert listed.expect == ["CI Summary", "Check Summary"]
    assert listed.path == (
        "[type=required_status_checks].parameters.required_status_checks[].context"
    )

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


# --- evaluation outcomes -------------------------------------------------------


def test_live_value_matching_the_expectation_is_clean() -> None:
    control = _control()
    result, _ = _evaluate(control, {PERMISSIONS: {"sha_pinning_required": True}})
    assert result.records == []
    assert result.clean_fingerprints == {_fingerprint(control)}
    assert result.unresolved_fingerprints == set()
    assert [o.status for o in result.outcomes] == [OK]


def test_live_value_diverging_opens_one_record_with_the_evidence() -> None:
    control = _control()
    result, _ = _evaluate(control, {PERMISSIONS: {"sha_pinning_required": False}})
    (record,) = result.records
    assert record.org == ORG
    assert record.resource == f"{RESOURCE_PREFIX}:org:sha-pinning"
    assert record.change_type == "assert-failed"
    assert record.title == "Unmanaged control drift: SHA-pinned actions required org-wide"
    # The evidence block must carry enough to triage without re-reading the API.
    assert PERMISSIONS in record.detail
    assert "sha_pinning_required" in record.detail
    assert "expected" in record.detail.lower()
    assert "True" in record.detail
    assert "False" in record.detail
    assert control.reason in record.detail
    # A failed row is neither clean nor unresolved: it is drift.
    assert result.clean_fingerprints == set()
    assert result.unresolved_fingerprints == set()
    assert [o.status for o in result.outcomes] == [DRIFT]


def test_tolerated_value_is_clean_but_noted() -> None:
    control = _control(tolerated=False, refs=("#120",))
    result, _ = _evaluate(control, {PERMISSIONS: {"sha_pinning_required": False}})
    assert result.records == []
    assert result.clean_fingerprints == {_fingerprint(control)}
    assert [o.status for o in result.outcomes] == [TOLERATED]
    assert any("sha-pinning" in note for note in result.notes)


def test_a_third_value_is_drift_even_with_a_tolerated_escape() -> None:
    control = _control(
        key="secret-scanning-non-provider-patterns",
        path="status",
        endpoint="/repos/{org}/{repo}",
        scope="repo",
        repository="devkit",
        expect="enabled",
        tolerated="disabled",
    )
    result, _ = _evaluate(control, {"/repos/vig-os/devkit": {"status": "suspended"}})
    (record,) = result.records
    assert "suspended" in record.detail
    assert "disabled" in record.detail  # the tolerated value is part of the evidence
    assert result.clean_fingerprints == set()


def test_expectation_comparison_does_not_conflate_booleans_with_integers() -> None:
    # `1` is not `true`: a retyped field is drift, not a silent pass.
    result, _ = _evaluate(_control(), {PERMISSIONS: {"sha_pinning_required": 1}})
    assert len(result.records) == 1


# --- per-row degradation -------------------------------------------------------


def _degrades(response: object, expected_note: str) -> None:
    control = _control()
    result, _ = _evaluate(control, {PERMISSIONS: response})
    assert result.records == []
    assert result.clean_fingerprints == set()
    assert result.unresolved_fingerprints == {_fingerprint(control)}
    assert [o.status for o in result.outcomes] == [UNRESOLVED]
    assert any(expected_note in note for note in result.notes)


def test_missing_endpoint_degrades_the_row() -> None:
    _degrades(ApiError(404, "GET /orgs/vig-os/actions/permissions: Not Found"), "unassertable")


def test_forbidden_endpoint_degrades_the_row() -> None:
    _degrades(ApiError(403, "GET /orgs/vig-os/actions/permissions: Forbidden"), "token")


def test_network_failure_degrades_the_row() -> None:
    _degrades(ApiError(0, "connection refused"), "unreadable")


def test_absent_field_degrades_rather_than_fabricating_drift() -> None:
    # A 200 whose schema no longer carries the path means GitHub moved the
    # field; reporting that as drift would invent a security finding.
    _degrades({"something_else": True}, "absent")


def test_unresolved_rows_are_withheld_from_both_populations() -> None:
    # The load-bearing contract: an unreadable row must never land in
    # clean_fingerprints, or reconcile() would close its open issue.
    clean = _control()
    broken = _control(
        key="fork-pr-approval",
        endpoint="/orgs/{org}/actions/permissions/fork-pr-contributor-approval",
        path="approval_policy",
        expect="first_time_contributors",
    )
    client = FakeApiClient(
        {
            PERMISSIONS: {"sha_pinning_required": True},
            f"{PERMISSIONS}/fork-pr-contributor-approval": ApiError(403, "Forbidden"),
        }
    )
    result = evaluate_controls(ControlsConfig(controls=[clean, broken]), client, org=ORG)
    assert result.clean_fingerprints == {_fingerprint(clean)}
    assert result.unresolved_fingerprints == {_fingerprint(broken)}
    assert result.records == []


# --- memoization and unassertable rows -----------------------------------------


def test_rows_sharing_an_endpoint_are_read_once() -> None:
    keys = ("dependency-graph", "dependabot-alerts", "secret-scanning")
    controls = [
        _control(key=key, endpoint="/orgs/{org}", path=f"{key.replace('-', '_')}_enabled")
        for key in keys
    ]
    client = FakeApiClient({"/orgs/vig-os": {f"{k.replace('-', '_')}_enabled": True for k in keys}})
    result = evaluate_controls(ControlsConfig(controls=controls), client, org=ORG)
    assert client.requested == ["/orgs/vig-os"]
    assert len(result.clean_fingerprints) == 3


def test_a_failed_read_is_memoized_too() -> None:
    controls = [_control(key="a", path="x"), _control(key="b", path="y")]
    client = FakeApiClient({PERMISSIONS: ApiError(403, "Forbidden")})
    result = evaluate_controls(ControlsConfig(controls=controls), client, org=ORG)
    assert client.requested == [PERMISSIONS]
    assert len(result.unresolved_fingerprints) == 2


def test_unassertable_rows_are_never_evaluated(controls_path: Path) -> None:
    config = load_controls(controls_path)
    unassertable = _by_key(config, "two-factor-requirement")
    client = FakeApiClient({})
    result = evaluate_controls(ControlsConfig(controls=[unassertable]), client, org=ORG)
    assert client.requested == []
    assert result.records == []
    assert result.clean_fingerprints == set()
    assert result.unresolved_fingerprints == set()
    assert [o.status for o in result.outcomes] == [SKIPPED]
    assert any("two-factor-requirement" in note for note in result.notes)


def test_outcomes_report_the_scope_expected_and_actual_values() -> None:
    control = _control(scope="repo", repository="devkit", endpoint="/repos/{org}/{repo}")
    result, _ = _evaluate(control, {"/repos/vig-os/devkit": {"sha_pinning_required": False}})
    (outcome,) = result.outcomes
    assert outcome.key == "sha-pinning"
    assert outcome.scope == "devkit"
    assert outcome.status == DRIFT
    assert outcome.expected == "True"
    assert outcome.actual == "False"


def _fingerprint(control: Control) -> str:
    return DriftRecord(
        org=ORG, resource=control_resource(control), change_type="assert-failed", detail=""
    ).fingerprint


# --- generated org-secret families ---------------------------------------------

DECLARED_SECRETS = """
orgs.newOrgSecret('ALPHA') {
  selected_repositories+: [
    'devkit',
    'org-config',
  ],
  value: '********',
  visibility: 'selected',
},
orgs.newOrgSecret('BETA') {
  selected_repositories+: [
    'org-config',
  ],
  value: '********',
  visibility: 'selected',
},
"""

LIVE_MATCHING = [
    {"name": "ALPHA", "visibility": "selected"},
    {"name": "BETA", "visibility": "selected"},
]
REPOS_MATCHING: dict[str, object] = {
    "ALPHA": ["org-config", "devkit"],
    "BETA": ["org-config"],
}


def _evaluate_secrets(
    live: object = None,
    repositories: dict[str, object] | None = None,
    **policy: object,
):
    settings: dict[str, object] = {
        "enabled": True,
        "assert_visibility": True,
        "assert_selected_repositories": True,
        "assert_no_undeclared": True,
        "reason": "otterdog cannot diff a dummy-valued secret",
    }
    settings.update(policy)
    config = ControlsConfig(
        controls=[],
        org_secrets=OrgSecretsPolicy(**settings),  # type: ignore[arg-type]
    )
    client = FakeApiClient(
        org_secrets=LIVE_MATCHING if live is None else live,
        secret_repositories=REPOS_MATCHING if repositories is None else repositories,
    )
    result = evaluate_controls(config, client, org=ORG, config_jsonnet_text=DECLARED_SECRETS)
    return result, client


def test_live_org_secrets_matching_the_config_are_clean() -> None:
    result, _ = _evaluate_secrets()
    assert result.records == []
    assert len(result.clean_fingerprints) == 3  # one per enabled family
    assert {o.status for o in result.outcomes} == {OK}


def test_widened_visibility_yields_one_aggregate_record() -> None:
    live = [{"name": "ALPHA", "visibility": "all"}, {"name": "BETA", "visibility": "selected"}]
    result, _ = _evaluate_secrets(live=live, repositories={"BETA": ["org-config"]})
    (record,) = result.records
    assert record.resource == f"{RESOURCE_PREFIX}:org:org-secret-visibility"
    assert "ALPHA" in record.detail
    assert "BETA" not in record.detail
    assert "selected" in record.detail
    assert "all" in record.detail


def test_selected_repository_gain_and_loss_are_reported_in_both_directions() -> None:
    repositories = {"ALPHA": ["org-config", "rogue"], "BETA": ["org-config"]}
    result, _ = _evaluate_secrets(repositories=repositories)
    (record,) = result.records
    assert record.resource == f"{RESOURCE_PREFIX}:org:org-secret-repositories"
    assert "rogue" in record.detail  # live-only: an unreviewed reader
    assert "devkit" in record.detail  # config-only: a consumer that lost access


def test_undeclared_live_secret_is_its_own_family() -> None:
    live = [*LIVE_MATCHING, {"name": "GHOST", "visibility": "all"}]
    result, _ = _evaluate_secrets(live=live)
    (record,) = result.records
    assert record.resource == f"{RESOURCE_PREFIX}:org:org-secret-undeclared"
    assert "GHOST" in record.detail


def test_two_independent_breakages_stay_two_records() -> None:
    live = [{"name": "ALPHA", "visibility": "all"}, {"name": "BETA", "visibility": "selected"}]
    result, _ = _evaluate_secrets(live=live, repositories={"BETA": ["rogue"]})
    assert len(result.records) == 2
    assert {r.resource for r in result.records} == {
        f"{RESOURCE_PREFIX}:org:org-secret-visibility",
        f"{RESOURCE_PREFIX}:org:org-secret-repositories",
    }


def test_disabled_families_are_not_evaluated_at_all() -> None:
    live = [*LIVE_MATCHING, {"name": "GHOST", "visibility": "all"}]
    result, _ = _evaluate_secrets(live=live, assert_no_undeclared=False)
    assert result.records == []
    assert len(result.clean_fingerprints) == 2
    assert all("undeclared" not in o.key for o in result.outcomes)


def test_a_disabled_policy_skips_the_whole_leg() -> None:
    result, client = _evaluate_secrets(enabled=False)
    assert result.outcomes == []
    assert client.requested == []


def test_an_unreadable_secret_list_degrades_every_family() -> None:
    result, _ = _evaluate_secrets(live=ApiError(403, "Forbidden"))
    assert result.records == []
    assert result.clean_fingerprints == set()
    assert len(result.unresolved_fingerprints) == 3
    assert {o.status for o in result.outcomes} == {UNRESOLVED}


def test_an_unreadable_repository_list_degrades_only_its_family() -> None:
    repositories = {"ALPHA": ApiError(403, "Forbidden"), "BETA": ["org-config"]}
    result, _ = _evaluate_secrets(repositories=repositories)
    assert result.records == []
    statuses = {o.key: o.status for o in result.outcomes}
    assert statuses["org-secret-repositories"] == UNRESOLVED
    assert statuses["org-secret-visibility"] == OK
    assert statuses["org-secret-undeclared"] == OK


def test_org_secret_families_need_the_committed_config_text() -> None:
    config = ControlsConfig(controls=[], org_secrets=OrgSecretsPolicy(enabled=True))
    client = FakeApiClient(org_secrets=LIVE_MATCHING, secret_repositories=REPOS_MATCHING)
    result = evaluate_controls(config, client, org=ORG, config_jsonnet_text=None)
    assert result.outcomes == []
    assert client.requested == []


# --- list addressing: match and projection segments (issue #205) ---------------

# The real shape the grammar exists for: `GET /repos/{o}/{r}/rules/branches/main`
# answers with a LIST of rules, each keyed by `type`, and the required checks are
# a list of dicts inside one of them. Nothing here is dict-addressable.
BRANCH_RULES = [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {"type": "pull_request", "parameters": {"required_approving_review_count": 1}},
    {
        "type": "required_status_checks",
        "parameters": {
            "strict_required_status_checks_policy": True,
            "do_not_enforce_on_create": False,
            "required_status_checks": [
                {"context": "CI Summary"},
                {"context": "Check Summary", "integration_id": 15368},
            ],
        },
    },
]

BRANCH_RULES_ENDPOINT = "/repos/vig-os/devkit/rules/branches/main"


def test_select_path_matches_the_unique_element_of_a_root_list() -> None:
    assert (
        select_path(
            BRANCH_RULES,
            "[type=required_status_checks].parameters.strict_required_status_checks_policy",
        )
        is True
    )


def test_select_path_matches_the_unique_element_of_a_named_list() -> None:
    # The by-id ruleset endpoint nests the same array under `rules`.
    document = {"name": "Main protection", "rules": BRANCH_RULES}
    assert select_path(document, "rules[type=deletion].type") == "deletion"


def test_select_path_zero_matches_is_missing() -> None:
    # Never guess: a rule that is simply not configured must degrade the row
    # rather than be read as a neighbouring rule's value.
    assert select_path(BRANCH_RULES, "[type=required_signatures].parameters") is MISSING


def test_select_path_several_matches_is_missing() -> None:
    # Two rulesets can both contribute a rule of the same type to one branch;
    # which one the row meant is unknowable, so the row degrades.
    ambiguous = BRANCH_RULES + [{"type": "required_status_checks", "parameters": {}}]
    assert select_path(ambiguous, "[type=required_status_checks].parameters") is MISSING


def test_select_path_match_literal_is_compared_as_a_string_only() -> None:
    # No coercion, for the same reason `_equal` refuses it: `1` is not `"1"` and
    # `true` is not `"true"`, so a numeric field is never matched by a literal.
    assert select_path([{"id": 1, "x": "a"}], "[id=1].x") is MISSING
    assert select_path([{"on": True, "x": "a"}], "[on=True].x") is MISSING
    assert select_path([{"id": "1", "x": "a"}], "[id=1].x") == "a"


def test_select_path_match_on_a_non_list_is_missing() -> None:
    assert select_path({"rules": {"type": "deletion"}}, "rules[type=deletion].type") is MISSING
    assert select_path({"rules": BRANCH_RULES}, "nope[type=deletion]") is MISSING


def test_select_path_projects_a_field_out_of_every_element() -> None:
    assert select_path(
        BRANCH_RULES,
        "[type=required_status_checks].parameters.required_status_checks[].context",
    ) == ["CI Summary", "Check Summary"]


def test_select_path_projection_with_no_remaining_path_yields_the_elements() -> None:
    document = {"conditions": {"ref_name": {"include": ["refs/heads/main"]}}}
    assert select_path(document, "conditions.ref_name.include[]") == ["refs/heads/main"]


def test_select_path_projection_is_all_or_nothing() -> None:
    # A partial projection would silently compare a SHORTER set and read as
    # drift (or, worse, as clean) — so one element missing the field degrades
    # the whole row.
    document = {"checks": [{"context": "CI Summary"}, {"integration_id": 15368}]}
    assert select_path(document, "checks[].context") is MISSING


def test_select_path_projection_over_a_non_list_is_missing() -> None:
    assert select_path({"checks": {"context": "CI"}}, "checks[].context") is MISSING


def test_select_path_projection_over_an_empty_list_is_an_empty_list() -> None:
    # "this ruleset requires no status checks" is a legitimate live answer and
    # an assertable one — not an absence.
    assert select_path({"checks": []}, "checks[].context") == []


def test_select_path_bracket_values_may_contain_dots_and_spaces() -> None:
    # Status-check contexts are free text: `CodeQL Analysis (python)`,
    # `build.test`. Splitting the path on `.` inside brackets would break them.
    document = {"checks": [{"context": "CodeQL Analysis (python)"}, {"context": "build.test"}]}
    assert select_path(document, "checks[context=build.test].context") == "build.test"
    assert (
        select_path(document, "checks[context=CodeQL Analysis (python)].context")
        == "CodeQL Analysis (python)"
    )


def test_select_path_malformed_paths_are_missing() -> None:
    # Defence in depth: load_controls drops these rows, but a hand-built Control
    # must degrade rather than assert something the author did not write.
    malformed = (
        "rules[type=x",
        "rules]",
        "rules[]extra",
        "rules[=x]",
        "rules[type]",
        "[].",
        "rules[a[b]=c]",
        "",
    )
    for path in malformed:
        assert select_path({"rules": BRANCH_RULES}, path) is MISSING, path


def test_select_path_still_reads_a_plain_dotted_path() -> None:
    document = {"security_and_analysis": {"secret_scanning": {"status": "enabled"}}}
    assert select_path(document, "security_and_analysis.secret_scanning.status") == "enabled"


# --- set-valued assertions (issue #205) ----------------------------------------


def _checks_control(**overrides: object) -> Control:
    fields: dict[str, object] = {
        "key": "main-required-checks",
        "scope": "repo",
        "repository": "devkit",
        "title": "Required status checks on devkit main",
        "endpoint": "/repos/{org}/{repo}/rules/branches/main",
        "path": "[type=required_status_checks].parameters.required_status_checks[].context",
        "compare": "set",
        "expect": ["CI Summary", "Check Summary"],
    }
    fields.update(overrides)
    return _control(**fields)


def test_set_comparison_ignores_order_and_duplicates() -> None:
    # GitHub returns the check list in no guaranteed order, so an ordered
    # comparison would report drift every time the UI reshuffled it.
    control = _checks_control(expect=["Check Summary", "CI Summary"])
    result, _ = _evaluate(control, {BRANCH_RULES_ENDPOINT: BRANCH_RULES})
    assert result.records == []
    assert [o.status for o in result.outcomes] == [OK]


def test_set_comparison_reports_both_directions_of_a_mismatch() -> None:
    control = _checks_control(expect=["CI Summary", "Docs Summary"])
    result, _ = _evaluate(control, {BRANCH_RULES_ENDPOINT: BRANCH_RULES})
    (record,) = result.records
    # A dropped required check and an unexpected extra one are different
    # incidents; the body must name which is which without a re-read.
    assert "Docs Summary" in record.detail
    assert "Check Summary" in record.detail
    assert "missing" in record.detail
    assert "unexpected" in record.detail


def test_set_comparison_does_not_conflate_booleans_with_integers() -> None:
    control = _checks_control(path="values[]", expect=[1], endpoint="/repos/{org}/{repo}")
    result, _ = _evaluate(control, {"/repos/vig-os/devkit": {"values": [True]}})
    assert [o.status for o in result.outcomes] == [DRIFT]


def test_set_comparison_of_a_non_list_live_value_degrades() -> None:
    # A schema change from a list to a scalar is not drift, it is a row that no
    # longer means what it says.
    control = _checks_control(path="values[]", endpoint="/repos/{org}/{repo}")
    result, _ = _evaluate(control, {"/repos/vig-os/devkit": {"values": "CI Summary"}})
    assert result.records == []
    assert [o.status for o in result.outcomes] == [UNRESOLVED]
    assert result.clean_fingerprints == set()


def test_set_comparison_of_unnormalized_elements_degrades() -> None:
    # The live value is a list of DICTS: the row forgot its `[].context`
    # projection. Comparing raw dicts would report a permanent false drift, so
    # the row degrades and says so.
    control = _checks_control(
        path="[type=required_status_checks].parameters.required_status_checks"
    )
    result, _ = _evaluate(control, {BRANCH_RULES_ENDPOINT: BRANCH_RULES})
    assert result.records == []
    assert [o.status for o in result.outcomes] == [UNRESOLVED]
    assert any("main-required-checks" in note for note in result.notes)


def test_set_comparison_honours_a_tolerated_value() -> None:
    control = _checks_control(
        expect=["CI Summary", "Check Summary", "CodeQL Analysis (python)"],
        tolerated=["CI Summary", "Check Summary"],
    )
    result, _ = _evaluate(control, {BRANCH_RULES_ENDPOINT: BRANCH_RULES})
    assert result.records == []
    assert [o.status for o in result.outcomes] == [TOLERATED]
    assert result.clean_fingerprints == {_fingerprint(control)}


def test_set_comparison_renders_both_sides_sorted() -> None:
    control = _checks_control(expect=["Check Summary", "CI Summary"])
    result, _ = _evaluate(control, {BRANCH_RULES_ENDPOINT: BRANCH_RULES})
    (outcome,) = result.outcomes
    assert outcome.expected == "['CI Summary', 'Check Summary']"
    assert outcome.actual == "['CI Summary', 'Check Summary']"


def test_the_two_ruleset_criteria_assert_independently() -> None:
    # Issue #205's acceptance: the check SET and the strict-policy flag are two
    # rows over one memoized read, and they fail apart.
    checks = _checks_control()
    strict = _control(
        key="main-strict-checks",
        scope="repo",
        repository="devkit",
        endpoint="/repos/{org}/{repo}/rules/branches/main",
        path="[type=required_status_checks].parameters.strict_required_status_checks_policy",
        expect=True,
    )
    drifted = [
        rule
        if rule["type"] != "required_status_checks"
        else {
            **rule,
            "parameters": {
                "strict_required_status_checks_policy": False,
                "required_status_checks": [{"context": "CI Summary"}, {"context": "Check Summary"}],
            },
        }
        for rule in BRANCH_RULES
    ]
    client = FakeApiClient({BRANCH_RULES_ENDPOINT: drifted})
    result = evaluate_controls(ControlsConfig(controls=[checks, strict]), client, org=ORG)
    assert client.requested == [BRANCH_RULES_ENDPOINT]  # one read, two rows
    assert result.clean_fingerprints == {_fingerprint(checks)}
    (record,) = result.records
    assert record.resource == f"{RESOURCE_PREFIX}:devkit:main-strict-checks"


def test_an_ambiguous_ruleset_match_degrades_rather_than_guessing() -> None:
    # Two rulesets contributing required_status_checks to the same branch: the
    # row cannot know which was meant, so it degrades — never picks one.
    ambiguous = BRANCH_RULES + [{"type": "required_status_checks", "parameters": {}}]
    control = _checks_control()
    result, _ = _evaluate(control, {BRANCH_RULES_ENDPOINT: ambiguous})
    assert result.records == []
    assert result.unresolved_fingerprints == {_fingerprint(control)}
    assert [o.status for o in result.outcomes] == [UNRESOLVED]


# --- load-time validation of the new row fields (issue #205) -------------------


def _one_row(tmp_path: Path, body: str) -> list[Control]:
    path = tmp_path / "controls.toml"
    path.write_text('[[control]]\nkey = "row"\nscope = "org"\n' + body)
    return load_controls(path).controls


def test_load_controls_defaults_to_exact_comparison(tmp_path: Path) -> None:
    (control,) = _one_row(tmp_path, 'endpoint = "/orgs/{org}"\npath = "x"\nexpect = true\n')
    assert control.compare == "exact"


def test_load_controls_rejects_an_unknown_compare_mode(tmp_path: Path) -> None:
    body = 'endpoint = "/orgs/{org}"\npath = "x"\nexpect = true\ncompare = "subset"\n'
    assert _one_row(tmp_path, body) == []


def test_load_controls_rejects_a_set_row_whose_declared_value_is_not_a_list(
    tmp_path: Path,
) -> None:
    scalar_expect = 'endpoint = "/orgs/{org}"\npath = "x[]"\nexpect = "CI"\ncompare = "set"\n'
    assert _one_row(tmp_path, scalar_expect) == []
    scalar_tolerated = (
        'endpoint = "/orgs/{org}"\npath = "x[]"\nexpect = ["CI"]\n'
        'tolerated = "CI"\ncompare = "set"\n'
    )
    assert _one_row(tmp_path, scalar_tolerated) == []


def test_load_controls_rejects_a_set_row_with_non_primitive_elements(tmp_path: Path) -> None:
    # `expect = [{context = "CI"}]` cannot be set-compared; the row must project
    # `[].context` instead of shipping an assertion that can never pass.
    body = 'endpoint = "/orgs/{org}"\npath = "x[]"\ncompare = "set"\nexpect = [{context = "CI"}]\n'
    assert _one_row(tmp_path, body) == []


def test_load_controls_rejects_a_malformed_path(tmp_path: Path) -> None:
    for bad in ("rules[type=x", "rules[type]", "rules[=x]", "", "a..b"):
        body = 'endpoint = "/orgs/{org}"\npath = "' + bad + '"\nexpect = true\n'
        assert _one_row(tmp_path, body) == [], bad


# --- guard against the real shipped table --------------------------------------


def test_shipped_controls_table_is_well_formed(
    shipped_controls_path: Path, declared_repos: frozenset[str]
) -> None:
    # The shipped table is the durable record of every control otterdog cannot
    # model, so it is asserted here rather than only exercised through fixtures.
    config = load_controls(shipped_controls_path)
    assert len(config.controls) >= 12
    assert config.org_secrets is not None
    assert config.org_secrets.enabled is True

    identities = [(c.scope, c.repository, c.key) for c in config.controls]
    assert len(identities) == len(set(identities))  # one issue per identity

    for control in config.controls:
        assert control.reason.strip(), f"{control.key} documents no rationale"
        assert control.title.strip()
        if control.scope == "repo":
            assert control.repository in declared_repos, control.key
        if control.assertable:
            assert "{org}" in control.endpoint
            assert control.path
            assert control.expect is not UNSET


def test_shipped_controls_table_records_the_desired_value_not_the_stuck_one(
    shipped_controls_path: Path,
) -> None:
    # The known-stuck and pending-fix rows must assert what SHOULD be true and
    # tolerate today's value, so they turn green on their own once fixed.
    config = load_controls(shipped_controls_path)
    tolerated = {c.key: c for c in config.controls if c.has_tolerated}
    assert tolerated["sha-pinning"].expect is True
    assert tolerated["sha-pinning"].tolerated is False
    for key in ("secret-scanning-non-provider-patterns", "secret-scanning-validity-checks"):
        assert tolerated[key].expect == "enabled"
        assert tolerated[key].tolerated == "disabled"
