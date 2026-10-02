---
type: issue
state: open
created: 2026-09-30T09:42:55Z
updated: 2026-10-01T10:09:12Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/313
comments: 2
labels: drift, critical, unmanaged-control
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-10-02T08:04:13.761Z
---

# [Issue 313]: [Unmanaged control drift: org-secret reader lists diverge from the committed config](https://github.com/vig-os/org-config/issues/313)

<!-- drift-fingerprint: 2f8152958cfe1a5e -->
## Drift detected: `unmanaged-control:org:org-secret-repositories`

- **Organization:** `vig-os`
- **Change type:** `assert-failed`
- **Last observed:** 2026-10-01 10:09 UTC

The live GitHub control diverges from the value asserted for it in `unmanaged-controls.toml`. Otterdog has no schema field for this control, so it appears in no plan diff — the assertion table is its only declaration. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Live API assertion</summary>

```text
The repositories a `selected` org secret is shared with diverge from the committed list. A live-only entry is an unreviewed reader; a config-only entry is a consumer whose workflows now resolve the secret to an empty string, with no error.

- COMMIT_APP_CLIENT_ID: live-only [], config-only ['revkit']
- COMMIT_APP_ID: live-only [], config-only ['revkit']
- COMMIT_APP_PRIVATE_KEY: live-only [], config-only ['revkit']
- DEVKIT_UPGRADE_APP_CLIENT_ID: live-only [], config-only ['revkit']
- DEVKIT_UPGRADE_APP_PRIVATE_KEY: live-only [], config-only ['revkit']
- RELEASE_APP_CLIENT_ID: live-only [], config-only ['revkit']
- RELEASE_APP_ID: live-only [], config-only ['revkit']
- RELEASE_APP_PRIVATE_KEY: live-only [], config-only ['revkit']

Otterdog structurally cannot police org-secret metadata: nine of the ten
committed org secrets carry a `'********'` dummy value, so `include_for_live_patch`
is false and its plan skips them entirely. A visibility widened in the UI, or a
reader list hand-edited through `PUT /orgs/{org}/actions/secrets/{name}/repositories`
(which needs no secret value), therefore produces no diff at all — the exact
operations #123 used to narrow all ten secrets to `selected` are the ones that
can silently undo it. Each family opens at most ONE issue listing every
offender. `assert_no_undeclared` is on because a live org secret with no
committed declaration is an unreviewed credential: nothing records who created
it, what reads it, or when it should be rotated.
```

</details>
---

# [Comment #1]() by [c-vigo]()

_Posted on September 30, 2026 at 08:19 PM_

Consequence of this drift, seen from devkit: `vig-os/revkit` carries the scaffolded `devkit-upgrade.yml`, `sync-issues.yml` and release train. Because it is on none of these live reader lists, its `secrets.COMMIT_APP_*`, `secrets.DEVKIT_UPGRADE_APP_*` and `secrets.RELEASE_APP_*` all resolve to empty strings. So the weekly upgrade fails its App-identity preflight, and sync and release cannot mint tokens. Resolve it by applying the committed lists (adding revkit), not by removing it from config.

When applying, only the client-ID and private-key secrets matter going forward. The numeric `COMMIT_APP_ID` / `RELEASE_APP_ID` are being retired in #315, so adding revkit to them is harmless but unnecessary.

---

# [Comment #2]() by [vig-os-org-config[bot]]()

_Posted on October 1, 2026 at 10:09 AM_

Drift still present as of 2026-10-01 10:09 UTC. Refreshed the report above.

