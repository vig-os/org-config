---
type: issue
state: open
created: 2026-10-13T10:37:02Z
updated: 2026-10-13T10:37:02Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/342
comments: 0
labels: drift, critical
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-10-14T07:14:45.743Z
---

# [Issue 342]: [Drift: remove repository[name="ksb-ci-smoke"]](https://github.com/vig-os/org-config/issues/342)

<!-- drift-fingerprint: 8fd4141c5ee431ec -->
## Drift detected: `remove repository[name="ksb-ci-smoke"]`

- **Organization:** `vig-os`
- **Change type:** `delete`
- **Last observed:** 2026-10-13 10:36 UTC

The live GitHub state diverges from the committed Otterdog config. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Plan diff</summary>

```text
  - remove repository[name="ksb-ci-smoke"] {
    - allow_auto_merge                           = false
    - allow_forking                              = false
    - allow_merge_commit                         = true
    - allow_rebase_merge                         = true
    - allow_squash_merge                         = true
    - allow_update_branch                        = false
    - archived                                   = false
    - code_scanning_default_setup_enabled        = false
    - custom_properties                          = {
      - type                                       = [
        - "internal"
      - ],
    - }
    - default_branch                             = "main"
    - delete_branch_on_merge                     = false
    - dependabot_alerts_enabled                  = false
    - description                                = "Smoke test for the ksb ARC runners"
    - gh_pages_build_type                        = "disabled"
    - has_discussions                            = false
    - has_issues                                 = true
    - has_projects                               = true
    - has_wiki                                   = false
    - homepage                                   = null
    - is_template                                = false
    - merge_commit_message                       = "PR_TITLE"
    - merge_commit_title                         = "MERGE_MESSAGE"
    - name                                       = "ksb-ci-smoke"
    - private                                    = true
    - squash_merge_commit_message                = "COMMIT_MESSAGES"
    - squash_merge_commit_title                  = "COMMIT_OR_PR_TITLE"
    - template_repository                        = null
    - topics                                     = []
    - web_commit_signoff_required                = true
    - workflows                                  = {
      - actions_can_approve_pull_request_reviews   = false
      - allow_action_patterns                      = []
      - allow_github_owned_actions                 = null
      - allow_verified_creator_actions             = null
      - allowed_actions                            = "all"
      - default_workflow_permissions               = "read"
      - enabled                                    = true
    - }
  - }
```

</details>
