---
type: issue
state: closed
created: 2026-08-17T07:18:54Z
updated: 2026-08-17T08:37:26Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/181
comments: 1
labels: bug, priority:high, area:ci, effort:small
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-18T02:57:52.600Z
---

# [Issue 181]: [Devkit upgrade to 1.10.0 blocked: typos hook rejects the generated mirror-fold comment](https://github.com/vig-os/org-config/issues/181)

## Description

The scheduled `Devkit Upgrade` run for 1.10.0 fails at "Commit the upgrade in
the project shell": the `typos` pre-commit hook rejects the managed
`.github/workflows/release-core.yml` devkit generates for this repo.

```
error: `mis` should be `miss`, `mist`
  .github/workflows/release-core.yml:641:54
  # renames as "R old -> new", both of which mis-parse. The tr has to
```

Run: https://github.com/vig-os/org-config/actions/runs/32002045870

## Cause

Upstream bug — vig-os/devkit#1529. Devkit emits that comment inside the
`DEVKIT_SYNC_TARGET` mirror-fold block (#1424), and the word is only spell-clean
under devkit's own `.typos.toml`, which gained `mis = "mis"` in devkit#1488.
Devkit's seed at `assets/workspace/.typos.toml` gained it too, but `.typos.toml`
is a seeded file that upgrades never overwrite — so this repo, seeded earlier,
never received the entry.

This repo is the only consumer affected: it is the sole repo in the org with a
non-empty `DEVKIT_SYNC_TARGET`, so it is the only one that renders the block.
`commit-action` and `sync-issues-action` adopted 1.10.0 cleanly the same morning.

## Fix here

Add `mis = "mis"` to this repo's `.typos.toml` with a comment pointing at the
devkit render, then re-dispatch the upgrade. Legitimate — `.typos.toml` is this
repo's own file — but it is a workaround for the upstream defect; drop the entry
once devkit#1529 rewords the generated comment and nothing else in the tree
needs it.

Nothing in this repo is misconfigured: the hook firing is the design working.
The upgrade commit is deliberately made inside the project shell so consumer
hooks run, and the hook correctly rejected content that violates this repo's
config.

## Follow-ups upstream

- vig-os/devkit#1529 — generated content must lint under the stock seed
- vig-os/devkit#1530 — a failed upgrade leaves no artifact (no branch/PR/issue)
- vig-os/devkit#1531 — the mirror-fold render path is untested

---

# [Comment #1]() by [c-vigo]()

_Posted on August 17, 2026 at 08:37 AM_

Unblocked. #182 added `mis = "mis"` to this repo's `.typos.toml` (merged as
`d22d108`), and the re-dispatched upgrade then ran clean:
https://github.com/vig-os/org-config/actions/runs/32010644210

Adoption PR is #183 (`chore: adopt devkit 1.10.0`), which carries the actual
version bump — closing this in favour of it.

Confirms the diagnosis end-to-end: the incoming `release-core.yml` still
contains the `mis-parse` comment, and the commit only succeeded because of the
allowlist entry. The workaround is load-bearing until vig-os/devkit#1529
rewords the generated comment; drop the `.typos.toml` entry then, provided
nothing else in the tree needs it.

Upstream: vig-os/devkit#1529 (root cause), #1530 (a failed upgrade leaves no
branch/PR/issue), #1531 (the mirror-fold render path is untested).

