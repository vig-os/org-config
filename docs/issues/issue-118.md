---
type: issue
state: closed
created: 2026-08-07T15:03:16Z
updated: 2026-08-07T15:59:27Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/118
comments: 0
labels: chore, security, priority:medium, area:ci, effort:small, semver:patch
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-08T03:28:17.589Z
---

# [Issue 118]: [Dismiss stale approvals on push for devkit's Main protection](https://github.com/vig-os/org-config/issues/118)

Approved finding **D7** of the devkit settings review, following #115 (PR #117).

## Problem

`devkit`'s `Main protection` ruleset requires 1 approving review but sets `dismiss_stale_reviews_on_push: false`, so an approval survives every subsequent push to the PR branch. A reviewer can approve a two-line docs change and the author can then push arbitrary new commits onto the same branch and merge to `main` on the strength of a review that never saw them.

```console
$ gh api repos/vig-os/devkit/rulesets/13444364 --jq '.rules[]|select(.type=="pull_request").parameters|{required_approving_review_count, dismiss_stale_reviews_on_push, require_last_push_approval}'
{"required_approving_review_count":1,"dismiss_stale_reviews_on_push":false,"require_last_push_approval":false}
```

The required status checks are `strict` and re-run on every push, so CI cannot be stale — but the human review can, and it is the only control standing between a change and `main`.

## Change

Set `dismisses_stale_reviews: true` (the otterdog `newPullRequest` field name; `dismiss_stale_reviews_on_push` on the GitHub side) on `devkit`'s **`Main protection` only**.

- **Not `Dev protection`** — 0 required approvals, so there is no review to dismiss.
- **Not `Release protection`** — 0 required approvals, same reason.

Cost is proportionate: `main` PRs already need a deliberate approval, and re-requesting it after a substantive push is the intended behavior. This composes with #115's `requires_code_owner_review: false` — the single binding human gate on `main` is now one approval that actually covers the code being merged.

## Engine constraint

This is a PATCH of a ruleset carrying numeric `15368:<context>` status checks, which otterdog 1.3.4 cannot write (#69, upstream eclipse-csi/otterdog#695). As with #115, live is reconciled by hand with `gh api -X PUT` so the apply sees no `devkit` change.

**Ordering note:** the reconciliation must not land while the apply run for #117 is still queued on the `production` gate — that run re-plans at execution time against the merged tree, which does not yet declare this field, so an early PUT would turn it into a `Main protection` PATCH and trip #69. The PUT is therefore deferred until that apply has completed.

