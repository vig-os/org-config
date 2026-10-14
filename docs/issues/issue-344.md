---
type: issue
state: open
created: 2026-10-13T10:37:04Z
updated: 2026-10-13T10:37:04Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/344
comments: 0
labels: drift, critical
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-10-14T07:14:44.759Z
---

# [Issue 344]: [Drift: remove repo_secret[name="CACHIX_AUTH_TOKEN", repository=stepv]](https://github.com/vig-os/org-config/issues/344)

<!-- drift-fingerprint: bdad66d194a35d88 -->
## Drift detected: `remove repo_secret[name="CACHIX_AUTH_TOKEN", repository=stepv]`

- **Organization:** `vig-os`
- **Change type:** `delete`
- **Last observed:** 2026-10-13 10:36 UTC

The live GitHub state diverges from the committed Otterdog config. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Plan diff</summary>

```text
  - remove repo_secret[name="CACHIX_AUTH_TOKEN", repository=stepv] {
    - name = "CACHIX_AUTH_TOKEN"
  - }
```

</details>
