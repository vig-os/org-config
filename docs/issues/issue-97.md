---
type: issue
state: closed
created: 2026-08-07T05:03:02Z
updated: 2026-08-07T09:28:27Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/97
comments: 1
labels: drift, critical
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-08T03:28:22.372Z
---

# [Issue 97]: [Drift: add repository[name="part-registry"]](https://github.com/vig-os/org-config/issues/97)

<!-- drift-fingerprint: 8e273e2e322b778f -->
## Drift detected: `add repository[name="part-registry"]`

- **Organization:** `vig-os`
- **Change type:** `add`
- **Last observed:** 2026-08-07 05:02 UTC

The live GitHub state diverges from the committed Otterdog config. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Plan diff</summary>

```text
  + add repository[name="part-registry"] {
    + allow_auto_merge                           = true
    + allow_forking                              = true
    + allow_merge_commit                         = true
    + allow_rebase_merge                         = false
    + allow_squash_merge                         = false
    + allow_update_branch                        = false
    + archived                                   = false
    + auto_init                                  = true
    + code_scanning_default_setup_enabled        = false
    + custom_properties                          = {
      + type                                       = [
        + "tools"
      + ],
    + }
    + default_branch                             = "main"
    + delete_branch_on_merge                     = true
    + dependabot_alerts_enabled                  = true
    + dependabot_security_updates_enabled        = false
    + description                                = "Registry of components, parts, assemblies"
    + gh_pages_build_type                        = "disabled"
    + has_discussions                            = false
    + has_issues                                 = true
    + has_projects                               = true
    + has_wiki                                   = true
    + is_template                                = true
    + merge_commit_message                       = "PR_BODY"
    + merge_commit_title                         = "PR_TITLE"
    + name                                       = "part-registry"
    + private                                    = false
    + private_vulnerability_reporting_enabled    = false
    + secret_scanning                            = "disabled"
    + secret_scanning_push_protection            = "disabled"
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

