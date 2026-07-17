"""L1 tests for the CLI pipeline and the client executor (fake client edge)."""

from __future__ import annotations

from pathlib import Path

from drift_layer.cli import build_actions, build_inventory_records, reconcile_populations, run
from drift_layer.github_client import execute
from drift_layer.models import Issue
from drift_layer.parser import parse_plan
from drift_layer.reconcile import DRIFT_LABELS, INVENTORY_LABELS, render_body

NOW = "2026-07-17 03:00 UTC"


class FakeClient:
    """In-memory GitHubClient stand-in recording every call (injected edge)."""

    def __init__(
        self, issues: list[Issue] | None = None, org_repos: list[str] | None = None
    ) -> None:
        self.issues = issues or []
        self.org_repos = org_repos or []
        self.created: list[tuple[str, str, tuple[str, ...]]] = []
        self.updated: list[tuple[int, str, str]] = []
        self.comments: list[tuple[int, str]] = []
        self.closed: list[int] = []
        self._next = 100

    def list_open_drift_issues(self) -> list[Issue]:
        return self.issues

    def list_org_repos(self, org: str) -> list[str]:
        return self.org_repos

    def create_issue(self, title: str, body: str, labels: tuple[str, ...]) -> int:
        self.created.append((title, body, labels))
        number = self._next
        self._next += 1
        return number

    def update_issue(self, number: int, title: str, body: str) -> None:
        self.updated.append((number, title, body))

    def add_comment(self, number: int, body: str) -> None:
        self.comments.append((number, body))

    def close_issue(self, number: int) -> None:
        self.closed.append(number)


class ExplodingReposClient(FakeClient):
    """Repos read raises — models a sweep failure (403 / network / API error)."""

    def list_org_repos(self, org: str) -> list[str]:
        msg = "boom: org repos unreadable"
        raise RuntimeError(msg)


def test_build_actions_end_to_end_from_pr42(plan_pr42: str, allowlist_path: Path) -> None:
    # vs-dolt is allow-listed, so a fresh repo yields no actions.
    actions = build_actions(
        plan_pr42, [], allowlist_path=str(allowlist_path), now=NOW, default_org="vig-os"
    )
    assert actions == []


def test_build_actions_pr42_without_allowlist_opens_one(plan_pr42: str) -> None:
    actions = build_actions(plan_pr42, [], allowlist_path=None, now=NOW)
    assert len(actions) == 1
    assert actions[0].kind == "open"


def test_execute_open_creates_issue_with_labels() -> None:
    client = FakeClient()
    actions = build_actions(
        """Project vig-os[github_id=vig-os] (1/1)

  ~ repository[name="foo"] {
    ~ private = false -> true
  ~ }

  Plan: 0 to add, 1 to change, 0 to delete.
""",
        [],
        allowlist_path=None,
        now=NOW,
    )
    execute(actions, client, DRIFT_LABELS)
    assert len(client.created) == 1
    title, body, labels = client.created[0]
    assert title == 'Drift: repository[name="foo"]'
    assert labels == ("drift", "critical")
    assert "drift-fingerprint" in body


def test_execute_close_comments_then_closes() -> None:
    record_body = render_body(
        parse_plan(
            """Project vig-os[github_id=vig-os] (1/1)

  ~ repository[name="gone"] {
    ~ private = false -> true
  ~ }

  Plan: 0 to add, 1 to change, 0 to delete.
"""
        ).records[0],
        now="old",
    )
    existing = [Issue(number=55, title="Drift: gone", body=record_body)]
    client = FakeClient(existing)
    actions = build_actions(
        "Plan: 0 to add, 0 to change, 0 to delete.\n", existing, allowlist_path=None, now=NOW
    )
    execute(actions, client, DRIFT_LABELS)
    assert client.comments == [(55, actions[0].comment)]
    assert client.closed == [55]


# --- inventory sweep pipeline (issue #21) -------------------------------------

DECLARE_TWO = "orgs.newRepo('alpha') {}\norgs.newRepo('beta') {}\n"

PLAN_ONE_DRIFT = """Project vig-os[github_id=vig-os] (1/1)

  ~ repository[name="alpha"] {
    ~ private = false -> true
  ~ }

  Plan: 0 to add, 1 to change, 0 to delete.
"""


def test_build_inventory_records_flags_undeclared_live_repo() -> None:
    records = build_inventory_records(
        DECLARE_TWO,
        ["alpha", "beta", "rogue"],
        org="vig-os",
        allowlist_path=None,
    )
    assert len(records) == 1
    assert records[0].resource == "repository-inventory:rogue"


def test_reconcile_populations_keeps_plan_and_inventory_independent() -> None:
    inv_records = build_inventory_records(
        DECLARE_TWO, ["alpha", "beta", "rogue"], org="vig-os", allowlist_path=None
    )
    plan_records = parse_plan(PLAN_ONE_DRIFT).records
    plan_actions, inv_actions = reconcile_populations(plan_records, inv_records, [], now=NOW)
    assert [a.kind for a in plan_actions] == ["open"]
    assert [a.kind for a in inv_actions] == ["open"]
    assert plan_actions[0].title == 'Drift: repository[name="alpha"]'
    assert "rogue" in inv_actions[0].title


def test_reconcile_populations_degrades_leaving_inventory_issues_untouched() -> None:
    # Sweep failed (inventory_records is None): plan drift must still reconcile,
    # and existing inventory issues must NOT be closed as phantom-resolved.
    inv_issue = Issue(
        number=9,
        title="Undeclared repository: rogue",
        body="<!-- drift-fingerprint: deadbeefdeadbeef -->",
        labels=("drift", "critical", "inventory"),
    )
    plan_records = parse_plan(PLAN_ONE_DRIFT).records
    plan_actions, inv_actions = reconcile_populations(plan_records, None, [inv_issue], now=NOW)
    assert [a.kind for a in plan_actions] == ["open"]
    assert inv_actions == []  # inventory issue left exactly as-is


def test_run_opens_plan_and_inventory_issues_with_correct_labels() -> None:
    client = FakeClient(org_repos=["alpha", "beta", "rogue"])
    plan_actions, inv_actions = run(
        PLAN_ONE_DRIFT,
        issues_client=client,
        repos_client=client,
        org="vig-os",
        config_jsonnet_text=DECLARE_TWO,
        allowlist_path=None,
        now=NOW,
    )
    labels_used = {labels for _, _, labels in client.created}
    assert DRIFT_LABELS in labels_used
    assert INVENTORY_LABELS in labels_used
    assert len(client.created) == 2


def test_run_degrades_on_sweep_failure_but_reconciles_plan_drift() -> None:
    client = ExplodingReposClient(org_repos=["alpha", "beta", "rogue"])
    plan_actions, inv_actions = run(
        PLAN_ONE_DRIFT,
        issues_client=client,
        repos_client=client,
        org="vig-os",
        config_jsonnet_text=DECLARE_TWO,
        allowlist_path=None,
        now=NOW,
    )
    # Plan drift still opened; no inventory issue created (sweep degraded).
    assert len(client.created) == 1
    (title, _body, labels) = client.created[0]
    assert labels == DRIFT_LABELS
    assert title == 'Drift: repository[name="alpha"]'
    assert inv_actions == []


def test_run_without_repos_client_is_plan_only() -> None:
    client = FakeClient()
    plan_actions, inv_actions = run(
        PLAN_ONE_DRIFT,
        issues_client=client,
        repos_client=None,
        org="vig-os",
        config_jsonnet_text=None,
        allowlist_path=None,
        now=NOW,
    )
    assert len(client.created) == 1
    assert inv_actions == []
