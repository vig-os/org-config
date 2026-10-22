---
type: issue
state: open
created: 2026-10-13T10:37:05Z
updated: 2026-10-21T08:35:11Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/347
comments: 8
labels: drift, critical, unmanaged-control
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-10-22T07:14:58.043Z
---

# [Issue 347]: [Unmanaged control drift: Fork-PR workflow approval required on devkit](https://github.com/vig-os/org-config/issues/347)

<!-- drift-fingerprint: 6e94ced37ca4c195 -->
## Drift detected: `unmanaged-control:devkit:fork-pr-approval`

- **Organization:** `vig-os`
- **Change type:** `assert-failed`
- **Last observed:** 2026-10-21 08:34 UTC

The live GitHub control diverges from the value asserted for it in `unmanaged-controls.toml`. Otterdog has no schema field for this control, so it appears in no plan diff — the assertion table is its only declaration. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Live API assertion</summary>

```text
endpoint:  GET /repos/vig-os/devkit/actions/permissions/fork-pr-contributor-approval
path:      approval_policy
expected:  'first_time_contributors'
actual:    'all_external_contributors'

The repo-level policy overrides the org one, so the org row alone is not
sufficient: devkit is public and the fleet's supply-chain root, which makes it
the repo where an unreviewed fork run costs the most.
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

