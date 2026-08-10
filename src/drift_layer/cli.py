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

A third leg asserts the **unmanaged controls** (issue #116): live org/repo
settings otterdog has no schema field for, read straight from the REST API and
compared against ``unmanaged-controls.toml``. Its findings form an
``unmanaged-control``-labelled population and degrade PER ROW — a row that could
not be read has its issue withheld from reconciliation entirely, so a single
403 never phantom-resolves a real finding.

``--dry-run`` prints the plan of actions without touching GitHub;
``--controls-report`` evaluates the assertion table and prints the per-row
outcomes without any issue write, which is how the table is authored and
verified. The issues token is read from ``$GITHUB_TOKEN``
(issues:write-narrowed); the org/repo read token from ``$DRIFT_REPOS_TOKEN``
(the full plan token) — when unset, both live-read legs are skipped and only
plan drift is reconciled.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from .allowlist import apply_allowlist, load_allowlist
from .controls import (
    ControlOutcome,
    ControlsConfig,
    ControlsResult,
    evaluate_controls,
    load_controls,
)
from .github_client import GitHubClient, RestGitHubClient, execute
from .inventory import build_inventory_records
from .models import DriftRecord, Issue, IssueAction
from .parser import parse_plan
from .reconcile import (
    DRIFT_LABELS,
    INVENTORY_LABEL,
    INVENTORY_LABELS,
    UNMANAGED_LABEL,
    UNMANAGED_LABELS,
    extract_fingerprint,
    reconcile,
)

DEFAULT_CONFIG_JSONNET = "otterdog/vig-os/vig-os.jsonnet"
DEFAULT_UNMANAGED_CONTROLS = "unmanaged-controls.toml"


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
    controls_result: ControlsResult | None,
    issues: list[Issue],
    *,
    now: str,
) -> tuple[list[IssueAction], list[IssueAction], list[IssueAction]]:
    """Reconcile the plan, inventory and unmanaged-control populations apart.

    Open drift issues are partitioned by label so no lifecycle ever touches
    another's issues — the plan population must exclude BOTH extra labels, or
    the first run would close every inventory and control issue as
    phantom-resolved.

    ``None`` for a leg means it did not run (skipped or failed wholesale): its
    issues are then left exactly as-is while the others still reconcile (issue
    #21 explicit degradation). The controls leg degrades one step finer — the
    issues of rows that could not be READ are withheld from its reconcile input
    individually, so those issues are neither refreshed nor closed while every
    readable row is still reported (issue #116).
    """
    plan_issues = [
        i for i in issues if INVENTORY_LABEL not in i.labels and UNMANAGED_LABEL not in i.labels
    ]
    plan_actions = reconcile(plan_records, plan_issues, now=now)

    inventory_actions: list[IssueAction] = []
    if inventory_records is not None:
        inventory_issues = [i for i in issues if INVENTORY_LABEL in i.labels]
        inventory_actions = reconcile(inventory_records, inventory_issues, now=now)

    control_actions: list[IssueAction] = []
    if controls_result is not None:
        control_issues = [
            i
            for i in issues
            if UNMANAGED_LABEL in i.labels
            and extract_fingerprint(i.body) not in controls_result.unresolved_fingerprints
        ]
        control_actions = reconcile(controls_result.records, control_issues, now=now)

    return plan_actions, inventory_actions, control_actions


def run(
    plan_text: str,
    *,
    issues_client: GitHubClient,
    repos_client: GitHubClient | None,
    org: str,
    config_jsonnet_text: str | None,
    allowlist_path: str | None,
    controls_config: ControlsConfig | None,
    now: str,
) -> tuple[list[IssueAction], list[IssueAction], list[IssueAction]]:
    """Reconcile plan drift, inventory sweep and control assertions, then execute.

    Both live-read legs need the org-wide repos client; the sweep additionally
    needs the committed config text. Either leg failing degrades only itself —
    its issues are left untouched while the others still reconcile. Returns the
    (plan, inventory, control) actions executed, for logging/tests.
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

    controls_result: ControlsResult | None = None
    if repos_client is not None and controls_config is not None:
        try:
            controls_result = evaluate_controls(
                controls_config,
                repos_client,
                org=org,
                config_jsonnet_text=config_jsonnet_text,
            )
        except Exception as exc:  # a wholesale leg failure, not a per-row one
            print(
                f"warning: unmanaged-control assertions failed ({exc!s}); leaving "
                f"unmanaged-control issues untouched",
                file=sys.stderr,
            )
            controls_result = None
        else:
            _warn(controls_result.notes)

    plan_actions, inventory_actions, control_actions = reconcile_populations(
        plan_records, inventory_records, controls_result, issues, now=now
    )
    execute(plan_actions, issues_client, DRIFT_LABELS)
    execute(inventory_actions, issues_client, INVENTORY_LABELS)
    execute(control_actions, issues_client, UNMANAGED_LABELS)
    return plan_actions, inventory_actions, control_actions


def _warn(notes: list[str]) -> None:
    """Surface degradation/tolerance notes as Actions annotations (stderr).

    ``::warning::`` is inert outside GitHub Actions, so this stays readable
    locally while still annotating the run where it matters."""
    for note in notes:
        print(f"::warning::unmanaged-control: {note}", file=sys.stderr)


def _format_action(action: IssueAction) -> str:
    target = f"#{action.number}" if action.number is not None else "(new)"
    return f"{action.kind:>6}  {target:>6}  {action.fingerprint}  {action.title}"


def _format_outcome(outcome: ControlOutcome) -> str:
    return (
        f"{outcome.status:<10}  {outcome.scope:<18}  {outcome.key:<40}  "
        f"expected {outcome.expected or '-'} | actual {outcome.actual or '-'}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="drift-layer", description=__doc__)
    # --plan-file/--repo are required for every mode EXCEPT --controls-report,
    # which reconciles nothing and reads no issues; enforced below.
    parser.add_argument("--plan-file", type=Path, help="captured otterdog plan output")
    parser.add_argument("--repo", help="owner/repo hosting the drift issues")
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
        "--unmanaged-controls",
        default=DEFAULT_UNMANAGED_CONTROLS,
        help="TOML assertion table for controls otterdog cannot model (missing -> leg skipped)",
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
    parser.add_argument(
        "--controls-report",
        action="store_true",
        help="evaluate the assertion table and print each row's outcome; no issue writes",
    )
    args = parser.parse_args(argv)

    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    config_jsonnet_text: str | None = None
    if args.config_jsonnet:
        config_path = Path(args.config_jsonnet)
        if config_path.exists():
            config_jsonnet_text = config_path.read_text()

    if args.controls_report:
        return _report_controls(args, config_jsonnet_text)

    if args.plan_file is None or not args.repo:
        print("error: --plan-file and --repo are required", file=sys.stderr)
        return 2
    plan_text = args.plan_file.read_text()

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
        plan_actions, inventory_actions, _ = reconcile_populations(
            plan_records, inventory_records, None, [], now=now
        )
        actions = plan_actions + inventory_actions
        print(f"[dry-run] {len(actions)} action(s) from plan+sweep (against empty issue set):")
        for action in actions:
            print(_format_action(action))
        # The assertion leg is a live read by definition; --controls-report is
        # its offline-ish equivalent (still read-only, but it does call the API).
        print("[dry-run] unmanaged-controls leg skipped")
        return 0

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("error: GITHUB_TOKEN is not set", file=sys.stderr)
        return 2

    issues_client = RestGitHubClient(args.repo, token)

    # Org/repo reads use the full plan token (issues-narrowed cannot read them).
    # Absent -> both live-read legs skipped, plan drift still reconciles. The
    # committed-config text gates only the sweep and the org-secret families,
    # not the assertion leg as a whole, so it is checked per-leg rather than here.
    repos_client: GitHubClient | None = None
    repos_token = os.environ.get("DRIFT_REPOS_TOKEN")
    if repos_token:
        repos_client = RestGitHubClient(args.repo, repos_token)

    plan_actions, inventory_actions, control_actions = run(
        plan_text,
        issues_client=issues_client,
        repos_client=repos_client,
        org=args.org,
        config_jsonnet_text=config_jsonnet_text,
        allowlist_path=args.allowlist,
        controls_config=load_controls(args.unmanaged_controls),
        now=now,
    )
    print(
        f"{len(plan_actions)} plan action(s), {len(inventory_actions)} inventory action(s), "
        f"{len(control_actions)} unmanaged-control action(s):"
    )
    for action in (*plan_actions, *inventory_actions, *control_actions):
        print(_format_action(action))
    return 0


def _report_controls(args: argparse.Namespace, config_jsonnet_text: str | None) -> int:
    """Evaluate the assertion table and print one line per row; no issue writes.

    This is how the table is authored and verified: a seeded row should read OK
    or TOLERATED here BEFORE the scheduled run turns it into a critical issue.
    """
    token = os.environ.get("DRIFT_REPOS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("error: DRIFT_REPOS_TOKEN (or GITHUB_TOKEN) is not set", file=sys.stderr)
        return 2

    config = load_controls(args.unmanaged_controls)
    if not config.controls and config.org_secrets is None:
        print(f"no assertion table at {args.unmanaged_controls}; nothing to report")
        return 0

    result = evaluate_controls(
        config,
        RestGitHubClient(args.repo or "", token),
        org=args.org,
        config_jsonnet_text=config_jsonnet_text,
    )
    print(f"unmanaged-control assertions for `{args.org}` ({len(result.outcomes)} row(s)):")
    for outcome in result.outcomes:
        print(_format_outcome(outcome))
    if result.notes:
        print("\nnotes:")
        for note in result.notes:
            print(f"  - {note}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
