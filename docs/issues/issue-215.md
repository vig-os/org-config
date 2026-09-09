---
type: issue
state: open
created: 2026-09-08T08:05:45Z
updated: 2026-09-08T08:05:45Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/215
comments: 0
labels: drift, critical
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-09T07:10:09.467Z
---

# [Issue 215]: [Drift: repository[name="tessera"]](https://github.com/vig-os/org-config/issues/215)

<!-- drift-fingerprint: 8ccca8a1149ecfa2 -->
## Drift detected: `repository[name="tessera"]`

- **Organization:** `vig-os`
- **Change type:** `change`
- **Last observed:** 2026-09-08 08:05 UTC

The live GitHub state diverges from the committed Otterdog config. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Plan diff</summary>

```text
  ~ repository[name="tessera"] {
    ~ default_branch = "dev" -> "main"
  ~ }
```

</details>
