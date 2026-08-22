---
type: issue
state: closed
created: 2026-07-30T14:34:18Z
updated: 2026-07-30T15:45:44Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/81
comments: 1
labels: none
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-07-31T05:38:40.760Z
---

# [Issue 81]: [feat: grant vigos-devkit-upgrade bypass on the Signed-commits ruleset across consumer repos](https://github.com/vig-os/org-config/issues/81)

## Context

The first full live run of the devkit-upgrade workflow (vig-os/devkit#1302, devkit-smoke-test run 30551310266) was rejected at push: consumer repos' **Signed commits** ruleset blocks the workflow's worktree commit (made inside `nix develop` so consumer hooks run — it cannot be API-signed without losing hook fidelity).

Resolution model: rulesets have bypass actors for exactly this. The `vigos-devkit-upgrade` App (id 4434545) gets `bypass_mode: always` on the Signed-commits ruleset. Applied by hand to devkit-smoke-test (2026-07-30) to complete the 1.5.0 validation — the adoption PR then opened cleanly (devkit-smoke-test#316).

## Ask

Reconciler support: add the App as a bypass actor on the Signed-commits ruleset in every devkit consumer repo (and document the requirement in the vig-os/devkit#1302 provisioning SSoT). Note fine print: the bypass covers the *push*; PR-level CI (commit message validation, drift gate) still applies to the bot's commits, which is the intended containment.

Refs: vig-os/devkit#1302
---

# [Comment #1]() by [c-vigo]()

_Posted on July 30, 2026 at 03:45 PM_

Superseded by vig-os/devkit#1308 after maintainer review: fleet-wide Signed-commits bypasses are the wrong model — verified signatures are policy. devkit-upgrade will instead replay the hook-validated tree via the API as a verified App-signed commit (commit-app pattern). The interim bypass on devkit-smoke-test has been reverted; no reconciler change needed.

