---
type: issue
state: closed
created: 2026-09-23T20:30:26Z
updated: 2026-09-23T20:45:19Z
author: vigos-devkit-upgrade[bot]
author_url: https://github.com/vigos-devkit-upgrade[bot]
url: https://github.com/vig-os/org-config/issues/242
comments: 0
labels: none
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-23T21:09:30.742Z
---

# [Issue 242]: [chore(devkit): automated devkit upgrade is failing](https://github.com/vig-os/org-config/issues/242)

<!-- devkit-upgrade-failure -->

The managed devkit-upgrade workflow is failing, so this repo has stopped adopting new devkit releases.

- Run: https://github.com/vig-os/org-config/actions/runs/35916200558
- Failing step: Commit the upgrade in the project shell
- Pinned devkit version: 1.15.1
- Target devkit version: 1.16.0
Nothing was pushed: the adoption branch only reaches the remote once the upgrade commit is published, so there is no half-applied state to clean up. Fix the cause and re-run the workflow (or dispatch it with an explicit version) — this issue is filed, updated and closed by the workflow itself.
