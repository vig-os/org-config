---
type: issue
state: open
created: 2026-08-07T16:20:07Z
updated: 2026-08-07T16:20:07Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/120
comments: 0
labels: chore, security, priority:low, area:ci, effort:small, semver:patch
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-08T03:28:17.312Z
---

# [Issue 120]: [Enforce org-wide SHA-pinned actions (sha_pinning_required) once unpinned repos are handled](https://github.com/vig-os/org-config/issues/120)

## Context

From the 2026-08-07 org settings audit (follow-up to #115/#116): `GET /orgs/vig-os/actions/permissions` reports `sha_pinning_required: false` org-wide, while devkit sets it `true` at repo level. Org-wide enforcement would guarantee every workflow in every repo references actions by commit SHA — closing the tag-retargeting supply-chain vector fleet-wide.

## Why not now

Flipping it today would break CI in repos with unpinned action refs:

- `vs-dolt` — upstream fork workflows use version tags (candidate for archival, which also resolves this)
- `tessera` — 4 hand-rolled workflows, unpinned; will be resolved by greenfield devkit adoption (tessera#364)
- `qx`, `nvd-mirror`, `vigos-mvp` — pinning status unaudited

devkit-scaffolded repos (devkit, commit-action, sync-issues-action, devkit-smoke-test, h5v) pin by SHA already via the scaffold.

## Plan

1. Blocked on: vs-dolt disposition (archive or disable Actions) and tessera#364 devkit adoption.
2. Grep remaining repos' workflows for non-SHA `uses:` refs; pin or fix any stragglers.
3. Enable live: the field is **not modeled by otterdog** (no `sha_pinning` field in 1.3.4), so this is a `gh api` change on `/orgs/vig-os/actions/permissions` — record it as an asserted unmanaged control per #116.
4. Once org-level is `true`, the repo-level devkit override becomes redundant but harmless.

## Acceptance

- `gh api orgs/vig-os/actions/permissions --jq .sha_pinning_required` → `true`
- CI green across all active repos after the flip
- Control listed in the #116 drift assertions
