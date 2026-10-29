---
type: issue
state: open
created: 2026-10-26T08:56:17Z
updated: 2026-10-28T09:40:42Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/351
comments: 5
labels: drift, critical
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-10-29T08:10:29.845Z
---

# [Issue 351]: [Drift: remove org_variable[name="CI_RUNNER_SMALL"]](https://github.com/vig-os/org-config/issues/351)

<!-- drift-fingerprint: cd8a076aab6b83fa -->
## Drift detected: `remove org_variable[name="CI_RUNNER_SMALL"]`

- **Organization:** `vig-os`
- **Change type:** `delete`
- **Last observed:** 2026-10-28 09:40 UTC

The live GitHub state diverges from the committed Otterdog config. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Plan diff</summary>

```text
  - remove org_variable[name="CI_RUNNER_SMALL"] {
    - name                  = "CI_RUNNER_SMALL"
    - selected_repositories = []
    - value                 = "ksb-vig-os-small"
    - visibility            = "public"
  - }
```

</details>
---

# [Comment #1]() by [vig-os-org-config[bot]]()

_Posted on October 26, 2026 at 11:15 AM_

Drift still present as of 2026-10-26 11:14 UTC. Refreshed the report above.

---

# [Comment #2]() by [vig-os-org-config[bot]]()

_Posted on October 26, 2026 at 11:15 AM_

Drift still present as of 2026-10-26 11:15 UTC. Refreshed the report above.

---

# [Comment #3]() by [vig-os-org-config[bot]]()

_Posted on October 26, 2026 at 11:15 AM_

Drift still present as of 2026-10-26 11:15 UTC. Refreshed the report above.

---

# [Comment #4]() by [vig-os-org-config[bot]]()

_Posted on October 27, 2026 at 09:00 AM_

Drift still present as of 2026-10-27 09:00 UTC. Refreshed the report above.

---

# [Comment #5]() by [vig-os-org-config[bot]]()

_Posted on October 28, 2026 at 09:40 AM_

Drift still present as of 2026-10-28 09:40 UTC. Refreshed the report above.

