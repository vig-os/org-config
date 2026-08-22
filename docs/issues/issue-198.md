---
type: issue
state: open
created: 2026-08-22T09:21:03Z
updated: 2026-08-22T09:21:03Z
author: vig-os-release-app[bot]
author_url: https://github.com/vig-os-release-app[bot]
url: https://github.com/vig-os/org-config/issues/198
comments: 0
labels: bug
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-22T09:25:33.944Z
---

# [Issue 198]: [Release 1.2.2 failed — automatic rollback](https://github.com/vig-os/org-config/issues/198)

Release 1.2.2 failed during the automated release workflow.

**Workflow Run:** [View logs](https://github.com/vig-os/org-config/actions/runs/32564607043)
**Release PR:** #197

**Automatic rollback attempted:**
- Release branch: this run's finalize commit(s) reverted, but only when the branch tip matched exactly what the run wrote — otherwise the branch is left untouched and the rollback step fails loudly instead (vig-os/devkit#1462)

**Tag status (forward-fix policy):**
- Release tags are not deleted by automation (workflow choice; GitHub immutable-release lock-in applies only after a release is **published** when that setting is enabled). If a tag was pushed before the failure, it remains on the remote.
- Use a new release candidate to validate fixes, then re-run the final release when ready.
- If a draft GitHub Release exists, manage it from the Releases UI; **publishing** locks the linked tag and assets when **immutable releases** are enabled.
