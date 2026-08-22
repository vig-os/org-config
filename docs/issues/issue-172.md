---
type: issue
state: closed
created: 2026-08-14T08:48:20Z
updated: 2026-08-22T08:34:11Z
author: vig-os-release-app[bot]
author_url: https://github.com/vig-os-release-app[bot]
url: https://github.com/vig-os/org-config/issues/172
comments: 1
labels: bug
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-22T09:25:35.667Z
---

# [Issue 172]: [Release 1.2.0 failed — automatic rollback](https://github.com/vig-os/org-config/issues/172)

Release 1.2.0 failed during the automated release workflow.

**Workflow Run:** [View logs](https://github.com/vig-os/org-config/actions/runs/31785289555)
**Release PR:** #171

**Automatic rollback attempted:**
- Release branch: this run's finalize commit(s) reverted, but only when the branch tip matched exactly what the run wrote — otherwise the branch is left untouched and the rollback step fails loudly instead (vig-os/devkit#1462)

**Tag status (forward-fix policy):**
- Release tags are not deleted by automation (workflow choice; GitHub immutable-release lock-in applies only after a release is **published** when that setting is enabled). If a tag was pushed before the failure, it remains on the remote.
- Use a new release candidate to validate fixes, then re-run the final release when ready.
- If a draft GitHub Release exists, manage it from the Releases UI; **publishing** locks the linked tag and assets when **immutable releases** are enabled.
---

# [Comment #1]() by [c-vigo]()

_Posted on August 22, 2026 at 08:34 AM_

Stale rollback artifact: the 1.2.0 release was recovered forward — v1.2.0 shipped 2026-08-14T09:06Z on the re-run and v1.2.1 (Latest) followed the same day. Tags and published releases verified present; per the forward-fix policy nothing remains to do here.

