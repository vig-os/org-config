---
type: issue
state: open
created: 2026-10-11T09:04:14Z
updated: 2026-10-11T09:04:14Z
author: gerchowl
author_url: https://github.com/gerchowl
url: https://github.com/vig-os/org-config/issues/334
comments: 0
labels: none
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-10-12T08:46:30.943Z
---

# [Issue 334]: [stepv: Main protection without a required approval (solo maintainer)](https://github.com/vig-os/org-config/issues/334)

## Problem

`stepv` is maintained by one person, who writes every PR with an agent, and the house `Main protection` (ADR-0008) needs **1 approval**. GitHub refuses a PR author's own approval (`422: Can not approve your own pull request`), so every stepv PR blocks on `REVIEW_REQUIRED` once CI is green. vig-os/stepv#50 is waiting on that now: all 13 checks pass, CI Summary included.

ADR-0008's answer for a solo repo is the `#OrganizationAdmin:pull_request` bypass (`gh pr merge --admin`). stepv's working rule is never to merge with `--admin`, so that override doesn't become the routine path. A hand-set 0-approval ruleset (2026-10-05) was reverted by the 2026-10-09 apply, as it should be: the config is the source of truth.

## Proposal

Declare a stepv exception: Main protection with **0 approvals**, still gated by the required `CI Summary` check (strict). That matches `devkit-smoke-test`'s exception and the house `devProtection`/`releaseProtection` shapes ("count-0-with-required-checks"). Everything else stays on the house shape: stale dismissal, thread resolution, the admin `pull_request` bypass, signed commits and tag protection.

CI Summary can be required now that the dependency graph is on (vig-os/stepv#16): Dependency Review, the one check that used to fail, passes.

## Acceptance

- [ ] The `stepv` block in `otterdog/vig-os/vig-os.jsonnet` overrides `required_approving_review_count: 0`, with an EXCEPTION comment.
- [ ] ADR-0008's Exceptions table has a `stepv` row with its reason and exit.
- [ ] CHANGELOG `Unreleased` has an entry.
- [ ] `plan` shows exactly one diff: stepv's `Main protection` `required_approving_review_count` 1 → 0.

## Exit

A second maintainer reviews stepv PRs routinely; then stepv goes back to the house shape.

