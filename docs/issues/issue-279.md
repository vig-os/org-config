---
type: issue
state: closed
created: 2026-09-26T08:36:53Z
updated: 2026-09-26T14:17:19Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/279
comments: 0
labels: drift, critical
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-27T07:43:41.369Z
---

# [Issue 279]: [Drift: remove environment[name="commit-app", repository=devkit-smoke-test]](https://github.com/vig-os/org-config/issues/279)

<!-- drift-fingerprint: 5120e2b443f36f05 -->
## Drift detected: `remove environment[name="commit-app", repository=devkit-smoke-test]`

- **Organization:** `vig-os`
- **Change type:** `delete`
- **Last observed:** 2026-09-26 08:36 UTC

The live GitHub state diverges from the committed Otterdog config. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Plan diff</summary>

```text
  - remove environment[name="commit-app", repository=devkit-smoke-test] {
    - branch_policies          = [
      - "dev"
      - "main"
      - "release/*"
    - ],
    - deployment_branch_policy = "selected"
    - name                     = "commit-app"
    - prevent_self_review      = false
    - reviewers                = []
    - wait_timer               = 0
  - }
```

</details>
