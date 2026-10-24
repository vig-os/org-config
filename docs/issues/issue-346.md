---
type: issue
state: open
created: 2026-10-13T10:37:05Z
updated: 2026-10-23T08:33:38Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/346
comments: 10
labels: drift, critical, unmanaged-control
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-10-24T06:58:03.567Z
---

# [Issue 346]: [Unmanaged control drift: Fork-PR workflow approval required org-wide](https://github.com/vig-os/org-config/issues/346)

<!-- drift-fingerprint: 33354df00e3061fc -->
## Drift detected: `unmanaged-control:org:fork-pr-approval`

- **Organization:** `vig-os`
- **Change type:** `assert-failed`
- **Last observed:** 2026-10-23 08:33 UTC

The live GitHub control diverges from the value asserted for it in `unmanaged-controls.toml`. Otterdog has no schema field for this control, so it appears in no plan diff — the assertion table is its only declaration. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Live API assertion</summary>

```text
endpoint:  GET /orgs/vig-os/actions/permissions/fork-pr-contributor-approval
path:      approval_policy
expected:  'first_time_contributors'
actual:    'all_external_contributors'

Fork-PR workflow runs execute attacker-supplied code against this org's runners
(OWASP CICD-SEC-4). `first_time_contributors` is the live policy and what this
row locks in — a silent widening to `never` would let any fork run workflows
unreviewed. Hardening further to `all_external_contributors` is a separate
posture decision, deliberately not conflated with standing up the detector.
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

