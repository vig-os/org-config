"""L1 tests for the plan-time org-secret reader-list check (issue #318).

``otterdog apply`` never live-patches an org secret whose committed value is a
``'********'`` dummy, so a repository added to such a secret's
``selected_repositories`` is green on review and never granted. The drift
layer's ``org-secret-repositories`` family already makes the comparison daily;
this check runs the SAME comparison at plan time and renders it into the plan
report. Four layers, all offline:

1. **Extraction** — the declaration now says whether its value is a dummy,
   with otterdog's own predicate (non-empty, all ``*``).
2. **Comparison** — the shared per-secret differ, the helper both the drift
   family and the plan report call.
3. **Rendering** — the markdown fragment, which must print the hand-grant
   command and say ``apply`` will not do it.
4. **The CLI mode**, whose exit code is 0 always (downstream the plan context
   is a required check, #268).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from drift_layer.secret_repositories import (
    check_secret_repositories,
    comparable_secrets,
    diff_secret_repositories,
    render_degraded_markdown,
    render_markdown,
)

from drift_layer.cli import main
from drift_layer.github_client import ApiError
from drift_layer.inventory import extract_declared_org_secrets

ORG = "fixture-org"

DECLARED = """
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
orgs.newOrgSecret('CANARY') {
  selected_repositories+: [
    'org-config',
  ],
  value: 'pass:org-config/CANARY',
  visibility: 'selected',
},
"""

LIVE = [
    {"name": "ALPHA", "visibility": "selected"},
    {"name": "BETA", "visibility": "selected"},
    {"name": "CANARY", "visibility": "selected"},
]
REPOS = {"ALPHA": ["org-config", "devkit"], "BETA": ["org-config"], "CANARY": ["org-config"]}


class FakeClient:
    """Answers the two org-secret reads from tables; records every read."""

    def __init__(self, live: object = None, repositories: dict[str, object] | None = None):
        self.live = LIVE if live is None else live
        self.repositories = REPOS if repositories is None else repositories
        self.requested: list[str] = []

    def list_org_secrets(self, org: str) -> list[dict]:
        self.requested.append(f"/orgs/{org}/actions/secrets")
        return _unwrap(self.live)

    def list_org_secret_repositories(self, org: str, name: str) -> list[str]:
        self.requested.append(f"/orgs/{org}/actions/secrets/{name}/repositories")
        return _unwrap(self.repositories[name])


def _unwrap(answer: object) -> object:
    if isinstance(answer, Exception):
        raise answer
    return answer


def _check(text: str = DECLARED, **client: object):
    fake = FakeClient(**client)  # type: ignore[arg-type]
    return check_secret_repositories(text, fake, org=ORG), fake


# --------------------------------------------------------------------------
# 1. Extraction
# --------------------------------------------------------------------------


def test_a_starred_value_is_a_dummy_and_a_provider_reference_is_not() -> None:
    declared = extract_declared_org_secrets(DECLARED)
    assert declared["ALPHA"].dummy_value is True
    assert declared["CANARY"].dummy_value is False


def test_an_absent_or_empty_value_is_not_a_dummy() -> None:
    # otterdog's `has_dummy_secret`: set, non-empty, and every character `*`.
    text = "orgs.newOrgSecret('BARE') {\n  visibility: 'selected',\n},\n"
    assert extract_declared_org_secrets(text)["BARE"].dummy_value is False
    text = "orgs.newOrgSecret('EMPTY') {\n  value: '',\n},\n"
    assert extract_declared_org_secrets(text)["EMPTY"].dummy_value is False


def test_only_the_canary_carries_a_real_value_in_the_committed_config(
    declared_jsonnet: str,
) -> None:
    declared = extract_declared_org_secrets(declared_jsonnet)
    assert {name for name, s in declared.items() if not s.dummy_value} == {"ORG_CONFIG_CANARY"}


# --------------------------------------------------------------------------
# 2. Comparison (the shared helper)
# --------------------------------------------------------------------------


def test_only_live_selected_secrets_are_comparable() -> None:
    declared = extract_declared_org_secrets(DECLARED)
    live = {
        "ALPHA": {"name": "ALPHA", "visibility": "selected"},
        "BETA": {"name": "BETA", "visibility": "all"},
    }
    assert [s.name for s in comparable_secrets(declared, live)] == ["ALPHA"]


def test_the_differ_splits_both_directions_and_carries_the_dummy_flag() -> None:
    declared = extract_declared_org_secrets(DECLARED)
    client = FakeClient(repositories={"ALPHA": ["org-config", "rogue"]})
    diff = diff_secret_repositories(client, ORG, declared["ALPHA"])
    assert diff.name == "ALPHA"
    assert diff.config_only == ("devkit",)
    assert diff.live_only == ("rogue",)
    assert diff.dummy_value is True
    assert diff.diverges


def test_matching_lists_are_clean() -> None:
    report, _ = _check()
    assert [d.name for d in report.compared] == ["ALPHA", "BETA", "CANARY"]
    assert report.divergent == ()
    assert report.unreadable is None


def test_a_declared_reader_not_granted_live_is_reported() -> None:
    report, _ = _check(repositories={**REPOS, "ALPHA": ["org-config"]})
    (diff,) = report.divergent
    assert (diff.name, diff.config_only, diff.live_only) == ("ALPHA", ("devkit",), ())


def test_a_secret_not_live_or_not_selected_live_is_not_compared_and_not_read() -> None:
    live = [{"name": "ALPHA", "visibility": "all"}, {"name": "CANARY", "visibility": "selected"}]
    report, client = _check(live=live)
    assert [d.name for d in report.compared] == ["CANARY"]
    assert {name for name, _ in report.not_compared} == {"ALPHA", "BETA"}
    assert all("ALPHA/repositories" not in path for path in client.requested)


def test_an_unreadable_secret_list_degrades_the_whole_check() -> None:
    report, _ = _check(live=ApiError(403, "GET /orgs/fixture-org/actions/secrets: Forbidden"))
    assert report.unreadable is not None and "403" in report.unreadable
    assert report.compared == ()


def test_a_rate_limited_secret_list_says_it_was_the_limiter() -> None:
    limited = ApiError(403, "Forbidden", {"x-ratelimit-remaining": "0"})
    report, _ = _check(live=limited)
    assert report.unreadable is not None and "rate limit" in report.unreadable


def test_an_unreadable_reader_list_degrades_only_that_secret() -> None:
    report, _ = _check(repositories={**REPOS, "BETA": ApiError(404, "Not Found")})
    assert [d.name for d in report.compared] == ["ALPHA", "CANARY"]
    ((name, detail),) = report.undetermined
    assert name == "BETA" and "404" in detail


# --------------------------------------------------------------------------
# 3. Rendering
# --------------------------------------------------------------------------


def test_markdown_on_matching_lists_says_so_without_a_table() -> None:
    report, _ = _check()
    text = render_markdown(report)
    assert text.startswith("### Declared org-secret readers")
    assert "All 3 `selected` org secrets" in text
    assert "|" not in text


def test_markdown_prints_the_hand_grant_and_says_apply_will_not() -> None:
    report, _ = _check(repositories={**REPOS, "ALPHA": ["org-config"]})
    text = render_markdown(report)
    assert "Declared, not granted live" in text
    assert "will **not**" in text
    assert (
        'gh api -X PUT "/orgs/fixture-org/actions/secrets/ALPHA/repositories/'
        '$(gh api /repos/fixture-org/devkit --jq .id)"'
    ) in text


def test_markdown_lets_apply_fix_a_real_valued_secret_without_a_command() -> None:
    report, _ = _check(repositories={**REPOS, "CANARY": []})
    text = render_markdown(report)
    assert "`CANARY`" in text
    assert "secrets/CANARY/repositories/" not in text  # no hand grant needed
    assert "reconciles" in text


def test_markdown_reports_a_live_only_reader_with_the_revoke_command() -> None:
    report, _ = _check(repositories={**REPOS, "BETA": ["org-config", "rogue"]})
    text = render_markdown(report)
    assert "Granted live, not declared" in text
    assert (
        'gh api -X DELETE "/orgs/fixture-org/actions/secrets/BETA/repositories/'
        '$(gh api /repos/fixture-org/rogue --jq .id)"'
    ) in text


def test_markdown_reports_unreadable_reads_as_not_a_finding() -> None:
    report, _ = _check(repositories={**REPOS, "BETA": ApiError(404, "Not Found")})
    assert "could not be checked" in render_markdown(report)
    report, _ = _check(live=ApiError(403, "Forbidden"))
    text = render_markdown(report)
    assert "could not read" in text and "403" in text


def test_degraded_markdown_names_the_reason() -> None:
    text = render_degraded_markdown("no token")
    assert text.startswith("### Declared org-secret readers")
    assert "could not be checked" in text and "no token" in text


# --------------------------------------------------------------------------
# 4. CLI mode
# --------------------------------------------------------------------------


def _config(tmp_path: Path) -> str:
    path = tmp_path / "org.jsonnet"
    path.write_text(DECLARED)
    return str(path)


def test_cli_org_secrets_report_exits_zero_and_prints_the_fragment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from drift_layer import cli

    seen: list[str] = []
    fake = FakeClient(repositories={**REPOS, "ALPHA": ["org-config"]})
    monkeypatch.setattr(cli, "RestGitHubClient", lambda repo, token: seen.append(token) or fake)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("DRIFT_REPOS_TOKEN", "full-plan-token")
    rc = main(["--org-secrets-report", "--config-jsonnet", _config(tmp_path), "--org", ORG])
    assert rc == 0
    assert seen == ["full-plan-token"]
    assert "secrets/ALPHA/repositories/" in capsys.readouterr().out


def test_cli_org_secrets_report_exits_zero_without_a_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("DRIFT_REPOS_TOKEN", raising=False)
    rc = main(["--org-secrets-report", "--config-jsonnet", _config(tmp_path), "--org", ORG])
    assert rc == 0
    assert "could not be checked" in capsys.readouterr().out


def test_cli_org_secrets_report_exits_zero_on_a_missing_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("DRIFT_REPOS_TOKEN", "t")
    missing = str(tmp_path / "nope.jsonnet")
    rc = main(["--org-secrets-report", "--config-jsonnet", missing, "--org", ORG])
    assert rc == 0
    assert "could not be checked" in capsys.readouterr().out


def test_cli_org_secrets_report_exits_zero_when_the_check_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from drift_layer import cli

    def explode(*args: object, **kwargs: object) -> object:
        raise RuntimeError("upstream changed shape")

    monkeypatch.setattr(cli, "check_secret_repositories", explode)
    monkeypatch.setenv("DRIFT_REPOS_TOKEN", "t")
    rc = main(["--org-secrets-report", "--config-jsonnet", _config(tmp_path), "--org", ORG])
    assert rc == 0
    out = capsys.readouterr().out
    assert "could not be checked" in out and "upstream changed shape" in out
