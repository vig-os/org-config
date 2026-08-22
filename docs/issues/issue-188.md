---
type: issue
state: open
created: 2026-08-21T14:21:08Z
updated: 2026-08-21T14:21:08Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/188
comments: 0
labels: change-request
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-22T02:56:12.230Z
---

# [Issue 188]: [[CHANGE-REQUEST] sync-issues-action: require up-to-date branches (strict) on Main protection](https://github.com/vig-os/org-config/issues/188)

### Target repo(s)

vig-os/sync-issues-action

### Setting area

Ruleset / branch protection

### Current behavior

`sync-issues-action`'s `Main protection` (`otterdog/vig-os/vig-os.jsonnet:782-787` as of `7249220`) requires the `CI Summary` + `Dist Check` status checks but does not set `strict`, so it defaults to false — verified live on ruleset `13401788`: `strict_required_status_checks_policy: false`. A PR whose checks passed against a stale base can merge even after `main` has moved, so the merged result was never tested as it will actually land.

devkit (`:408`) and commit-action (`:276`) both set `strict: true` — sync-issues-action is the only one of the three action/tooling repos without up-to-date-branch enforcement. The repo also sets `allow_update_branch: false` (`:746`), unlike what the requirement wants ergonomically.

### Desired change

1. Add `strict: true` to the `required_status_checks` block of `Main protection`.
2. Flip `allow_update_branch: true` on the repo, so the **Update branch** button (and auto-merge's auto-update) satisfies the requirement without a manual rebase.

### Justification

Same principle as #184's stale-review dismissal, applied to CI instead of review: the gates must cover the code actually being merged. Convergence with devkit and commit-action removes an accidental difference between sibling repos. Also clears the `'up-to-date branches' is disabled` warning on OpenSSF Scorecard alert [sync-issues-action#15](https://github.com/vig-os/sync-issues-action/security/code-scanning/15) — improving the score while the alert stays open, since its remaining warnings (approval count 1, last-push approval off) are deliberate for a solo maintainer.

Cost: one CI re-run per merge, only when `main` has moved since the branch last built. On a low-traffic solo-maintained repo this is rare; PRs are small and CI is short.

### Urgency

Low — whenever capacity allows

### Additional context

Explicitly deferred out of #184 ("worth deciding separately"); this is that decision. Precedent lines: devkit `:408`, commit-action `:276`. Related: #184, PR #186.
