---
type: issue
state: open
created: 2026-10-13T10:37:03Z
updated: 2026-10-14T08:44:15Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/343
comments: 1
labels: drift, critical
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-10-15T07:06:24.477Z
---

# [Issue 343]: [Drift: remove repo_variable[name="CACHIX_CACHE", repository=stepv]](https://github.com/vig-os/org-config/issues/343)

<!-- drift-fingerprint: a2099ad3ed4f1be6 -->
## Drift detected: `remove repo_variable[name="CACHIX_CACHE", repository=stepv]`

- **Organization:** `vig-os`
- **Change type:** `delete`
- **Last observed:** 2026-10-14 08:44 UTC

The live GitHub state diverges from the committed Otterdog config. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Plan diff</summary>

```text
  - remove repo_variable[name="CACHIX_CACHE", repository=stepv] {
    - name  = "CACHIX_CACHE"
    - value = "gerchowl"
  - }
```

</details>
---

# [Comment #1]() by [vig-os-org-config[bot]]()

_Posted on October 14, 2026 at 08:44 AM_

Drift still present as of 2026-10-14 08:44 UTC. Refreshed the report above.

