---
type: issue
state: open
created: 2026-10-13T10:37:05Z
updated: 2026-11-10T11:13:27Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/347
comments: 28
labels: drift, critical, unmanaged-control
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-11-11T08:58:51.177Z
---

# [Issue 347]: [Unmanaged control drift: Fork-PR workflow approval required on devkit](https://github.com/vig-os/org-config/issues/347)

<!-- drift-fingerprint: 6e94ced37ca4c195 -->
## Drift detected: `unmanaged-control:devkit:fork-pr-approval`

- **Organization:** `vig-os`
- **Change type:** `assert-failed`
- **Last observed:** 2026-11-10 11:13 UTC

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

---

# [Comment #9]() by [vig-os-org-config[bot]]()

_Posted on October 22, 2026 at 08:37 AM_

Drift still present as of 2026-10-22 08:37 UTC. Refreshed the report above.

---

# [Comment #10]() by [vig-os-org-config[bot]]()

_Posted on October 23, 2026 at 08:33 AM_

Drift still present as of 2026-10-23 08:33 UTC. Refreshed the report above.

---

# [Comment #11]() by [vig-os-org-config[bot]]()

_Posted on October 24, 2026 at 08:08 AM_

Drift still present as of 2026-10-24 08:08 UTC. Refreshed the report above.

---

# [Comment #12]() by [vig-os-org-config[bot]]()

_Posted on October 25, 2026 at 08:25 AM_

Drift still present as of 2026-10-25 08:25 UTC. Refreshed the report above.

---

# [Comment #13]() by [vig-os-org-config[bot]]()

_Posted on October 26, 2026 at 08:56 AM_

Drift still present as of 2026-10-26 08:56 UTC. Refreshed the report above.

---

# [Comment #14]() by [vig-os-org-config[bot]]()

_Posted on October 27, 2026 at 09:00 AM_

Drift still present as of 2026-10-27 09:00 UTC. Refreshed the report above.

---

# [Comment #15]() by [vig-os-org-config[bot]]()

_Posted on October 28, 2026 at 09:40 AM_

Drift still present as of 2026-10-28 09:40 UTC. Refreshed the report above.

---

# [Comment #16]() by [vig-os-org-config[bot]]()

_Posted on October 29, 2026 at 09:59 AM_

Drift still present as of 2026-10-29 09:58 UTC. Refreshed the report above.

---

# [Comment #17]() by [vig-os-org-config[bot]]()

_Posted on October 30, 2026 at 10:01 AM_

Drift still present as of 2026-10-30 10:01 UTC. Refreshed the report above.

---

# [Comment #18]() by [vig-os-org-config[bot]]()

_Posted on October 31, 2026 at 09:40 AM_

Drift still present as of 2026-10-31 09:39 UTC. Refreshed the report above.

---

# [Comment #19]() by [vig-os-org-config[bot]]()

_Posted on November 1, 2026 at 10:28 AM_

Drift still present as of 2026-11-01 10:28 UTC. Refreshed the report above.

---

# [Comment #20]() by [vig-os-org-config[bot]]()

_Posted on November 2, 2026 at 11:08 AM_

Drift still present as of 2026-11-02 11:08 UTC. Refreshed the report above.

---

# [Comment #21]() by [vig-os-org-config[bot]]()

_Posted on November 3, 2026 at 10:53 AM_

Drift still present as of 2026-11-03 10:53 UTC. Refreshed the report above.

---

# [Comment #22]() by [vig-os-org-config[bot]]()

_Posted on November 4, 2026 at 10:56 AM_

Drift still present as of 2026-11-04 10:56 UTC. Refreshed the report above.

---

# [Comment #23]() by [vig-os-org-config[bot]]()

_Posted on November 5, 2026 at 10:57 AM_

Drift still present as of 2026-11-05 10:56 UTC. Refreshed the report above.

---

# [Comment #24]() by [vig-os-org-config[bot]]()

_Posted on November 6, 2026 at 10:53 AM_

Drift still present as of 2026-11-06 10:53 UTC. Refreshed the report above.

---

# [Comment #25]() by [vig-os-org-config[bot]]()

_Posted on November 7, 2026 at 10:10 AM_

Drift still present as of 2026-11-07 10:10 UTC. Refreshed the report above.

---

# [Comment #26]() by [vig-os-org-config[bot]]()

_Posted on November 8, 2026 at 10:23 AM_

Drift still present as of 2026-11-08 10:23 UTC. Refreshed the report above.

---

# [Comment #27]() by [vig-os-org-config[bot]]()

_Posted on November 9, 2026 at 11:33 AM_

Drift still present as of 2026-11-09 11:32 UTC. Refreshed the report above.

---

# [Comment #28]() by [vig-os-org-config[bot]]()

_Posted on November 10, 2026 at 11:13 AM_

Drift still present as of 2026-11-10 11:13 UTC. Refreshed the report above.

