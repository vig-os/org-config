---
type: issue
state: open
created: 2026-09-30T20:18:58Z
updated: 2026-09-30T20:18:58Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/315
comments: 0
labels: chore
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-10-01T08:28:24.941Z
---

# [Issue 315]: [[CHORE] Retire the numeric COMMIT_APP_ID / DEVKIT_UPGRADE_APP_ID / RELEASE_APP_ID org secrets](https://github.com/vig-os/org-config/issues/315)

### Chore Type

Configuration change

### Description

This covers **phase 3 and the final step of phase 4 of #112**: deleting the numeric App-ID org secrets that duplicate the client ID.

- `COMMIT_APP_ID`
- `DEVKIT_UPGRADE_APP_ID`
- `RELEASE_APP_ID`

The devkit side is done. vig-os/devkit#1366 (merged to devkit `dev` in vig-os/devkit#1792, 2026-09-30) drops the `|| secrets.DEVKIT_UPGRADE_APP_ID` fallback from the scaffolded `devkit-upgrade.yml`. From the next devkit release, no current scaffold reads any numeric `*_APP_ID`.

Deletion is still **blocked**: code search on 2026-09-30 found these workflows still reading the numeric secrets.

| Secret | Still read by | Why |
|---|---|---|
| `COMMIT_APP_ID` | `vig-os/scitadel`: `sync-issues.yml` (`app-id:`), `renovate-changelog.yml` (`app-id:`) | scitadel is still on the devkit **1.6.0** scaffold (`DEVKIT_VERSION=1.6.0`) and reads it as its **only** ID, not as a fallback. This is #112's phase 2 straggler (vig-os/scitadel#209 / #207). |
| `DEVKIT_UPGRADE_APP_ID` | `devkit-upgrade.yml` in `commit-action`, `devkit-smoke-test`, `scitadel`, `sync-issues-action`, `tessera` (plus the exo-pet org's consumers) | As a **fallback** only (`CLIENT_ID \|\| APP_ID`). The reference disappears when each repo adopts the devkit release that ships #1366. |
| `RELEASE_APP_ID` | none found | It is unreferenced now, so it is only kept by the ordering rule below. |

Every vig-os repo that currently reads the legacy `DEVKIT_UPGRADE_APP_ID` is also on the `DEVKIT_UPGRADE_APP_CLIENT_ID` reader list, so no repo loses its App identity when the fallback goes.

The ordering constraint is #112's: **a numeric ID may only be deleted after the last workflow that reads it is re-scaffolded.** Deleting a secret too early does not error. The workflow silently resolves it to an empty string (the playground `COMMIT_APP_ID` incident).

### Acceptance Criteria

- [ ] The devkit release carrying vig-os/devkit#1366 is published, and its `devkit-upgrade` adoption PR is merged in every vig-os consumer listed above
- [ ] `vig-os/scitadel` is re-scaffolded off devkit 1.6.0 (#112 phase 2), and a fleet code search for `secrets.COMMIT_APP_ID` returns no workflow hits
- [ ] A fleet code search for `secrets.DEVKIT_UPGRADE_APP_ID` and `secrets.RELEASE_APP_ID` returns no workflow hits in the vig-os org
- [ ] `otterdog/vig-os/vig-os.jsonnet`: remove the `COMMIT_APP_ID`, `DEVKIT_UPGRADE_APP_ID` and `RELEASE_APP_ID` declarations, and update `unmanaged-controls.toml` reader lists if they are asserted there. Merge that first, then delete the live secrets (the paired-edit order from #111).
- [ ] The exo-pet org's own config repo gets the same `DEVKIT_UPGRADE_APP_ID` retirement once its consumers adopt (it already has no numeric `COMMIT_APP_ID`/`RELEASE_APP_ID`)
- [ ] The exoma-ch org's live `COMMIT_APP_ID` / `RELEASE_APP_ID` are deleted after the same check (not declared in this repo)
- [ ] vig-os/devkit#1366's final checkbox is ticked

### Implementation Notes

- Verify each gate with code search rather than from memory: `gh search code "secrets.<NAME>" --owner <org>`, then filter to `.github/workflows/` and `.github/actions/`. Synced `docs/issues` / `docs/pull-requests` archives also mention these names; those hits are not consumers.
- `RELEASE_APP_ID` could go today, but keeping the three deletions in one paired edit is simpler and needs only one drift re-check.
- #313 (revkit missing from the live reader lists) touches the same reader lists. Land that first, or at least don't re-add revkit to the numeric secrets' lists when fixing it.

### Related Issues

Parent: #112 (phases 3–4). Devkit: vig-os/devkit#1366 (fallback removal), vig-os/devkit#1365 (client-ID rename). Blocker: vig-os/scitadel#209. Related: #111 (paired-edit precedent), #313 (reader-list drift).

### Priority

Low

### Changelog Category

Removed

