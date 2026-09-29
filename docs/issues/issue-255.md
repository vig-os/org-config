---
type: issue
state: open
created: 2026-09-24T08:28:25Z
updated: 2026-09-25T08:50:08Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/255
comments: 1
labels: drift, critical
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-26T07:11:55.896Z
---

# [Issue 255]: [Drift: remove repo_secret[name="RP_APP_ID", repository=tessera]](https://github.com/vig-os/org-config/issues/255)

<!-- drift-fingerprint: a327a50ca9108521 -->
## Drift detected: `remove repo_secret[name="RP_APP_ID", repository=tessera]`

- **Organization:** `vig-os`
- **Change type:** `delete`
- **Last observed:** 2026-09-25 08:49 UTC

The live GitHub state diverges from the committed Otterdog config. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Plan diff</summary>

```text
  - remove repo_secret[name="RP_APP_ID", repository=tessera] {
    - name = "RP_APP_ID"
  - }
```

</details>
---

# [Comment #1]() by [vig-os-org-config[bot]]()

_Posted on September 25, 2026 at 08:50 AM_

Drift still present as of 2026-09-25 08:49 UTC. Refreshed the report above.

