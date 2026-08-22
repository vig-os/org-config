---
type: issue
state: closed
created: 2026-08-07T12:52:10Z
updated: 2026-08-07T12:58:32Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/111
comments: 1
labels: chore, priority:medium, area:ci, effort:small, semver:patch
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-08T03:28:18.851Z
---

# [Issue 111]: [Retire orphaned APP_SYNC_ISSUES org secrets](https://github.com/vig-os/org-config/issues/111)

## Summary

The `vig-os` **organization** secrets `APP_SYNC_ISSUES_ID` and
`APP_SYNC_ISSUES_PRIVATE_KEY` have **zero consumers**. They are declared in
`otterdog/vig-os/vig-os.jsonnet` (org `secrets` list) and exist live on the org,
but no workflow in any `vig-os` repo reads them at org scope. Retire them.

## Audit finding (2026-08-07)

A sweep of every `sync-issues.yml` across the org found:

- The only workflows referencing the names `APP_SYNC_ISSUES_ID` /
  `APP_SYNC_ISSUES_PRIVATE_KEY` are **`vig-os/tessera`**'s.
- `tessera` carries its **own repo-level secrets of the same names**, which
  shadow the org-level pair entirely. They belong to a *different* GitHub App —
  the repo-scoped `tessera-sync-issues-bot` (app_id `4483218`) — not the
  org-wide sync-issues App. This is already documented in the jsonnet beside the
  declaration ("same secret names, different App identity, so do not
  'deduplicate' these into org secrets"). **Those repo-level secrets stay.**
- Every other repo's `sync-issues.yml` authenticates with the `COMMIT_APP_*`
  secrets, not `APP_SYNC_ISSUES_*`.

So the org-level pair is orphaned scaffolding from before the `COMMIT_APP_*`
consolidation. Because a repo-level secret always wins over an org-level secret
of the same name, deleting the org pair cannot change what `tessera` resolves.

## Plan

Config-first, then live deletion (the standard order in this repo — the
declaration is the source of truth, the live object follows):

1. Remove the two `orgs.newOrgSecret('APP_SYNC_ISSUES_*')` entries from the org
   `secrets` list in `otterdog/vig-os/vig-os.jsonnet`. Do **not** touch
   `tessera`'s `orgs.newRepoSecret(...)` declarations. `CHANGELOG` `Removed`
   entry. Merge via PR (plan diff visible on the PR).
2. Delete the live org secrets with
   `gh api -X DELETE orgs/vig-os/actions/secrets/APP_SYNC_ISSUES_ID` (and
   `_PRIVATE_KEY`). `otterdog apply` deliberately does not delete secrets, so
   this step is manual by design.
3. Verify: both names gone from `gh api orgs/vig-os/actions/secrets`, and
   `tessera`'s repo-level pair still present and its next sync unaffected.

## Scope

Phase 1 of the GitHub App secret consolidation program. Later phases (client-ID
migration, `RELEASE_APP_ID` / `COMMIT_APP_ID` / `DEVKIT_UPGRADE_APP_ID` retirement)
are tracked separately and are **not** in scope here.

---

# [Comment #1]() by [c-vigo]()

_Posted on August 7, 2026 at 12:58 PM_

Closing evidence (the issue auto-closed on merge via the linked branch).

**Config** — PR #113, merged as `f854d00ea14d637656f43b7f60711ff7adc87904`. Both
`orgs.newOrgSecret('APP_SYNC_ISSUES_*')` entries removed from the `vig-os` org
`secrets` list; `tessera`'s `orgs.newRepoSecret(...)` declarations untouched.

**Plan on the PR** was exactly as expected — `0 to add, 1 to change, 2 to delete`
(the standing benign `vs-dolt` `code_scanning_default_languages` change, plus the
two now-undeclared live org secrets).

**Live deletion** (`otterdog apply` never deletes secrets, so this is manual by
design):

```
gh api -X DELETE orgs/vig-os/actions/secrets/APP_SYNC_ISSUES_ID
gh api -X DELETE orgs/vig-os/actions/secrets/APP_SYNC_ISSUES_PRIVATE_KEY
```

Both returned 204.

**Verification** — `gh api orgs/vig-os/actions/secrets --jq '.secrets[].name'`:

```
COMMIT_APP_CLIENT_ID
COMMIT_APP_ID
COMMIT_APP_PRIVATE_KEY
DEVKIT_UPGRADE_APP_ID
DEVKIT_UPGRADE_APP_PRIVATE_KEY
DOCKERHUB_TOKEN
DOCKERHUB_USERNAME
ORG_CONFIG_CANARY
RELEASE_APP_CLIENT_ID
RELEASE_APP_ID
RELEASE_APP_PRIVATE_KEY
```

Neither name is present.

`tessera` is unaffected — `gh api repos/vig-os/tessera/actions/secrets --jq '.secrets[].name'`
still lists `APP_SYNC_ISSUES_ID` and `APP_SYNC_ISSUES_PRIVATE_KEY`, and its
`sync-issues.yml` reads them at lines 57/58 and 98/99, resolving to the
repo-level values as before (a repo-level secret always shadowed the org one, so
nothing ever resolved to the pair just deleted).

Phase 1 of #112 complete.

