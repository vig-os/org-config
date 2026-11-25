---
type: issue
state: open
created: 2026-11-23T12:42:11Z
updated: 2026-11-24T13:44:06Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/360
comments: 4
labels: drift, critical
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-11-25T10:57:40.202Z
---

# [Issue 360]: [Drift: remove repo_variable[name="CACHIX_CACHE", repository=stepv]](https://github.com/vig-os/org-config/issues/360)

<!-- drift-fingerprint: a2099ad3ed4f1be6 -->
## Drift detected: `remove repo_variable[name="CACHIX_CACHE", repository=stepv]`

- **Organization:** `vig-os`
- **Change type:** `delete`
- **Last observed:** 2026-11-24 13:43 UTC

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

_Posted on November 23, 2026 at 04:08 PM_

Drift still present as of 2026-11-23 16:08 UTC. Refreshed the report above.

---

# [Comment #2]() by [vig-os-org-config[bot]]()

_Posted on November 23, 2026 at 04:09 PM_

Drift still present as of 2026-11-23 16:09 UTC. Refreshed the report above.

---

# [Comment #3]() by [vig-os-org-config[bot]]()

_Posted on November 23, 2026 at 04:09 PM_

Drift still present as of 2026-11-23 16:09 UTC. Refreshed the report above.

---

# [Comment #4]() by [vig-os-org-config[bot]]()

_Posted on November 24, 2026 at 01:44 PM_

Drift still present as of 2026-11-24 13:43 UTC. Refreshed the report above.

