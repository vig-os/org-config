---
type: issue
state: open
created: 2026-10-06T10:19:02Z
updated: 2026-10-07T10:16:43Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/326
comments: 1
labels: drift, critical
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-10-08T08:32:44.107Z
---

# [Issue 326]: [Drift: repo_ruleset[name="Main protection", repository=stepv]](https://github.com/vig-os/org-config/issues/326)

<!-- drift-fingerprint: ca5d400c3dcc42ed -->
## Drift detected: `repo_ruleset[name="Main protection", repository=stepv]`

- **Organization:** `vig-os`
- **Change type:** `change`
- **Last observed:** 2026-10-07 10:16 UTC

The live GitHub state diverges from the committed Otterdog config. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Plan diff</summary>

```text
  ~ repo_ruleset[name="Main protection", repository=stepv] {
    ~ required_pull_request               = {
      ~ required_approving_review_count     = 0 -> 1
    ~ }
    ~ required_status_checks              = {
      ~ status_checks                       = [
        ~ "15368:Kernel (macos-15)"      -> "15368:CI Summary"
        - "15368:Kernel (ubuntu-26.04)"
        - "15368:Lint & Format"
        - "15368:Tests"
        - "15368:Viewer (Linux, lavapipe)"
      ~ ]
      ~ strict                              = false -> true
    ~ }
  ~ }
```

</details>
---

# [Comment #1]() by [vig-os-org-config[bot]]()

_Posted on October 7, 2026 at 10:16 AM_

Drift still present as of 2026-10-07 10:16 UTC. Refreshed the report above.

