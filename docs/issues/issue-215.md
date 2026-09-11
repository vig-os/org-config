---
type: issue
state: open
created: 2026-09-08T08:05:45Z
updated: 2026-09-10T08:08:53Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/215
comments: 2
labels: drift, critical
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-11T07:06:09.981Z
---

# [Issue 215]: [Drift: repository[name="tessera"]](https://github.com/vig-os/org-config/issues/215)

<!-- drift-fingerprint: 8ccca8a1149ecfa2 -->
## Drift detected: `repository[name="tessera"]`

- **Organization:** `vig-os`
- **Change type:** `change`
- **Last observed:** 2026-09-10 08:08 UTC

The live GitHub state diverges from the committed Otterdog config. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Plan diff</summary>

```text
  ~ repository[name="tessera"] {
    ~ default_branch = "dev" -> "main"
  ~ }
```

</details>
---

# [Comment #1]() by [vig-os-org-config[bot]]()

_Posted on September 9, 2026 at 08:09 AM_

Drift still present as of 2026-09-09 08:09 UTC. Refreshed the report above.

---

# [Comment #2]() by [vig-os-org-config[bot]]()

_Posted on September 10, 2026 at 08:08 AM_

Drift still present as of 2026-09-10 08:08 UTC. Refreshed the report above.

