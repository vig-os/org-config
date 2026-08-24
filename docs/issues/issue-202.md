---
type: issue
state: closed
created: 2026-08-24T08:30:06Z
updated: 2026-08-24T09:30:30Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/202
comments: 0
labels: feature, area:workflow, semver:minor
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-24T09:37:26.913Z
---

# [Issue 202]: [Apply-dispatch reminder for downstream orgs: reusable tracker-comment workflow + apply integration](https://github.com/vig-os/org-config/issues/202)

On a private Team/Free-plan downstream org-config repo, environment required
reviewers are unavailable, so the engine's apply-on-merge-with-approval model
degrades to `workflow_dispatch`-only: merging a config PR previews via `plan`
but writes nothing until a human dispatches `apply` (the dispatch *is* the
approval gate — recorded in the exo-pet caller's header, which also records the
HTTP 422 from attempting a required-reviewer environment on a private repo).
Consequence: merged-but-unapplied config is a silent state. The admin who
merged gets no notification (GitHub suppresses self-activity emails), and the
first signal is the next scheduled drift run — up to a day later. The engine
repo itself is unaffected (public → `production` reviewer gate), so this is
downstream-only machinery, which is why it belongs here and not vendored in a
consumer (the #169 principle: downstream repos hold config data and thin
callers only).

Design — long-standing tracker issue, no per-merge issue churn. The whole
feature is **optional, active by default in the template**: the template ships
the reminder caller enabled and the runbook makes tracker setup a standard
onboarding step; an org opts out by deleting the caller and leaving
`tracker_issue` unset — with the input omitted, `apply.yml` is byte-identical
to today at assembly time and at runtime.

- Each downstream org hand-creates one pinned "Apply dispatch tracker" issue
  and assigns its designated admins. Assignment makes every subsequent bot
  comment email them regardless of watch settings; the assignee list IS the
  admin list, changeable without touching any workflow.
- New reusable `.github/workflows/apply-reminder.yml` (`workflow_call`):
  inputs `tracker_issue` (`string`, default `''` — the established
  optional-input idiom per `otterdog_version`; `number` has no empty sentinel)
  plus the usual org/config-repo pair. On the caller's `push` to `main`,
  filtered to **all four** paths apply consumes — `otterdog.json`,
  `otterdog/**`, `secrets/**`, `.sops.yaml` (see `apply-engine.yml`; a
  two-path filter would let a SOPS secret rotation merge with no reminder,
  exactly the silent state this issue closes) — it comments on the tracker
  (merge commit, PR link, dispatch command) and adds a `pending-apply` label
  for at-a-glance state. The PR link is parsed from the merge commit title's
  guaranteed `(#N)` suffix (house policy: merge commits only,
  `merge_commit_title: PR_TITLE`); a direct push without one degrades to a
  commit-only comment, never fails. No secrets: same-repo comment on the
  workflow `GITHUB_TOKEN`; the job grants `issues: write` plus
  `contents: read` (a private caller needs it even to checkout, #173). Own
  concurrency group (`apply-reminder-<org>`) — never `otterdog-mutate-<org>`,
  where a reminder would queue uselessly behind a 30-minute apply. Pure `gh`
  run steps, no third-party actions, actionlint/zizmor clean with no baseline
  entries.
- Reusable `apply.yml` gains an optional `tracker_issue` input (`string`,
  default `''`): on successful apply, comment "applied in run <url>" and
  remove the label (tolerating 404 when absent). **Not** on `GITHUB_TOKEN`:
  the #176 standing rule caps the called job graph at `contents: read` at
  assembly time, before any `if:`, so adding `issues: write` would
  startup-fail every existing consumer. The comment instead rides a narrowed
  App token minted in-workflow, copying `drift.yml`'s issue-write pattern
  (`permission-issues: write`, `repositories: <config_repo>`) — no caller
  change, no new App grant (Issues R/W already held per
  `docs/runbooks/github-app.md`). The step slots between the apply report and
  "Fail on apply error", guarded by
  `inputs.tracker_issue != '' && steps.apply.outcome != 'skipped' && steps.apply.outputs.rc == '0'`
  — both extra terms load-bearing: the apply step runs under `set +e` so its
  outcome is `success` even when otterdog failed (`outputs.rc` is the only
  truth), and a superseded run self-skips yet stays green, so a weaker guard
  would post "applied" for a run that applied nothing.
- `template/` ships the thin reminder caller (active by default, with a
  `TODO(tracker)` placeholder in the style of the existing TODO pins) plus a
  runbook step in the "After the Team upgrade" section: create the pinned
  tracker, assign the admins, hand-create the `pending-apply` label (otterdog
  has no label schema and the add-label endpoint does not documentedly
  auto-create; a one-off UI step is the house preference), and fill the
  number into both callers.
- Scope rider, same change: correct the template apply caller.
  `template/.github/workflows/apply.yml` still ships push-triggered apply and
  instructs creating a required-reviewer `production` environment, which
  422s on private repos below Enterprise — a template-faithful private org
  would get an auto-apply *and* a reminder telling it to dispatch. Document
  both modes (public/Enterprise: push + reviewer gate; private Team/Free:
  dispatch-only) and align `README.repo.md`'s "How changes flow" claim.

Multiple merges before one dispatch yield N reminder comments, then one
"applied" comment and one label removal — acceptable, and the supersession
guard means only the newest tree ever applies. The tracker thread then pairs
every config merge with its apply — a durable audit record — with the
scheduled drift run remaining the enforcement backstop for ignored reminders.

Rollout: a minor release does not deliver the new caller — there is no
template-sync machinery, and Renovate only bumps pins on existing callers.
Sequence: engine PR (workflows + template + changelog) → minor release →
per-org PR hand-adding the reminder caller and bumping pins, plus the one-time
tracker/label/assignee setup.

First adopter: exo-pet/org-config (distribution pilot, #25), where the gap is
live today: exo-pet/org-config#37 merged and sat awaiting dispatch with no
notification path.

