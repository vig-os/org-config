---
type: issue
state: closed
created: 2026-08-05T06:02:00Z
updated: 2026-08-07T08:54:48Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/86
comments: 2
labels: drift, critical
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-08T03:28:25.459Z
---

# [Issue 86]: [Drift: remove repo_secret[name="APP_SYNC_ISSUES_PRIVATE_KEY", repository=tessera]](https://github.com/vig-os/org-config/issues/86)

<!-- drift-fingerprint: 123e162b0d97fa33 -->
## Drift detected: `remove repo_secret[name="APP_SYNC_ISSUES_PRIVATE_KEY", repository=tessera]`

- **Organization:** `vig-os`
- **Change type:** `delete`
- **Last observed:** 2026-08-07 05:02 UTC

The live GitHub state diverges from the committed Otterdog config. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Plan diff</summary>

```text
  - remove repo_secret[name="APP_SYNC_ISSUES_PRIVATE_KEY", repository=tessera] {
    - name = "APP_SYNC_ISSUES_PRIVATE_KEY"
  - }
```

</details>
---

# [Comment #1]() by [vig-os-org-config[bot]]()

_Posted on August 6, 2026 at 06:05 AM_

Drift still present as of 2026-08-06 06:05 UTC. Refreshed the report above.

---

# [Comment #2]() by [vig-os-org-config[bot]]()

_Posted on August 7, 2026 at 05:03 AM_

Drift still present as of 2026-08-07 05:02 UTC. Refreshed the report above.

