---
type: issue
state: closed
created: 2026-08-09T04:37:04Z
updated: 2026-08-10T09:48:24Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/137
comments: 5
labels: drift, critical
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-11T03:46:59.129Z
---

# [Issue 137]: [Drift: repo_ruleset[name="Dev protection", repository=sync-issues-action]](https://github.com/vig-os/org-config/issues/137)

<!-- drift-fingerprint: b2f75d8f06e3e7aa -->
## Drift detected: `repo_ruleset[name="Dev protection", repository=sync-issues-action]`

- **Organization:** `vig-os`
- **Change type:** `change`
- **Last observed:** 2026-08-10 06:47 UTC

The live GitHub state diverges from the committed Otterdog config. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Plan diff</summary>

```text
  ~ repo_ruleset[name="Dev protection", repository=sync-issues-action] {
    ~ required_status_checks     = {
      ~ status_checks              = [
        ~ "15368:CI Summary"        -> "github-actions:CI Summary"
      ~ ]
    ~ }
  ~ }
```

</details>
---

# [Comment #1]() by [vig-os-org-config[bot]]()

_Posted on August 10, 2026 at 04:54 AM_

Drift still present as of 2026-08-10 04:54 UTC. Refreshed the report above.

---

# [Comment #2]() by [vig-os-org-config[bot]]()

_Posted on August 10, 2026 at 06:46 AM_

Drift still present as of 2026-08-10 06:46 UTC. Refreshed the report above.

---

# [Comment #3]() by [vig-os-org-config[bot]]()

_Posted on August 10, 2026 at 06:46 AM_

Drift still present as of 2026-08-10 06:46 UTC. Refreshed the report above.

---

# [Comment #4]() by [vig-os-org-config[bot]]()

_Posted on August 10, 2026 at 06:47 AM_

Drift still present as of 2026-08-10 06:47 UTC. Refreshed the report above.

---

# [Comment #5]() by [vig-os-org-config[bot]]()

_Posted on August 10, 2026 at 09:48 AM_

Drift resolved as of 2026-08-10 09:48 UTC: the divergence no longer appears in the plan (config and live state reconciled). Closing automatically.

