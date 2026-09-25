---
type: issue
state: open
created: 2026-09-24T08:28:24Z
updated: 2026-09-24T08:28:24Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/254
comments: 0
labels: drift, critical
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-25T07:16:19.288Z
---

# [Issue 254]: [Drift: remove repo_secret[name="RP_APP_PRIVATE_KEY", repository=tessera]](https://github.com/vig-os/org-config/issues/254)

<!-- drift-fingerprint: 1b59d9787ea6908c -->
## Drift detected: `remove repo_secret[name="RP_APP_PRIVATE_KEY", repository=tessera]`

- **Organization:** `vig-os`
- **Change type:** `delete`
- **Last observed:** 2026-09-24 08:28 UTC

The live GitHub state diverges from the committed Otterdog config. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Plan diff</summary>

```text
  - remove repo_secret[name="RP_APP_PRIVATE_KEY", repository=tessera] {
    - name = "RP_APP_PRIVATE_KEY"
  - }
```

</details>
