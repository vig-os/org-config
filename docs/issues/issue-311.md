---
type: issue
state: open
created: 2026-09-29T14:46:57Z
updated: 2026-09-29T15:28:51Z
author: gerchowl
author_url: https://github.com/gerchowl
url: https://github.com/vig-os/org-config/issues/311
comments: 2
labels: chore, priority:medium, area:workflow
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-30T08:09:21.850Z
---

# [Issue 311]: [chore(config): declare revkit — decide visibility (public → Tier A like scitadel), rulesets, train Apps](https://github.com/vig-os/org-config/issues/311)

## Context

`vig-os/revkit` was created on 2026-09-29 as a **private** repo: an HTML-first review surface for docs/ADRs, with GitHub PR round-trip and agent question UIs. It is scaffolded with devkit 1.17.0 (direnv mode, **gitflow**: `dev` + `main`, full release train, Apache-2.0), with `main` and `dev` pushed. It is **not declared** in `otterdog/vig-os/vig-os.jsonnet`, so the next drift run's inventory sweep will raise it as undeclared.

## Decision needed: visibility decides the tier

Per ADR-0008, a private repo on the Free plan cannot have a ruleset enforced, which is `qms`'s deferred state (#306). revkit has two options:

| Option | Tier | Consequence |
|---|---|---|
| **Make it public (recommended)** | **A (releasing)** | Same shapes as `scitadel` (devkit gitflow + release train). Apache-2.0 already chosen; no secrets in the tree. |
| Keep it private | none (like `qms`) | No enforceable protection; only repo settings. Would need its own ADR-0008 exception row. |

## Proposed declaration (Tier A, if public)

```jsonnet
orgs.newRepo('revkit') {
  allow_auto_merge: true,
  allow_update_branch: true,
  description: 'HTML-first review surface for the agentic era — doc/ADR review with persistent comments, GH PR round-trip, and agent-rich question UIs',
  // Tier A (ADR-0008): devkit gitflow scaffold (DEVKIT_WORKFLOW unset) releasing
  // through the devkit train, same shapes as scitadel. `CI Summary` is ci.yml's
  // aggregator (job `summary`).
  rulesets: [
    orgs.devProtection(checks=['15368:CI Summary'], bypass=['commit-action-bot']),
    orgs.mainProtection(['15368:CI Summary']),
    orgs.releaseProtection(checks=['15368:CI Summary'], bypass=['commit-action-bot']),
    orgs.signedCommits(),
    orgs.tagProtection(['vig-os-release-app']),
  ],
},
```

Plus the train's App access: the Commit App (`commit-action-bot`) and Release App installed on revkit, and `COMMIT_APP_*` / `RELEASE_APP_*` available to it, as for the other train consumers.

## Coming later (heads-up, not for this change)

revkit's hosted mode will need:

- a **GitHub App** (user-to-server tokens, so review comments post as the reviewer; `pull_requests: write`, `contents: read`)
- a `cloudflare` deployment **environment** for per-PR preview deploys
- probably a `github-pages`-style environment policy

These will come as a separate change request once the hosting design (revkit ADR) lands.

## Observed on the new repo (may be related)

On revkit's first PR (vig-os/revkit#2, into `dev`), `pull_request`-triggered `ci.yml` created **no run**, and closing/reopening didn't help either. `workflow_dispatch` on the same branch runs green. The repo-level Actions permissions read `enabled: true, allowed_actions: all`. The org-level Actions policy isn't readable without `admin:org`, so an org-policy cause can't be ruled out from here.

## Tasks

- [ ] Decide visibility (public → Tier A / private → exception row)
- [ ] Declare `revkit` in `vig-os.jsonnet` (+ ADR-0008 tier table if it needs a row)
- [ ] Install the Commit + Release Apps on revkit
- [ ] Check why `pull_request` workflows don't trigger on revkit

---

# [Comment #1]() by [gerchowl]()

_Posted on September 29, 2026 at 03:27 PM_

**CI trigger: resolved. Not an org-config / org-policy issue.**

**Symptom:** on revkit, GitHub recorded every `PushEvent` and `PullRequestEvent` (open/close/reopen/synchronize), but Actions started **zero** event-triggered runs, including the `push`-triggered CodeQL, Scorecard and sync-main-to-dev on the initial `main`/`dev` pushes. `workflow_dispatch` ran green. Same-hour PRs on org-config (#312) triggered normally.

**Checked** (read-only, `admin:org`):
- org Actions `enabled_repositories: all`, `allowed_actions: all`
- default workflow permissions `read`; fork approval `first_time_contributors`
- no org rulesets (Free plan)
- repo Actions `enabled: true`; no path filters in `ci.yml`
- unchanged by switching the repo private → public

**Fix:** reset the repo's Actions (`PUT repos/vig-os/revkit/actions/permissions` `enabled=false`, then `enabled=true allowed_actions=all`, restoring the prior values). The next push to vig-os/revkit#5 immediately started CI and CodeQL. The root cause isn't visible via the API; it looks like stale GitHub-side state on a freshly created repo.

**#312:** the blocker is cleared once revkit's PR CI finishes green (running now).

---

# [Comment #2]() by [gerchowl]()

_Posted on September 29, 2026 at 03:28 PM_

revkit PR CI is green now (vig-os/revkit#2, #5: `CI Summary` passes). One more manual step was needed: **Dependency Review** 403'd because the org creates new repos with the dependency graph off (`dependency_graph_enabled_for_new_repositories: false`). Enabled with `gh api -X PUT repos/vig-os/revkit/vulnerability-alerts`, per devkit's MIGRATION.md ("Enable the dependency graph on new public consumers").

**#312 is unblocked.** Worth considering: flip that org default, or add a new-repo control for it in `unmanaged-controls.toml`, so the next public repo doesn't hit this.

