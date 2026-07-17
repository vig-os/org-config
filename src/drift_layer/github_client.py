"""GitHub client injected at the edge (ADR-0007).

The pure core (parser/reconcile) never touches the network; this is the only
module that does. :class:`GitHubClient` is the Protocol the core depends on, so
tests inject a fake. :class:`RestGitHubClient` is the production implementation
over the GitHub REST API using the standard library only — no third-party
runtime dependency, keeping the tool ``uvx``-light like otterdog (ADR-0005).

The client is constructed with an *issues:write*-narrowed token (the drift
workflow's second, least-privilege token); narrowing works fine for issues.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Protocol

from .models import Issue, IssueAction

_API_ROOT = "https://api.github.com"


class GitHubClient(Protocol):
    """The issue operations the reconciler's executor needs."""

    def list_open_drift_issues(self) -> list[Issue]: ...

    def create_issue(self, title: str, body: str, labels: tuple[str, ...]) -> int: ...

    def update_issue(self, number: int, title: str, body: str) -> None: ...

    def add_comment(self, number: int, body: str) -> None: ...

    def close_issue(self, number: int) -> None: ...


class RestGitHubClient:
    """Standard-library REST client for one ``owner/repo``."""

    def __init__(self, repo: str, token: str, *, api_root: str = _API_ROOT) -> None:
        self._repo = repo
        self._token = token
        self._api_root = api_root.rstrip("/")

    def _request(self, method: str, path: str, payload: dict | None = None) -> object:
        url = path if path.startswith("http") else f"{self._api_root}{path}"
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self._token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
        return json.loads(raw) if raw else None

    def list_open_drift_issues(self) -> list[Issue]:
        """List open issues labelled ``drift`` (the reconciler filters further)."""
        issues: list[Issue] = []
        page = 1
        while True:
            path = f"/repos/{self._repo}/issues?state=open&labels=drift&per_page=100&page={page}"
            batch = self._request("GET", path) or []
            for raw in batch:
                # The issues endpoint also returns PRs; skip them.
                if "pull_request" in raw:
                    continue
                issues.append(
                    Issue(
                        number=raw["number"],
                        title=raw.get("title", ""),
                        body=raw.get("body") or "",
                        state=raw.get("state", "open"),
                    )
                )
            if len(batch) < 100:
                break
            page += 1
        return issues

    def create_issue(self, title: str, body: str, labels: tuple[str, ...]) -> int:
        result = self._request(
            "POST",
            f"/repos/{self._repo}/issues",
            {"title": title, "body": body, "labels": list(labels)},
        )
        return result["number"]  # type: ignore[index]

    def update_issue(self, number: int, title: str, body: str) -> None:
        self._request(
            "PATCH",
            f"/repos/{self._repo}/issues/{number}",
            {"title": title, "body": body},
        )

    def add_comment(self, number: int, body: str) -> None:
        self._request(
            "POST",
            f"/repos/{self._repo}/issues/{number}/comments",
            {"body": body},
        )

    def close_issue(self, number: int) -> None:
        self._request(
            "PATCH",
            f"/repos/{self._repo}/issues/{number}",
            {"state": "closed", "state_reason": "completed"},
        )


def execute(actions: list[IssueAction], client: GitHubClient, labels: tuple[str, ...]) -> None:
    """Apply reconciler actions through the client (open/update/close)."""
    for action in actions:
        if action.kind == "open":
            number = client.create_issue(action.title, action.body, labels)
            if action.comment:
                client.add_comment(number, action.comment)
        elif action.kind == "update":
            assert action.number is not None
            client.update_issue(action.number, action.title, action.body)
            if action.comment:
                client.add_comment(action.number, action.comment)
        elif action.kind == "close":
            assert action.number is not None
            if action.comment:
                client.add_comment(action.number, action.comment)
            client.close_issue(action.number)
        else:  # pragma: no cover - defensive
            msg = f"unknown action kind: {action.kind}"
            raise ValueError(msg)
