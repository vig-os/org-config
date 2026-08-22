---
type: issue
state: closed
created: 2026-08-07T05:03:02Z
updated: 2026-08-07T09:28:29Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/98
comments: 1
labels: drift, critical
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-08T03:28:21.989Z
---

# [Issue 98]: [Drift: add repository[name="os-config"]](https://github.com/vig-os/org-config/issues/98)

<!-- drift-fingerprint: d718ad271fd006c7 -->
## Drift detected: `add repository[name="os-config"]`

- **Organization:** `vig-os`
- **Change type:** `add`
- **Last observed:** 2026-08-07 05:02 UTC

The live GitHub state diverges from the committed Otterdog config. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Plan diff</summary>

```text
  + add repository[name="os-config"] {
    + allow_auto_merge                           = false
    + allow_forking                              = true
    + allow_merge_commit                         = true
    + allow_rebase_merge                         = true
    + allow_squash_merge                         = true
    + allow_update_branch                        = false
    + archived                                   = false
    + auto_init                                  = true
    + code_scanning_default_languages            = [
      + "python"
    + ],
    + code_scanning_default_query_suite          = "default"
    + code_scanning_default_setup_enabled        = true
    + custom_properties                          = {
      + type                                       = [
        + "tools"
      + ],
    + }
    + default_branch                             = "main"
    + delete_branch_on_merge                     = false
    + dependabot_alerts_enabled                  = true
    + dependabot_security_updates_enabled        = false
    + description                                = "Reproducible OS configuration with for medtech-compliant deployments. Security hardening, audit logging, and ISO generation for air-gapped environments."
    + gh_pages_build_type                        = "disabled"
    + has_discussions                            = false
    + has_issues                                 = true
    + has_projects                               = true
    + has_wiki                                   = true
    + is_template                                = false
    + merge_commit_message                       = "PR_TITLE"
    + merge_commit_title                         = "MERGE_MESSAGE"
    + name                                       = "os-config"
    + private                                    = false
    + private_vulnerability_reporting_enabled    = true
    + secret_scanning                            = "enabled"
    + secret_scanning_push_protection            = "enabled"
    + squash_merge_commit_message                = "COMMIT_MESSAGES"
    + squash_merge_commit_title                  = "COMMIT_OR_PR_TITLE"
    + topics                                     = []
    + workflows                                  = {
      + actions_can_approve_pull_request_reviews   = true
      + enabled                                    = true
    + }
  + }
```

</details>
---

# [Comment #1]() by [vig-os-org-config[bot]]()

_Posted on August 7, 2026 at 09:28 AM_

Drift resolved as of 2026-08-07 09:28 UTC: the divergence no longer appears in the plan (config and live state reconciled). Closing automatically.

