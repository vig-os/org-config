---
type: issue
state: open
created: 2026-10-10T09:51:26Z
updated: 2026-10-10T09:51:26Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/333
comments: 0
labels: drift, critical, unmanaged-control
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-10-11T08:25:12.990Z
---

# [Issue 333]: [Unmanaged control drift: org-secret reader lists diverge from the committed config](https://github.com/vig-os/org-config/issues/333)

<!-- drift-fingerprint: 2f8152958cfe1a5e -->
## Drift detected: `unmanaged-control:org:org-secret-repositories`

- **Organization:** `vig-os`
- **Change type:** `assert-failed`
- **Last observed:** 2026-10-10 09:51 UTC

The live GitHub control diverges from the value asserted for it in `unmanaged-controls.toml`. Otterdog has no schema field for this control, so it appears in no plan diff — the assertion table is its only declaration. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Live API assertion</summary>

```text
The repositories a `selected` org secret is shared with diverge from the committed list. A live-only entry is an unreviewed reader; a config-only entry is a consumer whose workflows now resolve the secret to an empty string, with no error.

- COMMIT_APP_CLIENT_ID: live-only [], config-only ['vigil']
- COMMIT_APP_PRIVATE_KEY: live-only [], config-only ['vigil']
- DEVKIT_UPGRADE_APP_CLIENT_ID: live-only [], config-only ['vigil']
- DEVKIT_UPGRADE_APP_PRIVATE_KEY: live-only [], config-only ['vigil']
- RELEASE_APP_CLIENT_ID: live-only [], config-only ['vigil']
- RELEASE_APP_PRIVATE_KEY: live-only [], config-only ['vigil']

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
