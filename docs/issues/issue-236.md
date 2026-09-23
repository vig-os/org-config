---
type: issue
state: closed
created: 2026-09-23T11:59:15Z
updated: 2026-09-23T12:51:52Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/236
comments: 0
labels: discussion, priority:low, area:ci, effort:medium
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-23T21:09:31.443Z
---

# [Issue 236]: [Decide whether the Plan check should ever be enforcing, given a path-filtered workflow cannot be required](https://github.com/vig-os/org-config/issues/236)

## Summary

`Plan` is advisory. The `Main protection` ruleset requires exactly one status
check context, `CI Summary`; the plan posts a comment and nothing blocks on its
result. A red plan — a PR whose config changes propose a diff nobody intended —
merges on green CI like any other.

Whether that is right has never actually been decided. It is worth deciding
explicitly rather than continuing by default.

## The constraint that makes this non-trivial

`Plan` **cannot** simply be added to the ruleset's required contexts, because it
is path-filtered. GitHub leaves a required check that never runs in `pending`
forever, so every PR not touching `otterdog.json`, `otterdog/**`, `plan.yml` or
`justfile.project` — the majority — would become unmergeable.

This came up in #230, where the issue described the missing filter entry as a
lost "merge gate". It was not one, and the correction is recorded in that issue
and in the changelog. But it surfaced the real question underneath.

## Options, roughly

1. **Leave it advisory.** A plan's output is a judgement call, not a pass/fail —
   [ADR-0002](docs/adr/0002-drift-semantics.md) already takes this position for
   drift ("a non-empty diff is for the author to decide on, **not** a failure"),
   and the plan comment says exactly that today. The apply path has its own
   human gate (the `production` environment reviewer), so nothing reaches the
   live org unreviewed regardless. Cheapest, and arguably already correct.
2. **Always-runs skip-job shim.** Drop the `paths:` filter and gate the real work
   inside the job on a `dorny/paths-filter`-style step, so the check always
   reports — green-by-skip when no config path changed. Makes `Plan` requirable
   at the cost of a job on every PR and a check whose green means two different
   things.
3. **Require it only where it runs.** Not expressible in a ruleset; noted only to
   record that it was considered and is not available.

Option 1 is the status quo and may well be the answer. The point of this issue is
that it should be the recorded answer, with the trade named, rather than an
accident of how the workflow was first written.

## Worth weighing

- What a required `Plan` would actually buy over the existing `production`
  environment gate, which already stops every live mutation with the exact-tree
  plan preview beside the approve button (#105, #176).
- Whether green-by-skip devalues the signal: a check that is green both when the
  plan is empty and when it never ran is weaker evidence than one that is absent.
- Downstream blast radius: `template/`'s caller carries the same filter, so this
  decision propagates to every consumer org's skeleton.

## Acceptance

- [ ] A decision recorded in ADR-0007 (or a new ADR if it supersedes L2's shape)
- [ ] If the answer is "stay advisory", the reasoning is written down so the
      question is not re-raised from scratch next time
- [ ] If the answer is enforcing, the implementation issue is spun off separately

## Context

Split out of #230, which fixed the paths filter and deliberately did not touch
the advisory/enforcing question.
