"""CLI entry point wiring the pure core to the GitHub edge.

    uv run drift-layer --plan-file plan.txt --repo vig-os/org-config \
        --allowlist drift-allowlist.toml

Reads a captured ``otterdog plan`` output, parses it, drops allow-listed
divergences, reconciles against the repo's open drift issues, and executes the
resulting open/update/close actions. ``--dry-run`` prints the plan of actions
without touching GitHub. The issues token is read from ``$GITHUB_TOKEN`` (the
workflow's issues:write-narrowed token).
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from .allowlist import apply_allowlist, load_allowlist
from .github_client import RestGitHubClient, execute
from .models import Issue, IssueAction
from .parser import parse_plan
from .reconcile import DRIFT_LABELS, reconcile


def build_actions(
    plan_text: str,
    issues: list[Issue],
    *,
    allowlist_path: str | None,
    now: str,
    default_org: str = "unknown",
) -> list[IssueAction]:
    """Pure pipeline: plan text + live issues -> reconciled actions.

    Kept free of I/O so it is unit-testable end to end with fixture plans and a
    fake issue list.
    """
    parsed = parse_plan(plan_text, default_org=default_org)
    entries = load_allowlist(allowlist_path)
    records = apply_allowlist(parsed.records, entries)
    return reconcile(records, issues, now=now)


def _format_action(action: IssueAction) -> str:
    target = f"#{action.number}" if action.number is not None else "(new)"
    return f"{action.kind:>6}  {target:>6}  {action.fingerprint}  {action.title}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="drift-layer", description=__doc__)
    parser.add_argument(
        "--plan-file", required=True, type=Path, help="captured otterdog plan output"
    )
    parser.add_argument("--repo", required=True, help="owner/repo hosting the drift issues")
    parser.add_argument(
        "--org", default="unknown", help="fallback org id if the plan omits a Project header"
    )
    parser.add_argument("--allowlist", default=None, help="TOML allow-list of expected drift")
    parser.add_argument(
        "--dry-run", action="store_true", help="print actions without touching GitHub"
    )
    args = parser.parse_args(argv)

    plan_text = args.plan_file.read_text()
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    if args.dry_run:
        # Reconcile against an empty issue set: dry-run shows what a fresh repo
        # would open, without reading GitHub. Useful for local plan inspection.
        actions = build_actions(
            plan_text, [], allowlist_path=args.allowlist, now=now, default_org=args.org
        )
        print(f"[dry-run] {len(actions)} action(s) from plan (against empty issue set):")
        for action in actions:
            print(_format_action(action))
        return 0

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("error: GITHUB_TOKEN is not set", file=sys.stderr)
        return 2

    client = RestGitHubClient(args.repo, token)
    issues = client.list_open_drift_issues()
    actions = build_actions(
        plan_text, issues, allowlist_path=args.allowlist, now=now, default_org=args.org
    )

    print(f"{len(actions)} action(s):")
    for action in actions:
        print(_format_action(action))

    execute(actions, client, DRIFT_LABELS)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
