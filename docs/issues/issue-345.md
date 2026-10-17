---
type: issue
state: open
created: 2026-10-13T10:37:04Z
updated: 2026-10-16T08:11:24Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/345
comments: 3
labels: drift, critical, inventory
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-10-17T06:42:04.433Z
---

# [Issue 345]: [Undeclared repository: ksb-ci-smoke](https://github.com/vig-os/org-config/issues/345)

<!-- drift-fingerprint: e09dbedd615070d6 -->
## Drift detected: `repository-inventory:ksb-ci-smoke`

- **Organization:** `vig-os`
- **Change type:** `undeclared`
- **Last observed:** 2026-10-16 08:11 UTC

The live GitHub state diverges from the committed Otterdog config. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Inventory finding</summary>

```text
Repository `vig-os/ksb-ci-smoke` exists in the live organization but is not declared in the committed Otterdog config.

Resolve by either:
  - adopting it into config (add `orgs.newRepo('ksb-ci-smoke')`, reconciled by apply), or
  - marking it intentionally out of scope in drift-allowlist.toml (`[[unmanaged]]`, ADR-0002 `managed: false`).
```

</details>
---

# [Comment #1]() by [vig-os-org-config[bot]]()

_Posted on October 14, 2026 at 08:44 AM_

Drift still present as of 2026-10-14 08:44 UTC. Refreshed the report above.

---

# [Comment #2]() by [vig-os-org-config[bot]]()

_Posted on October 15, 2026 at 08:18 AM_

Drift still present as of 2026-10-15 08:18 UTC. Refreshed the report above.

---

# [Comment #3]() by [vig-os-org-config[bot]]()

_Posted on October 16, 2026 at 08:11 AM_

Drift still present as of 2026-10-16 08:11 UTC. Refreshed the report above.

