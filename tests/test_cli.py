"""L1 tests for the CLI pipeline and the client executor (fake client edge)."""

from __future__ import annotations

from pathlib import Path

from drift_layer.cli import build_actions
from drift_layer.github_client import execute
from drift_layer.models import Issue
from drift_layer.parser import parse_plan
from drift_layer.reconcile import DRIFT_LABELS, render_body

NOW = "2026-07-17 03:00 UTC"


class FakeClient:
    """In-memory GitHubClient stand-in recording every call (injected edge)."""

    def __init__(self, issues: list[Issue] | None = None) -> None:
        self.issues = issues or []
        self.created: list[tuple[str, str, tuple[str, ...]]] = []
        self.updated: list[tuple[int, str, str]] = []
        self.comments: list[tuple[int, str]] = []
        self.closed: list[int] = []
        self._next = 100

    def list_open_drift_issues(self) -> list[Issue]:
        return self.issues

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
