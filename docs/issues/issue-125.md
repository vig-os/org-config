---
type: issue
state: open
created: 2026-08-07T16:46:56Z
updated: 2026-08-07T16:46:56Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/125
comments: 0
labels: chore, priority:low, area:ci, effort:small, semver:patch
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-08T03:28:16.439Z
---

# [Issue 125]: [Retire orphaned DOCKERHUB_TOKEN / DOCKERHUB_USERNAME org secrets](https://github.com/vig-os/org-config/issues/125)

Surfaced by the consumer-matrix sweep for #123.

## Finding

`DOCKERHUB_TOKEN` and `DOCKERHUB_USERNAME` are `vig-os` **organization** secrets with **zero consumers**. A grep of every `secrets.*` reference across all 14 org repos — whole `.github` tree, `.yml` and `.yaml`, cross-repo `workflow_call` checked and absent — finds no workflow referencing either name.

The only Docker Hub credentials actually in use belong to `vs-dolt`, and they are **repo-level secrets under different names**:

```
vs-dolt   DOCKER_HUB_ACCESS_TOKEN   DOCKER_HUB_USERNAME     <- repo-level, underscore after DOCKER
vig-os    DOCKERHUB_TOKEN           DOCKERHUB_USERNAME      <- org-level, orphaned
```

So nothing has ever resolved the org pair. This is the same shape as the `APP_SYNC_ISSUES_*` orphans retired in #111 — an org secret shadowed by, or simply unrelated to, a repo-level secret of a similar name.

## Interim state (already done in #123)

Both are declared `visibility: 'selected'` with an **empty** repository list, so they reach nothing while their values are preserved. That is the safe, reversible half.

## Proposed

Retire them properly, following the #111 pattern:

1. Re-confirm zero consumers at the time of retirement (a repo may have gained a Docker Hub workflow in the meantime).
2. Drop both `orgs.newOrgSecret(...)` declarations from `otterdog/vig-os/vig-os.jsonnet`.
3. Delete the live org secrets out of band — `otterdog apply` never deletes secrets, so until the manual delete they surface as two pending deletions in the plan (exactly as #111 described).
4. CHANGELOG entry under **Removed**.

## Caveat before deleting

Confirm with @c-vigo whether the Docker Hub credentials are still needed anywhere at all — including for a repo not yet created, or a workflow currently disabled. Deleting an org secret is irreversible without the original token, and a Docker Hub token cannot be recovered, only reissued.

Related: #111 (the precedent), #123 (the sweep that found this).

