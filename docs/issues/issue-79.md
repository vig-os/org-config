---
type: issue
state: closed
created: 2026-07-27T16:45:39Z
updated: 2026-07-28T11:41:38Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/79
comments: 0
labels: none
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-07-28T11:43:10.354Z
---

# [Issue 79]: [Point sync-issues at an unprotected mirror branch (DEVKIT_SYNC_TARGET)](https://github.com/vig-os/org-config/issues/79)

Nightly sync-issues fails on delta days: the job pushes snapshot docs directly to `main`, which the require-PR + CI-Summary ruleset rejects (e.g. run of 2026-07-25). Fix: set `DEVKIT_SYNC_TARGET=sync/issue-mirror` in `.vig-os` and re-render the scaffold — the devkit-native mechanism for exactly this (vig-os/devkit#1227/#1228). The mirror branch bootstraps from main and is never merged back (each run regenerates full state).
