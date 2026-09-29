---
type: issue
state: closed
created: 2026-09-24T08:04:37Z
updated: 2026-09-24T08:37:16Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/252
comments: 0
labels: chore, priority:medium, area:ci, effort:small
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-25T07:16:19.598Z
---

# [Issue 252]: [[CHORE] Grant tessera the org App secrets its devkit scaffold reads](https://github.com/vig-os/org-config/issues/252)

### Chore Type

Configuration change

### Description

`vig-os/tessera` is adopting the devkit scaffold ([tessera#364](https://github.com/vig-os/tessera/issues/364)) and its managed workflows mint GitHub App tokens from **org** secrets whose `visibility` is `selected`. `tessera` is on none of those lists, so on merge its `sync-issues.yml` and `devkit-upgrade.yml` would receive empty credentials.

That failure mode is the one the `DEVKIT_UPGRADE_APP_ID` comment in `vig-os.jsonnet` already warns about — *"its upgrade workflow fails with an empty credential and no error"* — so this is a known trap, not a discovery.

Grant `tessera` the four secrets its scaffold actually reads.

### Acceptance Criteria

- [ ] `tessera` added to `selected_repositories` for **`COMMIT_APP_CLIENT_ID`**, **`COMMIT_APP_PRIVATE_KEY`**, **`DEVKIT_UPGRADE_APP_CLIENT_ID`** and **`DEVKIT_UPGRADE_APP_PRIVATE_KEY`**.
- [ ] **Not** added to `COMMIT_APP_ID` or `DEVKIT_UPGRADE_APP_ID` — see below.
- [ ] The prose above each list is updated, not just the list: those comments enumerate which repos are on which ID form and why, and a silent list edit makes them wrong.
- [ ] `plan` shows exactly four `~ modify` lines against the four secrets and nothing else.
- [ ] `CHANGELOG.md` `## Unreleased` entry.

### Implementation Notes

**Derived from the files, not assumed** — the reference forms in tessera's freshly scaffolded workflows at devkit **1.16.0**:

| Workflow | Reads |
|---|---|
| `sync-issues.yml` | `client-id: ${{ secrets.COMMIT_APP_CLIENT_ID }}` + `COMMIT_APP_PRIVATE_KEY` — client-ID form only, no numeric fallback |
| `devkit-upgrade.yml` | `DEVKIT_UPGRADE_APP_CLIENT_ID` with `DEVKIT_UPGRADE_APP_ID` as a legacy fallback (`if { [ -z CLIENT_ID ] && [ -z ID_LEGACY ]; } || [ -z PRIVATE_KEY ]`) + `DEVKIT_UPGRADE_APP_PRIVATE_KEY` |

So the client-ID form alone satisfies both. Adding `tessera` to the two numeric-ID lists would hand it a credential nothing reads and enlarge a surface [#112](https://github.com/vig-os/org-config/issues/112) is trying to retire. This makes tessera the **first repo on the client-ID form from day one**, with no numeric entry to retire later.

Two other secrets appear in the scaffolded workflows and need **no** action:

- **`GHCR_PULL_TOKEN`** — referenced by `ci.yml` and `sync-issues.yml`, but it is not an org secret, not in this config, and not a repo secret anywhere: `h5v` runs the same scaffold with **zero** repo secrets. It is an optional fallback for pulling the public devcontainer image; `GITHUB_TOKEN` covers it.
- **`CACHIX_AUTH_TOKEN`** — declared in this config as a **repo** secret for the repo that uses it, and optional in `ci.yml`.

Lists are alphabetical, so `tessera` appends after `sync-issues-action` in each.

### Related Issues

Refs [tessera#364](https://github.com/vig-os/tessera/issues/364) (the scaffold adoption this unblocks), [#112](https://github.com/vig-os/org-config/issues/112) / [#123](https://github.com/vig-os/org-config/issues/123) (client-ID migration and the `selected` visibility work these lists came from).

### Priority

Medium

### Changelog Category

Changed

### Additional Context

Merging applies to the live org, which is the intent — the grant must exist before tessera's scaffold PR merges, or its first scheduled `sync-issues` run fails silently.

Unrelated drift to expect on this PR's plan: `tessera` carries two undeclared repo secrets (`RP_APP_ID`, `RP_APP_PRIVATE_KEY`, created 2026-09-23) that show as proposed deletions on every plan right now. They are not touched by this change and nothing can delete them (`apply` omits `--delete-resources`).

