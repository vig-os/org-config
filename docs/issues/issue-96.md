---
type: issue
state: closed
created: 2026-08-07T05:03:01Z
updated: 2026-08-07T09:28:24Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/96
comments: 1
labels: drift, critical
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-08T03:28:22.713Z
---

# [Issue 96]: [Drift: add repo_ruleset[name="Main protection", repository=meta]](https://github.com/vig-os/org-config/issues/96)

<!-- drift-fingerprint: 74e266ecb38752a6 -->
## Drift detected: `add repo_ruleset[name="Main protection", repository=meta]`

- **Organization:** `vig-os`
- **Change type:** `add`
- **Last observed:** 2026-08-07 05:02 UTC

The live GitHub state diverges from the committed Otterdog config. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Plan diff</summary>

```text
  + add repo_ruleset[name="Main protection", repository=meta] {
    + allows_creations                    = true
    + allows_deletions                    = false
    + allows_force_pushes                 = false
    + allows_updates                      = true
    + bypass_actors                       = []
    + enforcement                         = "active"
    + exclude_refs                        = []
    + include_refs                        = [
      + "refs/heads/main"
    + ],
    + name                                = "Main protection"
    + required_pull_request               = {
      + dismisses_stale_reviews             = false
      + required_approving_review_count     = 0
      + requires_code_owner_review          = false
      + requires_last_push_approval         = false
      + requires_review_thread_resolution   = false
    + }
    + requires_commit_signatures          = true
    + requires_deployments                = false
    + requires_linear_history             = false
    + target                              = "branch"
  + }
```

</details>
---

# [Comment #1]() by [vig-os-org-config[bot]]()

_Posted on August 7, 2026 at 09:28 AM_

Drift resolved as of 2026-08-07 09:28 UTC: the divergence no longer appears in the plan (config and live state reconciled). Closing automatically.

