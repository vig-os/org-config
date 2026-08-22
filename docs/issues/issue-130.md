---
type: issue
state: closed
created: 2026-08-09T04:37:01Z
updated: 2026-08-10T09:45:07Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/130
comments: 4
labels: drift, critical
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-11T03:47:03.403Z
---

# [Issue 130]: [Drift: repo_ruleset[name="Main protection", repository=org-config]](https://github.com/vig-os/org-config/issues/130)

<!-- drift-fingerprint: 241ea1b92b34c2ed -->
## Drift detected: `repo_ruleset[name="Main protection", repository=org-config]`

- **Organization:** `vig-os`
- **Change type:** `change`
- **Last observed:** 2026-08-10 06:47 UTC

The live GitHub state diverges from the committed Otterdog config. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Plan diff</summary>

```text
  ~ repo_ruleset[name="Main protection", repository=org-config] {
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

