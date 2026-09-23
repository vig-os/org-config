---
type: issue
state: closed
created: 2026-09-14T10:46:41Z
updated: 2026-09-14T10:47:06Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/219
comments: 2
labels: drift, critical
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-15T07:21:41.950Z
---

# [Issue 219]: [Drift: repository[name="org-config-testbed"]](https://github.com/vig-os/org-config/issues/219)

<!-- drift-fingerprint: 0461b0f96f0e5c88 -->
## Drift detected: `repository[name="org-config-testbed"]`

- **Organization:** `vig-os`
- **Change type:** `change`
- **Last observed:** 2026-09-14 10:46 UTC

The live GitHub state diverges from the committed Otterdog config. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Plan diff</summary>

```text
  ~ repository[name="org-config-testbed"] {
    ~ description = "[DRIFT-E2E 34834826097] induced out-of-band flip; auto-reverted" -> "SACRIFICIAL testbed for the L3 mutation E2E harness (issue #23) - its live settings are deliberately churned and 
reverted by .github/workflows/testbed-e2e.yml on every run; do not rely on any state here."
  ~ }
```

</details>
---

# [Comment #1]() by [vig-os-org-config[bot]]()

_Posted on September 14, 2026 at 10:46 AM_

Drift still present as of 2026-09-14 10:46 UTC. Refreshed the report above.

---

# [Comment #2]() by [vig-os-org-config[bot]]()

_Posted on September 14, 2026 at 10:47 AM_

Drift resolved as of 2026-09-14 10:47 UTC: the divergence no longer appears in the plan (config and live state reconciled). Closing automatically.

