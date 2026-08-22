---
type: issue
state: closed
created: 2026-08-07T05:03:08Z
updated: 2026-08-07T09:28:33Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/101
comments: 1
labels: drift, critical, inventory
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-08T03:28:20.908Z
---

# [Issue 101]: [Declared repository absent from org: os-config](https://github.com/vig-os/org-config/issues/101)

<!-- drift-fingerprint: af34028f67aa7870 -->
## Drift detected: `repository-inventory-missing:os-config`

- **Organization:** `vig-os`
- **Change type:** `absent`
- **Last observed:** 2026-08-07 05:02 UTC

The live GitHub state diverges from the committed Otterdog config. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Inventory finding</summary>

```text
Repository `os-config` is declared in the committed Otterdog config but does not exist in the live `vig-os` organization.

Creating it is apply's job; its silent absence is drift (ADR-0002). Resolve by running apply to create it, or removing the declaration if the repository is no longer wanted.
```

</details>
---

# [Comment #1]() by [vig-os-org-config[bot]]()

_Posted on August 7, 2026 at 09:28 AM_

Drift resolved as of 2026-08-07 09:28 UTC: the divergence no longer appears in the plan (config and live state reconciled). Closing automatically.

