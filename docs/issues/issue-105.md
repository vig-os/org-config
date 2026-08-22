---
type: issue
state: open
created: 2026-08-07T09:24:29Z
updated: 2026-08-07T09:24:41Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/105
comments: 0
labels: bug, priority:high, area:workflow
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-08T03:28:20.525Z
---

# [Issue 105]: [apply executes a stale approved tree with no supersession guard](https://github.com/vig-os/org-config/issues/105)

## What happened

Sequence on 2026-08-07:

1. PR #102 (declare tessera resources) merged at 08:54 → apply run 31163683442 queued, waiting on production approval. Its tree still declared repos `meta`, `os-config`, `part-registry`.
2. PR #103 (adopt the intentional deletion of those three repos) merged at 08:57 → apply run 31163882296 queued behind it (concurrency group `otterdog-mutate`).
3. The production approval for run 31163683442 arrived ~09:21 — after #103 had already merged and reversed part of what that tree declared.
4. The apply executed the stale tree: `Executed plan: 8 added, 1 changed` — it recreated the three deleted repos as empty auto-init stubs plus their 5 rulesets, then exited rc=2 on two post-create patches (meta `main→dev` branch rename 403, os-config code-scanning default-setup 422 on an empty repo). Cleanup required deleting the three repos again by hand.

## Problem

Approval gates the *run*, not the *tree*. Once a later merge supersedes a queued apply, approving the older run mutates live state toward a config that is no longer on `main`, and the approval UI gives the reviewer no plan summary to catch it.

## Possible guards (pick one or combine)

- At apply-job start, compare `github.sha` with the current tip of `main`; if superseded, skip with a neutral notice (the newer queued apply covers the delta).
- On merge to `main`, cancel still-waiting apply runs for older commits (approval then only ever applies the newest tree).
- Surface the plan counts/diff for the exact tree in the deployment approval context so the reviewer sees what an old run will do.

## Evidence

- Failed run: https://github.com/vig-os/org-config/actions/runs/31163683442
- Recreated stubs: `meta`/`os-config`/`part-registry` created 2026-08-07T09:21:27–40Z (deletion pending — token lacks delete_repo scope).

Refs: #99

