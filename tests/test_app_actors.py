"""L1 tests for the plan-time App-slug checks (issue #259).

Four layers, all offline:

1. **Extraction** from an evaluated org document — the fixture carries every
   App-shaped actor site otterdog 1.5.0 resolves through ``GET /apps/{slug}``
   *and* every neighbouring form that is not one, so widening the predicate
   fails a test rather than paging a reviewer on green config.
2. **Classification** of each slug's answer, with the client stubbed — first
   the ``/apps/{slug}`` write-path class, then the INDEPENDENT
   ``/orgs/{org}/installations`` read-path class, then the two ways a refusal is
   NOT a finding: a rate-limited ``403`` (transient) and an ``[[app_actor]]``
   allow-list entry (known by design, reported as suppressed).
3. **Rendering** — the markdown fragment folded into the plan report and the
   machine-readable JSON.
4. **The CLI mode**, whose exit code is 0 always — including when the check
   itself raises, because downstream the plan context is a required check
   (#268).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from drift_layer.app_actors import (
    SITE_BRANCH_PROTECTION_STATUS_CHECK,
    SITE_ENVIRONMENT_REVIEWER,
    SITE_RULESET_BYPASS_ACTOR,
    SITE_RULESET_STATUS_CHECK,
    SITES,
    STATE_RESOLVED,
    STATE_UNDETERMINED,
    STATE_UNRESOLVABLE,
    ActorSite,
    check_app_slugs,
    extract_app_actor_sites,
    render_json,
    render_markdown,
)
from drift_layer.cli import main
from drift_layer.github_client import ApiError, TruncatedResponseError

FIXTURES = Path(__file__).parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def fixture_config() -> dict:
    """The evaluated fixture org (``app_actors_org.jsonnet``)."""
    return json.loads((FIXTURES / "app_actors_org.json").read_text())


class StubClient:
    """Answers ``GET /apps/{slug}`` from a table; records every path asked."""

    def __init__(self, answers: dict[str, object | Exception]) -> None:
        self.answers = answers
        self.paths: list[str] = []

    def get_json(self, path: str) -> object:
        self.paths.append(path)
        answer = self.answers.get(path, ApiError(404, f"GET {path}: Not Found"))
        if isinstance(answer, Exception):
            raise answer
        return answer


def _ok(slug: str) -> dict:
    return {"id": 1, "slug": slug, "node_id": "MDM6QXBwMQ=="}


INSTALLATIONS = "/orgs/fixture-org/installations"


def _installations(*slugs: str, total: int | None = None) -> dict:
    entries = [{"app_id": i, "app_slug": slug} for i, slug in enumerate(slugs, start=1)]
    return {"total_count": len(entries) if total is None else total, "installations": entries}


def _answers(*, installed: tuple[str, ...] | None = None) -> dict[str, object | Exception]:
    """A green table: every slug resolves, every one needing it is installed."""
    answers: dict[str, object | Exception] = {f"/apps/{slug}": _ok(slug) for slug in ALL_SLUGS}
    answers[INSTALLATIONS] = _installations(*(INSTALLED if installed is None else installed))
    return answers


def _resolving(*slugs: str) -> StubClient:
    answers: dict[str, object | Exception] = {f"/apps/{slug}": _ok(slug) for slug in slugs}
    answers[INSTALLATIONS] = _installations(*INSTALLED)
    return StubClient(answers)


ALL_SLUGS = (
    "15368",
    "bpr-app",
    "checks-app",
    "gated-app",
    "github-actions",
    "org-bypass-app",
    "org-check-app",
    "reviewer-app",
)

#: The subset declared at a site whose READ path needs an org installation —
#: ruleset bypass actors and ruleset status checks. `bpr-app`, `github-actions`
#: and `reviewer-app` are deliberately absent: an installation is not required
#: (nor, for the implicit `github-actions`, ever present) at their sites.
INSTALLED = ("15368", "checks-app", "gated-app", "org-bypass-app", "org-check-app")


# --------------------------------------------------------------------------
# 1. Extraction
# --------------------------------------------------------------------------


def test_extraction_covers_all_four_write_path_sites(fixture_config: dict) -> None:
    """Every site otterdog resolves on `/apps/`, and only those."""
    found = {(s.slug, s.site, s.repo, s.resource) for s in extract_app_actor_sites(fixture_config)}
    assert found == {
        # ruleset bypass actors — org-level and repo-level, `:bypass_mode` stripped
        ("org-bypass-app", SITE_RULESET_BYPASS_ACTOR, None, "Org protection"),
        ("gated-app", SITE_RULESET_BYPASS_ACTOR, "alpha", "Main protection"),
        # ... and with no `isdigit()` escape on this site (models/ruleset.py:646-649)
        ("15368", SITE_RULESET_BYPASS_ACTOR, "alpha", "Main protection"),
        # ruleset status checks — non-numeric, non-`any`, space-free prefixes only
        ("org-check-app", SITE_RULESET_STATUS_CHECK, None, "Org protection"),
        ("checks-app", SITE_RULESET_STATUS_CHECK, "alpha", "Main protection"),
        # branch-protection status checks — explicit prefix, numeric included ...
        ("bpr-app", SITE_BRANCH_PROTECTION_STATUS_CHECK, "alpha", "main"),
        ("15368", SITE_BRANCH_PROTECTION_STATUS_CHECK, "alpha", "main"),
        # ... and the IMPLICIT `github-actions` an unprefixed check resolves to
        ("github-actions", SITE_BRANCH_PROTECTION_STATUS_CHECK, "alpha", "main"),
        # environment reviewers — the un-prefixed form only
        ("reviewer-app", SITE_ENVIRONMENT_REVIEWER, "alpha", "production"),
    }


def test_extraction_skips_roles_teams_users_and_escaped_prefixes(fixture_config: dict) -> None:
    """The neighbouring forms that are NOT an `/apps/` lookup produce no site."""
    slugs = {site.slug for site in extract_app_actor_sites(fixture_config)}
    # `#RepositoryAdmin` / `#OrganizationAdmin` roles, `@org/team`, `@user`
    assert not any(slug.startswith(("#", "@")) for slug in slugs)
    assert "RepositoryAdmin" not in slugs
    assert "fixture-org/reviewers" not in slugs
    assert "c-vigo" not in slugs
    # ruleset status checks: `any:`, a spaced prefix, an unprefixed context and
    # the numeric form all escape before the lookup (models/ruleset.py:181-185)
    assert "any" not in slugs
    assert "spaced prefix" not in slugs
    assert "plain check" not in slugs
    pairs = {(s.slug, s.site) for s in extract_app_actor_sites(fixture_config)}
    assert ("15368", SITE_RULESET_STATUS_CHECK) not in pairs


def test_extraction_tolerates_absent_and_null_sections() -> None:
    """A repo with no rulesets, a null `required_status_checks`, an empty doc."""
    assert extract_app_actor_sites({}) == []
    assert extract_app_actor_sites({"repositories": [{"name": "beta"}]}) == []
    null_ruleset = {"name": "r", "required_status_checks": None}
    null_checks = {"repositories": [{"name": "beta", "rulesets": [null_ruleset]}]}
    assert extract_app_actor_sites(null_checks) == []


def test_extraction_is_deterministically_ordered(fixture_config: dict) -> None:
    sites = extract_app_actor_sites(fixture_config)
    assert sites == sorted(sites)


@pytest.mark.skipif(shutil.which("jsonnet") is None, reason="no jsonnet binary on PATH")
def test_committed_fixture_json_matches_a_fresh_evaluation() -> None:
    """The committed evaluated fixture is exactly its jsonnet source.

    The runner produces the real document with otterdog's own
    ``jsonnet_evaluate_file`` (rjsonnet); go-jsonnet agrees with it on this
    repo's committed config, so either evaluator anchors the fixture.
    """
    fresh = _evaluate(FIXTURES / "app_actors_org.jsonnet")
    assert fresh == json.loads((FIXTURES / "app_actors_org.json").read_text())


def _evaluate(path: Path) -> dict:
    result = subprocess.run(  # noqa: S603
        [shutil.which("jsonnet") or "jsonnet", str(path)],
        capture_output=True,
        check=True,
        text=True,
    )
    return json.loads(result.stdout)


@pytest.mark.skipif(shutil.which("jsonnet") is None, reason="no jsonnet binary on PATH")
def test_the_committed_config_declares_exactly_these_app_slugs() -> None:
    """Ground truth on the REAL config, in the spirit of ``DECLARED_REPOS``.

    Three slugs, twelve sites. `github-actions` is not written anywhere in the
    jsonnet — it is the implicit slug tessera's two un-prefixed
    branch-protection status checks resolve to, which is precisely the site a
    literal read of the config text could not see. Update this set deliberately
    when the config declares a new App.
    """
    config = _evaluate(REPO_ROOT / "otterdog" / "vig-os" / "vig-os.jsonnet")
    sites = extract_app_actor_sites(config)
    assert {site.slug for site in sites} == {
        "commit-action-bot",
        "github-actions",
        "vig-os-release-app",
    }
    assert {site.site for site in sites} == {
        SITE_RULESET_BYPASS_ACTOR,
        SITE_BRANCH_PROTECTION_STATUS_CHECK,
    }
    assert len(sites) == 12


# --------------------------------------------------------------------------
# 2. Classification
# --------------------------------------------------------------------------


def test_every_declared_slug_is_asked_exactly_once(fixture_config: dict) -> None:
    """One GET per unique slug, plus exactly one installations read for the org."""
    client = _resolving(*ALL_SLUGS)
    check_app_slugs(fixture_config, client, org="fixture-org")
    assert sorted(client.paths) == sorted([*(f"/apps/{slug}" for slug in ALL_SLUGS), INSTALLATIONS])


def test_a_200_resolves(fixture_config: dict) -> None:
    report = check_app_slugs(fixture_config, _resolving(*ALL_SLUGS), org="fixture-org")
    assert {o.state for o in report.outcomes} == {STATE_RESOLVED}
    assert report.unresolvable == ()
    assert report.not_installed == ()
    assert report.notes == ()


@pytest.mark.parametrize("status", [403, 404])
def test_a_403_or_404_is_unresolvable(fixture_config: dict, status: int) -> None:
    answers = _answers()
    answers["/apps/gated-app"] = ApiError(status, "GET /apps/gated-app: Forbidden")
    report = check_app_slugs(fixture_config, StubClient(answers), org="fixture-org")
    unresolvable = report.unresolvable
    assert [o.slug for o in unresolvable] == ["gated-app"]
    assert unresolvable[0].status == status
    assert unresolvable[0].sites == (
        ActorSite("gated-app", SITE_RULESET_BYPASS_ACTOR, "alpha", "Main protection"),
    )


@pytest.mark.parametrize(
    "error",
    [
        ApiError(0, "GET /apps/gated-app: connection reset"),
        ApiError(500, "GET /apps/gated-app: Internal Server Error"),
        ApiError(401, "GET /apps/gated-app: Unauthorized"),
        TruncatedResponseError("/apps/gated-app"),
    ],
)
def test_a_read_that_did_not_answer_is_undetermined_not_a_finding(
    fixture_config: dict, error: ApiError
) -> None:
    """Never assert "apply will fail" from a read that failed for another reason."""
    answers = _answers()
    answers["/apps/gated-app"] = error
    report = check_app_slugs(fixture_config, StubClient(answers), org="fixture-org")
    assert report.unresolvable == ()
    assert [o.slug for o in report.undetermined] == ["gated-app"]
    assert report.undetermined[0].state == STATE_UNDETERMINED
    assert report.notes and "gated-app" in report.notes[0]


@pytest.mark.parametrize(
    "headers",
    [
        {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1780000000"},
        {"retry-after": "60"},
    ],
    ids=["primary-limit", "secondary-limit"],
)
def test_a_rate_limited_403_is_undetermined_not_a_finding(
    fixture_config: dict, headers: dict[str, str]
) -> None:
    """GitHub answers 403 for the limiter too, with the same reason phrase (#259).

    The step that runs immediately before this check is a full org read on the
    same token, so this is the likeliest 403 of the two — and rendering it as
    "apply WILL fail on these" would diagnose the config from the harness's own
    exhaustion.
    """
    answers = _answers()
    answers["/apps/gated-app"] = ApiError(403, "GET /apps/gated-app: Forbidden", headers)
    report = check_app_slugs(fixture_config, StubClient(answers), org="fixture-org")
    assert report.unresolvable == ()
    assert [o.slug for o in report.undetermined] == ["gated-app"]
    assert "rate limit" in report.undetermined[0].detail


def test_a_permission_403_carries_no_rate_limit_headers_and_stays_a_finding(
    fixture_config: dict,
) -> None:
    """The #256 true positive must survive the rate-limit escape."""
    answers = _answers()
    answers["/apps/gated-app"] = ApiError(
        403, "GET /apps/gated-app: Forbidden", {"x-ratelimit-remaining": "4998"}
    )
    report = check_app_slugs(fixture_config, StubClient(answers), org="fixture-org")
    assert [o.slug for o in report.unresolvable] == ["gated-app"]


def test_a_rate_limited_installations_read_degrades_and_says_why(
    fixture_config: dict,
) -> None:
    answers = _answers()
    answers[INSTALLATIONS] = ApiError(403, f"GET {INSTALLATIONS}: Forbidden", {"retry-after": "42"})
    report = check_app_slugs(fixture_config, StubClient(answers), org="fixture-org")
    assert report.not_installed == ()
    assert report.installations is not None and not report.installations.complete
    assert "retry-after" in report.installations.detail


# --------------------------------------------------------------------------
# 2b. Suppression — the `[[app_actor]]` allow-list (#259)
# --------------------------------------------------------------------------

REASON = "private App owned by a sibling org; unreadable to an installation token"


def test_an_allowlisted_unresolvable_slug_is_suppressed_not_a_finding(
    fixture_config: dict,
) -> None:
    answers = _answers()
    answers["/apps/gated-app"] = ApiError(403, "GET /apps/gated-app: Forbidden")
    report = check_app_slugs(
        fixture_config,
        StubClient(answers),
        org="fixture-org",
        allowlist={"gated-app": REASON},
    )
    assert report.unresolvable == ()
    assert [o.slug for o in report.suppressed] == ["gated-app"]
    assert report.suppressed[0].allowlisted_reason == REASON
    # The state itself is untouched — the allow-list changes how it is REPORTED,
    # never what was observed.
    assert report.suppressed[0].state == STATE_UNRESOLVABLE


def test_an_allowlisted_uninstalled_slug_is_suppressed_too(fixture_config: dict) -> None:
    """Both finding classes are suppressible by one entry, for one slug."""
    answers = _answers(installed=("15368", "checks-app", "gated-app", "org-check-app"))
    report = check_app_slugs(
        fixture_config,
        StubClient(answers),
        org="fixture-org",
        allowlist={"org-bypass-app": REASON},
    )
    assert report.not_installed == ()
    assert [o.slug for o in report.suppressed] == ["org-bypass-app"]


def test_the_allowlist_matches_case_insensitively(fixture_config: dict) -> None:
    answers = _answers()
    answers["/apps/gated-app"] = ApiError(404, "GET /apps/gated-app: Not Found")
    report = check_app_slugs(
        fixture_config, StubClient(answers), org="fixture-org", allowlist={"GATED-App": REASON}
    )
    assert report.unresolvable == ()
    assert [o.slug for o in report.suppressed] == ["gated-app"]


def test_an_allowlisted_slug_that_resolves_is_not_reported_at_all(
    fixture_config: dict,
) -> None:
    """The allow-list suppresses findings, it does not invent them."""
    report = check_app_slugs(
        fixture_config, StubClient(_answers()), org="fixture-org", allowlist={"gated-app": REASON}
    )
    assert report.suppressed == ()
    assert report.unresolvable == () and report.not_installed == ()


def test_markdown_names_a_suppressed_slug_with_its_reason(fixture_config: dict) -> None:
    """Visible suppression: the slug and the why stay on every run."""
    answers = _answers()
    answers["/apps/gated-app"] = ApiError(403, "GET /apps/gated-app: Forbidden")
    report = check_app_slugs(
        fixture_config, StubClient(answers), org="fixture-org", allowlist={"gated-app": REASON}
    )
    body = render_markdown(report)
    assert "Known and suppressed" in body
    assert REASON in body
    assert "`apply` will fail on these" not in body
    # And never folded into the clean sentence, which would hide it.
    assert "Nothing here blocks" not in body


def test_json_records_the_allowlist_reason(fixture_config: dict) -> None:
    answers = _answers()
    answers["/apps/gated-app"] = ApiError(403, "GET /apps/gated-app: Forbidden")
    report = check_app_slugs(
        fixture_config, StubClient(answers), org="fixture-org", allowlist={"gated-app": REASON}
    )
    document = render_json(report)
    assert document["suppressed"] == 1
    assert document["unresolvable"] == 0
    entry = next(s for s in document["slugs"] if s["slug"] == "gated-app")
    assert entry["allowlisted_reason"] == REASON


def test_markdown_reports_a_rate_limited_read_as_not_checked(fixture_config: dict) -> None:
    answers = _answers()
    answers["/apps/gated-app"] = ApiError(
        403, "GET /apps/gated-app: Forbidden", {"retry-after": "60"}
    )
    body = render_markdown(check_app_slugs(fixture_config, StubClient(answers), org="fixture-org"))
    assert "could not be checked" in body
    assert "`apply` will fail on these" not in body


def test_one_slug_carries_every_site_that_declares_it(fixture_config: dict) -> None:
    """`15368` is declared at two sites; the report keeps both under one GET."""
    answers = _answers()
    answers["/apps/15368"] = ApiError(404, "GET /apps/15368: Not Found")
    report = check_app_slugs(fixture_config, StubClient(answers), org="fixture-org")
    (outcome,) = report.unresolvable
    assert {site.site for site in outcome.sites} == {
        SITE_RULESET_BYPASS_ACTOR,
        SITE_BRANCH_PROTECTION_STATUS_CHECK,
    }


# --------------------------------------------------------------------------
# 2b. The second, INDEPENDENT class: declared but not installed on the org
# --------------------------------------------------------------------------


def test_a_slug_absent_from_the_org_installations_is_flagged(fixture_config: dict) -> None:
    answers = _answers(installed=tuple(s for s in INSTALLED if s != "gated-app"))
    report = check_app_slugs(fixture_config, StubClient(answers), org="fixture-org")
    assert [o.slug for o in report.not_installed] == ["gated-app"]
    # ... and it is NOT an `/apps/` finding: the two classes are independent
    assert report.unresolvable == ()


def test_the_two_classes_are_independent_not_an_elif(fixture_config: dict) -> None:
    """One slug can fail both checks, and each is reported on its own terms."""
    answers = _answers(installed=tuple(s for s in INSTALLED if s != "gated-app"))
    answers["/apps/gated-app"] = ApiError(403, "GET /apps/gated-app: Forbidden")
    report = check_app_slugs(fixture_config, StubClient(answers), org="fixture-org")
    assert [o.slug for o in report.unresolvable] == ["gated-app"]
    assert [o.slug for o in report.not_installed] == ["gated-app"]


def test_installation_slugs_are_compared_case_folded(fixture_config: dict) -> None:
    """GitHub slugs are lowercase; a jsonnet declaration is free text."""
    answers = _answers(installed=tuple(s.upper() for s in INSTALLED))
    report = check_app_slugs(fixture_config, StubClient(answers), org="fixture-org")
    assert report.not_installed == ()


def test_only_sites_whose_read_path_needs_an_installation_are_checked(
    fixture_config: dict,
) -> None:
    """The implicit `github-actions` is never an org installation — and must

    not be a finding: this org's own branch-protection rules declare it and
    plan clean. Same for the other two non-ruleset sites.
    """
    report = check_app_slugs(fixture_config, _resolving(*ALL_SLUGS), org="fixture-org")
    by_slug = {o.slug: o for o in report.outcomes}
    assert by_slug["github-actions"].installed is None
    assert by_slug["bpr-app"].installed is None
    assert by_slug["reviewer-app"].installed is None
    assert by_slug["gated-app"].installed is True
    assert by_slug["checks-app"].installed is True


def test_no_installations_read_when_no_site_needs_one() -> None:
    config = {
        "repositories": [
            {
                "name": "alpha",
                "branch_protection_rules": [{"pattern": "main", "required_status_checks": ["CI"]}],
            }
        ]
    }
    client = StubClient({"/apps/github-actions": _ok("github-actions")})
    report = check_app_slugs(config, client, org="fixture-org")
    assert client.paths == ["/apps/github-actions"]
    assert report.installations is None


def test_a_partial_installations_list_is_reported_never_compared_against(
    fixture_config: dict,
) -> None:
    """`total_count` beyond the returned page: absence would prove nothing.

    otterdog's own read does NOT paginate here (``org_client.py:484-491``), so
    past one page it drops more actors than this check could predict — that is
    reported, not mirrored.
    """
    answers = _answers()
    answers[INSTALLATIONS] = _installations(*INSTALLED, total=200)
    report = check_app_slugs(fixture_config, StubClient(answers), org="fixture-org")
    assert report.not_installed == ()
    assert all(o.installed is None for o in report.outcomes)
    assert report.installations is not None and not report.installations.complete
    assert any("total_count" in note for note in report.notes)


@pytest.mark.parametrize(
    "answer",
    [
        ApiError(403, "GET /orgs/fixture-org/installations: Forbidden"),
        TruncatedResponseError("/orgs/fixture-org/installations"),
        {"total_count": 3},
        [],
    ],
)
def test_an_unreadable_installations_list_degrades_only_its_own_class(
    fixture_config: dict, answer: object
) -> None:
    answers = _answers()
    answers[INSTALLATIONS] = answer
    answers["/apps/gated-app"] = ApiError(403, "GET /apps/gated-app: Forbidden")
    report = check_app_slugs(fixture_config, StubClient(answers), org="fixture-org")
    # the `/apps/` class still reports ...
    assert [o.slug for o in report.unresolvable] == ["gated-app"]
    # ... while the installation class claims nothing
    assert report.not_installed == ()
    assert report.notes


# --------------------------------------------------------------------------
# 3. Rendering
# --------------------------------------------------------------------------


def test_markdown_separates_failing_sites_from_the_silently_dropped_one(
    fixture_config: dict,
) -> None:
    answers = _answers()
    answers["/apps/gated-app"] = ApiError(403, "GET /apps/gated-app: Forbidden")
    answers["/apps/reviewer-app"] = ApiError(403, "GET /apps/reviewer-app: Forbidden")
    body = render_markdown(check_app_slugs(fixture_config, StubClient(answers), org="fixture-org"))

    fail_heading = body.index("`apply` will fail")
    drop_heading = body.index("silently dropped")
    assert fail_heading < body.index("`gated-app`") < drop_heading
    assert drop_heading < body.index("`reviewer-app`")
    # the clean slugs are not listed as findings
    assert "`checks-app`" not in body


def test_markdown_on_clean_config_says_so_without_a_table(fixture_config: dict) -> None:
    report = check_app_slugs(fixture_config, _resolving(*ALL_SLUGS), org="fixture-org")
    body = render_markdown(report)
    assert "8" in body
    assert "|" not in body


def test_markdown_lists_the_not_installed_class_in_its_own_table(
    fixture_config: dict,
) -> None:
    answers = _answers(installed=tuple(s for s in INSTALLED if s != "gated-app"))
    body = render_markdown(check_app_slugs(fixture_config, StubClient(answers), org="fixture-org"))
    assert "not installed on `fixture-org`" in body
    assert "`apply` will fail" not in body  # a different class, not conflated
    assert "`gated-app`" in body
    assert "`checks-app`" not in body


def test_markdown_says_the_check_covers_declared_config_only(fixture_config: dict) -> None:
    report = check_app_slugs(fixture_config, _resolving(*ALL_SLUGS), org="fixture-org")
    body = render_markdown(report)
    assert "declared" in body
    assert "live ruleset read" in body


def test_markdown_reports_an_undetermined_read_separately(fixture_config: dict) -> None:
    answers = _answers()
    answers["/apps/gated-app"] = ApiError(0, "GET /apps/gated-app: connection reset")
    body = render_markdown(check_app_slugs(fixture_config, StubClient(answers), org="fixture-org"))
    assert "could not be checked" in body
    assert "`gated-app`" in body


def test_json_is_machine_readable_and_complete(fixture_config: dict) -> None:
    answers = _answers()
    answers["/apps/gated-app"] = ApiError(403, "GET /apps/gated-app: Forbidden")
    document = render_json(check_app_slugs(fixture_config, StubClient(answers), org="fixture-org"))
    assert json.loads(json.dumps(document)) == document  # plain JSON, no dataclasses
    assert document["org"] == "fixture-org"
    assert document["checked"] == len(ALL_SLUGS)
    assert document["unresolvable"] == 1
    assert document["undetermined"] == 0
    gated = next(s for s in document["slugs"] if s["slug"] == "gated-app")
    assert gated["state"] == STATE_UNRESOLVABLE
    assert gated["status"] == 403
    assert document["not_installed"] == 0
    assert document["installations_read"] is True
    assert gated["installed"] is True
    assert gated["sites"] == [
        {
            "site": SITE_RULESET_BYPASS_ACTOR,
            "repo": "alpha",
            "resource": "Main protection",
            "fails_apply": True,
            "read_needs_installation": True,
        }
    ]


def test_the_site_table_marks_exactly_one_site_as_silently_skipped() -> None:
    """Three sites fail the apply; the environment reviewer is dropped instead."""
    assert {key for key, site in SITES.items() if not site.fails_apply} == {
        SITE_ENVIRONMENT_REVIEWER
    }
    assert len(SITES) == 4


# --------------------------------------------------------------------------
# 4. CLI mode
# --------------------------------------------------------------------------


def test_cli_app_actors_report_exits_zero_and_writes_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from drift_layer import cli

    answers = _answers()
    answers["/apps/gated-app"] = ApiError(403, "GET /apps/gated-app: Forbidden")
    monkeypatch.setattr(cli, "RestGitHubClient", lambda repo, token: StubClient(answers))
    monkeypatch.setenv("GITHUB_TOKEN", "t")

    out = tmp_path / "app-actors.json"
    rc = main(
        [
            "--app-actors-report",
            "--config-json",
            str(FIXTURES / "app_actors_org.json"),
            "--org",
            "fixture-org",
            "--json-out",
            str(out),
        ]
    )
    assert rc == 0
    assert "`gated-app`" in capsys.readouterr().out
    assert json.loads(out.read_text())["unresolvable"] == 1


def test_cli_app_actors_report_exits_zero_without_a_token(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing token degrades visibly — it never reddens the plan job."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("DRIFT_REPOS_TOKEN", raising=False)
    config = str(FIXTURES / "app_actors_org.json")
    rc = main(["--app-actors-report", "--config-json", config, "--org", "x"])
    assert rc == 0
    assert "could not be checked" in capsys.readouterr().out


def test_cli_app_actors_report_exits_zero_on_a_missing_config(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    rc = main(["--app-actors-report", "--config-json", str(tmp_path / "nope.json"), "--org", "x"])
    assert rc == 0
    assert "could not be checked" in capsys.readouterr().out


def test_cli_app_actors_report_never_touches_the_transport_without_actors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A config declaring no App actor costs zero calls — asserted, not assumed."""
    from drift_layer import cli

    class Refusing:
        def get_json(self, path: str) -> object:
            raise AssertionError(f"no call expected, got {path}")

    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"github_id": "x", "repositories": []}))
    monkeypatch.setattr(cli, "RestGitHubClient", lambda repo, token: Refusing())
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    assert main(["--app-actors-report", "--config-json", str(empty), "--org", "x"]) == 0
    assert "All 0 declared App slugs resolved" in capsys.readouterr().out


def test_cli_app_actors_report_reads_the_repos_token(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`DRIFT_REPOS_TOKEN` is the name `plan.yml` exports the full token under.

    `GITHUB_TOKEN` stays reserved for the issues:write-narrowed credential
    (`drift.yml`, `cli.py`'s docstring), so the mode must run on the repos token
    alone.
    """
    from drift_layer import cli

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("DRIFT_REPOS_TOKEN", "full-plan-token")
    seen: list[str] = []
    monkeypatch.setattr(
        cli, "RestGitHubClient", lambda repo, token: seen.append(token) or StubClient(_answers())
    )
    rc = main(
        [
            "--app-actors-report",
            "--config-json",
            str(FIXTURES / "app_actors_org.json"),
            "--org",
            "fixture-org",
        ]
    )
    assert rc == 0
    assert seen == ["full-plan-token"]
    assert "could not be checked" not in capsys.readouterr().out


def test_cli_app_actors_report_suppresses_an_allowlisted_slug(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """End to end: `--allowlist` moves a finding into "known and suppressed"."""
    from drift_layer import cli

    answers = _answers()
    answers["/apps/gated-app"] = ApiError(403, "GET /apps/gated-app: Forbidden")
    monkeypatch.setattr(cli, "RestGitHubClient", lambda repo, token: StubClient(answers))
    monkeypatch.setenv("DRIFT_REPOS_TOKEN", "t")
    allowlist = tmp_path / "drift-allowlist.toml"
    allowlist.write_text(f'[[app_actor]]\nslug = "gated-app"\nreason = "{REASON}"\n')

    out = tmp_path / "app-actors.json"
    rc = main(
        [
            "--app-actors-report",
            "--config-json",
            str(FIXTURES / "app_actors_org.json"),
            "--org",
            "fixture-org",
            "--allowlist",
            str(allowlist),
            "--json-out",
            str(out),
        ]
    )
    assert rc == 0
    printed = capsys.readouterr().out
    assert "Known and suppressed" in printed and REASON in printed
    assert "`apply` will fail on these" not in printed
    assert json.loads(out.read_text())["suppressed"] == 1


def test_cli_app_actors_report_exits_zero_when_the_check_raises(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The guarantee lives in the mode, not in the workflow's `if !` wrapper.

    Downstream this job's context is a required check on `main` (#268), so an
    unforeseen exception in an advisory read must degrade to a visible fragment,
    never to a traceback and a non-zero status.
    """
    from drift_layer import cli

    def explode(*args: object, **kwargs: object) -> object:
        raise RuntimeError("upstream changed shape")

    monkeypatch.setattr(cli, "check_app_slugs", explode)
    monkeypatch.setenv("DRIFT_REPOS_TOKEN", "t")
    rc = main(
        [
            "--app-actors-report",
            "--config-json",
            str(FIXTURES / "app_actors_org.json"),
            "--org",
            "fixture-org",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "could not be checked" in out
    assert "upstream changed shape" in out


def test_cli_app_actors_report_exits_zero_when_the_json_cannot_be_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """And the fragment then says so, rather than a good one being overwritten."""
    from drift_layer import cli

    monkeypatch.setattr(cli, "RestGitHubClient", lambda repo, token: StubClient(_answers()))
    monkeypatch.setenv("DRIFT_REPOS_TOKEN", "t")
    rc = main(
        [
            "--app-actors-report",
            "--config-json",
            str(FIXTURES / "app_actors_org.json"),
            "--org",
            "fixture-org",
            "--json-out",
            str(tmp_path / "no-such-dir" / "app-actors.json"),
        ]
    )
    assert rc == 0
    assert "could not be checked" in capsys.readouterr().out


def test_real_client_resolves_a_slug_over_a_canned_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end through the REAL transport, `urlopen` stubbed (#258/#264)."""
    from drift_layer import github_client
    from tests.conftest import stub_response

    monkeypatch.setattr(
        github_client.urllib.request,
        "urlopen",
        lambda req, *a, **k: stub_response(_ok("gated-app")),
    )
    client = github_client.RestGitHubClient("vig-os/org-config", "token")
    config = {"rulesets": [{"name": "r", "bypass_actors": ["gated-app"]}]}
    report = check_app_slugs(config, client, org="vig-os")
    assert [o.state for o in report.outcomes] == [STATE_RESOLVED]
