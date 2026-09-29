---
type: issue
state: closed
created: 2026-09-28T12:38:01Z
updated: 2026-09-28T17:35:44Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/295
comments: 0
labels: chore, priority:medium, area:ci, effort:small
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-29T08:00:42.845Z
---

# [Issue 295]: [chore(vig-os): drop scitadel's retired release-please credentials](https://github.com/vig-os/org-config/issues/295)

## Context

`scitadel` retired release-please in [vig-os/scitadel#207](https://github.com/vig-os/scitadel/issues/207)
(shipped in 0.8.0) and moved to the devkit release train. Three credentials it
declared for that bot are now dead: nothing in the repo references them.

Verified on `scitadel@dev` after the devkit 1.17.0 bump
([vig-os/scitadel#225](https://github.com/vig-os/scitadel/issues/225)):
`release-please.yml` and `scripts/setup-release-bot.sh` are deleted, and a
repo-wide grep finds no reader for any of the three.
`scitadel:docs/RELEASING.md:74-75` already states they can be deleted.

## The declarations

`otterdog/vig-os/vig-os.jsonnet`, inside the `orgs.newRepo('scitadel')` block
(line 806):

| Line | Declaration | Action |
|---|---|---|
| 823 | `orgs.newRepoSecret('RELEASE_BOT_PRIVATE_KEY')` | **remove** |
| 826 | `orgs.newRepoSecret('RELEASE_PLEASE_TOKEN')` | **remove** |
| 831 | `orgs.newRepoVariable('RELEASE_BOT_APP_ID')` (plaintext `3931309`) | **remove** |
| 820 | `orgs.newRepoSecret('CARGO_REGISTRY_TOKEN')` | **keep** |

`CARGO_REGISTRY_TOKEN` stays deliberately. `scitadel` moved crates.io publishing
to trusted publishing (OIDC) in
[vig-os/scitadel#224](https://github.com/vig-os/scitadel/issues/224), but
`publish-crates.yml:118-131` keeps the secret as an explicit fallback for when
trusted publishing is unavailable, and fails loudly if neither is present.

Removing the `variables:` array's only entry (831-833) empties it — drop the
array too if the schema prefers that over an empty list.

## Why this repo leads

Config-first: deleting the live repo variable without removing the declaration
means the next otterdog `apply` re-creates it, and drift reporting flags it in
between. So the jsonnet edit lands **first**, then the live credentials go.

[vig-os/scitadel#209](https://github.com/vig-os/scitadel/issues/209) carried this
as a cross-repo dependency and is now closed — its numeric-App-ID migration is
moot (the workflows that used numeric IDs are deleted, and the devkit scaffold
moved to `*_CLIENT_ID` at 1.17.0). Note that issue cites
`vig-os.jsonnet:504` for the variable; the declaration has since moved to **831**.

Its migration principle still governs the order here: *no numeric `*_APP_ID`
secret or variable is deleted while any pinned workflow still references it.*
Nothing references these, so the principle is satisfied rather than waived.

## Work

1. Remove lines 823-828 (both secrets) and 830-834 (the variables array) from the
   `scitadel` block.
2. `otterdog validate --local` and `otterdog plan` clean.
3. Apply, then delete the live values on `vig-os/scitadel`:
   ```
   gh secret delete RELEASE_BOT_PRIVATE_KEY --repo vig-os/scitadel
   gh secret delete RELEASE_PLEASE_TOKEN   --repo vig-os/scitadel
   gh variable delete RELEASE_BOT_APP_ID   --repo vig-os/scitadel
   ```
4. Optionally tidy `scitadel:docs/RELEASING.md:74-75`, which describes the
   deletion as pending.

## Acceptance Criteria

- [ ] The three declarations are gone; `CARGO_REGISTRY_TOKEN` remains
- [ ] `otterdog plan` / drift run is clean for `scitadel`
- [ ] `gh secret list` / `gh variable list` on `vig-os/scitadel` show none of the three
- [ ] A `scitadel` release still publishes to crates.io (trusted publishing path unaffected)

## Note on the App itself

App `3931309`'s private key is being removed from this repo's config only. If no
other consumer uses that App, consider deleting or rotating it at the org level
so an unused key is not left in existence.
