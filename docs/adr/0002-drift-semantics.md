---
id: adr-0002-drift-semantics
type: adr
status: accepted
source: internal
date: 2026-07-17
owner: carlos.vigo@exoma.ch
tags: [drift, otterdog, governance, medtech]
refs: [vig-os/org-config#1, vig-os/org-config#9]
---

# ADR-0002 — Drift semantics: issue-only, deduplicated, `managed: false`

- Status: Accepted
- Date: 2026-07-17
- Component / area: `org-config` strict-drift layer
- Reviewers: Carlos Vigo (v1 plan approved in working session 2026-07-17; issue #1 plan comment)
- Trigger conditions: n/a (Accepted)
- Supersedes / Superseded by: n/a

## Context

`org-config` declaratively manages four GitHub organizations (`vig-os`, `exo-pet`, `exoma-ch`, `MorePET`) with
Otterdog as the reconciliation engine (ADR-0001). The engine produces a non-mutating `plan` diff between declared
config and live org/repo state; it does not itself decide what to *do* when live state has drifted from config. This
ADR fixes that policy: the response to detected drift, how drift is reported, and how undeclared or intentionally
unmanaged repositories are handled.

Constraints feeding the decision (issue #1 reevaluation and v1 plan comment):

- All four orgs are on the GitHub **Free** plan. Free-plan private repos have **no enforceable** branch protection or
  rulesets, and the API lets anyone *create* a repo — so tooling **cannot block** an out-of-band repo or setting
  change; it can only *detect and report* one after the fact.
- One of the governed orgs, `exo-pet`, is a **medtech** project whose git history is part of the audit record. Any
  automated mutation of that org's state must be conservative and fully traceable.
- The team is one engineer; the drift layer is a "few-hundred-LOC wrapper" around the engine's diff, not a second
  engine. Reporting must be low-noise or it will be ignored.
- Existing house building blocks: `sync-issues-action` (GitHub App auth) and `commit-action` (retry) are reused; the
  drift layer runs on a schedule and opens issues in the governed repo.

## Alternatives considered

Mandatory. Options for the drift-response mechanism:

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **Issue-only** | No silent edits; audit-safe; human-decided | Persists until triaged | **Chosen** |
| **Auto-revert** | Self-healing | Silent overwrite; unsafe for medtech; write creds | Rejected (opt-in-future) |
| **Safe-Settings revert** | Off-the-shelf; webhook | No record; hides drift; needs hosted Probot | Rejected |
| **Notification channel** | Fast human signal | Ephemeral; no dedup/lifecycle; splits record | Rejected (v1) |

Detail and reasoning for each verdict are carried in Decision and Rationale below.

## Decision

Drift response is **issue-only**: the scheduled drift run never mutates org or repo state.

- For each distinct divergence, the drift layer maintains **exactly one** open issue labelled `drift` + `critical`.
  On recurrence the existing issue is **updated, not duplicated**; on resolution (config and live state reconciled)
  the issue is **closed automatically**.
- **Undeclared repositories** discovered by the inventory sweep are **flagged** the same way (a `drift` + `critical`
  issue). The Free plan cannot block repo creation, so detect-and-report is the only available control.
- An allow-list of **`managed: false`** entries in the inventory sweep marks repos that are intentionally out of
  declarative scope; these are excluded from undeclared-repo flagging (but their absence from config is by design,
  not drift).
- **Auto-revert stays opt-in-future** and far from the medtech org: it is not built in v1 and, if ever added, is
  per-org opt-in and never enabled by default for `exo-pet`.

## Rationale

Issue-only reporting is the only response compatible with the two hard constraints. First, the Free plan means the
tooling is a *detector*, not an *enforcer* — it cannot prevent the drift, so its job is to make every divergence
loud, durable, and impossible to lose. GitHub issues give exactly that: a threaded, labelled, searchable, closeable
record that lives **inside the repo it audits**, which matters because `exo-pet`'s QMS wants its audit trail in its
own org. Second, medtech safety forbids an automated process silently rewriting org state; a human must decide
whether a given drift is an incident to revert or a change to adopt into config. Deduplication (one issue per
divergence, updated not duplicated, closed on resolution) is what keeps the signal usable — a fresh issue per
scheduled run would bury the real ones and train the team to ignore the `critical` label. The `managed: false`
allow-list keeps the undeclared-repo sweep honest: without it, every deliberately-unmanaged repo would generate
permanent noise, degrading the whole channel.

## Consequences

- The drift layer needs **stable divergence identity** (a deterministic key per divergence) to find-and-update the
  matching issue rather than opening a new one; this key format is coupled to the pinned Otterdog plan output and is
  covered by the L1 fixture tests (issue #1 plan comment, CI section).
- Drift **persists until a human acts** — the process guarantees visibility, not remediation. Triage of `drift` +
  `critical` issues is therefore an operational responsibility, not optional backlog.
- The scheduled run needs only **read/plan** credentials plus issue-write, not org-admin write — a smaller blast
  radius than an auto-revert design would require.
- The `managed: false` allow-list is itself governance state: adding an entry is a config change that goes through
  the normal PR flow, so "what is intentionally unmanaged" stays reviewable and versioned.
- Adopting a surfaced drift into config, or reverting it, is a **manual** follow-up PR; the issue is the trigger and
  its closure is the completion record.

## Corrections

<!-- None yet. Preserve superseded assumptions here with date + source when caught. -->

## Open questions / supersession triggers

- **GitHub natively absorbing drift policy** — if GitHub ships enforceable drift detection / auto-remediation for
  Free (or the orgs move to a plan where rulesets enforce prevention), the in-house issue-only layer may be
  reconsidered or narrowed.
- **Auto-revert promotion** — a future decision may enable opt-in auto-revert for specific low-risk, non-medtech orgs
  (never `exo-pet` by default); that would supersede the "issue-only, always" scope of this ADR for those orgs.
- **Notification channels** — adding Slack/email as a *secondary* signal (never replacing the issue record) is a
  deferred enhancement, not a reversal of this decision.

## References

- Issue #1 — GitHub org configuration management: <https://github.com/vig-os/org-config/issues/1>
- Issue #1 reevaluation comment (open-questions answers; drift → issue-only; `managed: false` in the inventory sweep):
  <https://github.com/vig-os/org-config/issues/1#issuecomment-4891615046>
- Issue #1 v1.0.0 implementation plan (drift lifecycle, CI/test pyramid, reviewer approval):
  <https://github.com/vig-os/org-config/issues/1#issuecomment-5001102649>
- Issue #9 — ADR-0002 decision summary: <https://github.com/vig-os/org-config/issues/9>
