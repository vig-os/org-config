---
type: issue
state: open
created: 2026-10-13T10:37:05Z
updated: 2026-10-13T10:37:05Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/347
comments: 0
labels: drift, critical, unmanaged-control
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-10-14T07:14:43.273Z
---

# [Issue 347]: [Unmanaged control drift: Fork-PR workflow approval required on devkit](https://github.com/vig-os/org-config/issues/347)

<!-- drift-fingerprint: 6e94ced37ca4c195 -->
## Drift detected: `unmanaged-control:devkit:fork-pr-approval`

- **Organization:** `vig-os`
- **Change type:** `assert-failed`
- **Last observed:** 2026-10-13 10:36 UTC

The live GitHub control diverges from the value asserted for it in `unmanaged-controls.toml`. Otterdog has no schema field for this control, so it appears in no plan diff — the assertion table is its only declaration. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Live API assertion</summary>

```text
endpoint:  GET /repos/vig-os/devkit/actions/permissions/fork-pr-contributor-approval
path:      approval_policy
expected:  'first_time_contributors'
actual:    'all_external_contributors'

The repo-level policy overrides the org one, so the org row alone is not
sufficient: devkit is public and the fleet's supply-chain root, which makes it
the repo where an unreviewed fork run costs the most.
```

</details>
