"""CLI entry point wiring the pure core to the GitHub edge.

    uv run drift-layer --plan-file plan.txt --repo vig-os/org-config \
        --org vig-os --allowlist drift-allowlist.toml \
        --config-jsonnet otterdog/vig-os/vig-os.jsonnet

Reads a captured ``otterdog plan`` output, parses it, drops allow-listed
divergences, reconciles against the repo's open drift issues, and executes the
resulting open/update/close actions.

After the plan leg it also runs the **inventory sweep** (issue #21): it lists
the live org repos and compares them against the declared set from the committed
otterdog config, feeding undeclared/absent repos into the SAME reconcile/issue
lifecycle (an ``inventory``-labelled population). The sweep is a best-effort
leg — if the live repo read fails it degrades explicitly, leaving inventory
issues untouched while plan drift still reconciles.

``--dry-run`` prints the plan of actions without touching GitHub. The issues
token is read from ``$GITHUB_TOKEN`` (issues:write-narrowed); the org-repo read
token from ``$DRIFT_REPOS_TOKEN`` (the full plan token) — when unset (or the
config is absent) the sweep is skipped and only plan drift is reconciled.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from .allowlist import apply_allowlist, load_allowlist
from .github_client import GitHubClient, RestGitHubClient, execute
from .inventory import build_inventory_records
from .models import DriftRecord, Issue, IssueAction
from .parser import parse_plan
from .reconcile import DRIFT_LABELS, INVENTORY_LABEL, INVENTORY_LABELS, reconcile

DEFAULT_CONFIG_JSONNET = "otterdog/vig-os/vig-os.jsonnet"


def parse_plan_records(
    plan_text: str, *, allowlist_path: str | None, default_org: str
) -> list[DriftRecord]:
    """Parse plan text and flag allow-listed (expected) divergences."""
    parsed = parse_plan(plan_text, default_org=default_org)
    entries = load_allowlist(allowlist_path)
    return apply_allowlist(parsed.records, entries)


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
    records = parse_plan_records(plan_text, allowlist_path=allowlist_path, default_org=default_org)
    return reconcile(records, issues, now=now)


def reconcile_populations(
    plan_records: list[DriftRecord],
    inventory_records: list[DriftRecord] | None,
    issues: list[Issue],
    *,
    now: str,
) -> tuple[list[IssueAction], list[IssueAction]]:
    """Reconcile the plan-drift and inventory populations independently.

    Open drift issues are partitioned by the ``inventory`` label so the two
    lifecycles never touch each other's issues. ``inventory_records is None``
    means the sweep did not run (skipped or failed): its issues are then left
    exactly as-is — never closed as phantom-resolved — while plan drift still
    reconciles (issue #21 explicit degradation).
    """
    plan_issues = [i for i in issues if INVENTORY_LABEL not in i.labels]
    plan_actions = reconcile(plan_records, plan_issues, now=now)

    if inventory_records is None:
        return plan_actions, []

    inventory_issues = [i for i in issues if INVENTORY_LABEL in i.labels]
    inventory_actions = reconcile(inventory_records, inventory_issues, now=now)
    return plan_actions, inventory_actions


def run(
    plan_text: str,
    *,
    issues_client: GitHubClient,
    repos_client: GitHubClient | None,
    org: str,
    config_jsonnet_text: str | None,
    allowlist_path: str | None,
    now: str,
) -> tuple[list[IssueAction], list[IssueAction]]:
    """Reconcile plan drift + inventory sweep against live issues, then execute.

    The inventory sweep runs only when both a repos client and the committed
    config text are available; any failure reading the live repos degrades to
    plan-only reconciliation (inventory issues left untouched). Returns the
    (plan_actions, inventory_actions) executed, for logging/tests.
    """
    plan_records = parse_plan_records(plan_text, allowlist_path=allowlist_path, default_org=org)
    issues = issues_client.list_open_drift_issues()

    inventory_records: list[DriftRecord] | None = None
    if repos_client is not None and config_jsonnet_text is not None:
        try:
            live = repos_client.list_org_repos(org)
            inventory_records = build_inventory_records(
                config_jsonnet_text, live, org=org, allowlist_path=allowlist_path
            )
        except Exception as exc:  # degrade on any live-read failure (403/network/API)
            print(
                f"warning: inventory sweep failed ({exc!s}); reconciling plan "
                f"drift only and leaving inventory issues untouched",
                file=sys.stderr,
            )
            inventory_records = None

    plan_actions, inventory_actions = reconcile_populations(
        plan_records, inventory_records, issues, now=now
    )
    execute(plan_actions, issues_client, DRIFT_LABELS)
    execute(inventory_actions, issues_client, INVENTORY_LABELS)
    return plan_actions, inventory_actions


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
        "--org", default="unknown", help="org id (fallback for the plan, target of the sweep)"
    )
    parser.add_argument("--allowlist", default=None, help="TOML allow-list (expected + unmanaged)")
    parser.add_argument(
        "--config-jsonnet",
        default=DEFAULT_CONFIG_JSONNET,
        help="committed otterdog config: the declared-repo source for the sweep",
    )
    parser.add_argument(
        "--repos-file",
        default=None,
        type=Path,
        help="offline live repo list (one name per line); overrides the REST read",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print actions without touching GitHub"
    )
    args = parser.parse_args(argv)

    plan_text = args.plan_file.read_text()
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    config_jsonnet_text: str | None = None
    if args.config_jsonnet:
        config_path = Path(args.config_jsonnet)
        if config_path.exists():
            config_jsonnet_text = config_path.read_text()

    if args.dry_run:
        # Reconcile against an empty issue set: shows what a fresh repo would
        # open, without reading GitHub. An offline --repos-file also previews the
        # inventory sweep; otherwise it is plan-only.
        plan_records = parse_plan_records(
            plan_text, allowlist_path=args.allowlist, default_org=args.org
        )
        inventory_records: list[DriftRecord] | None = None
        if args.repos_file and config_jsonnet_text is not None:
            live = args.repos_file.read_text().split()
            inventory_records = build_inventory_records(
                config_jsonnet_text, live, org=args.org, allowlist_path=args.allowlist
            )
        plan_actions, inventory_actions = reconcile_populations(
            plan_records, inventory_records, [], now=now
        )
        actions = plan_actions + inventory_actions
        print(f"[dry-run] {len(actions)} action(s) from plan+sweep (against empty issue set):")
        for action in actions:
            print(_format_action(action))
        return 0

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("error: GITHUB_TOKEN is not set", file=sys.stderr)
        return 2

    issues_client = RestGitHubClient(args.repo, token)

    # Org-repo read uses the full plan token (issues-narrowed cannot read repos).
    # Absent -> sweep skipped, plan drift still reconciles.
    repos_client: GitHubClient | None = None
    repos_token = os.environ.get("DRIFT_REPOS_TOKEN")
    if repos_token and config_jsonnet_text is not None:
        repos_client = RestGitHubClient(args.repo, repos_token)

    plan_actions, inventory_actions = run(
        plan_text,
        issues_client=issues_client,
        repos_client=repos_client,
        org=args.org,
        config_jsonnet_text=config_jsonnet_text,
        allowlist_path=args.allowlist,
        now=now,
    )
    print(f"{len(plan_actions)} plan action(s), {len(inventory_actions)} inventory action(s):")
    for action in (*plan_actions, *inventory_actions):
        print(_format_action(action))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
