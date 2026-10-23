---
type: issue
state: open
created: 2026-10-13T10:37:04Z
updated: 2026-10-22T08:37:23Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/345
comments: 9
labels: drift, critical, inventory
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-10-23T07:06:52.949Z
---

# [Issue 345]: [Undeclared repository: ksb-ci-smoke](https://github.com/vig-os/org-config/issues/345)

<!-- drift-fingerprint: e09dbedd615070d6 -->
## Drift detected: `repository-inventory:ksb-ci-smoke`

- **Organization:** `vig-os`
- **Change type:** `undeclared`
- **Last observed:** 2026-10-22 08:37 UTC

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

---

# [Comment #4]() by [vig-os-org-config[bot]]()

_Posted on October 17, 2026 at 07:48 AM_

Drift still present as of 2026-10-17 07:48 UTC. Refreshed the report above.

---

# [Comment #5]() by [vig-os-org-config[bot]]()

_Posted on October 18, 2026 at 08:02 AM_

Drift still present as of 2026-10-18 08:02 UTC. Refreshed the report above.

---

# [Comment #6]() by [vig-os-org-config[bot]]()

_Posted on October 19, 2026 at 08:53 AM_

Drift still present as of 2026-10-19 08:53 UTC. Refreshed the report above.

---

# [Comment #7]() by [vig-os-org-config[bot]]()

_Posted on October 20, 2026 at 08:33 AM_

Drift still present as of 2026-10-20 08:33 UTC. Refreshed the report above.

---

# [Comment #8]() by [vig-os-org-config[bot]]()

_Posted on October 21, 2026 at 08:35 AM_

Drift still present as of 2026-10-21 08:34 UTC. Refreshed the report above.

---

# [Comment #9]() by [vig-os-org-config[bot]]()

_Posted on October 22, 2026 at 08:37 AM_

Drift still present as of 2026-10-22 08:37 UTC. Refreshed the report above.

