---
type: issue
state: closed
created: 2026-08-07T09:30:56Z
updated: 2026-08-07T10:44:40Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/106
comments: 0
labels: bug, area:workspace, effort:small, semver:patch
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-08T03:28:20.130Z
---

# [Issue 106]: [template/ still references dev after trunk migration](https://github.com/vig-os/org-config/issues/106)

The `template/` skeleton shipped in `v1.0.0` (tag commit `dfc3cda`) still
describes the pre-trunk `dev` model, even though this repo migrated to trunk
`main` (#63). A downstream org that copies the skeleton verbatim gets workflows
that never fire and a runbook that points at a branch that does not exist.

## Occurrences at `v1.0.0`

| File | Line | Reference |
| --- | --- | --- |
| `template/.github/workflows/plan.yml` | `on.pull_request.branches` | `- dev` |
| `template/.github/workflows/apply.yml` | `on.push.branches` | `- dev` |
| `template/.github/workflows/apply.yml` | header | "a `dev`-only deployment-branch policy" |
| `template/.github/workflows/import.yml` | 12 | "commit via a normal PR to `dev`" |
| `template/README.md` | 102 | "Open a PR to `dev`" |
| `template/README.md` | 126 | "deployment-branch policy limited to `dev`" |
| `template/README.md` | 130 | "`otterdog apply` from `dev` on merge" |
| `template/renovate.json` | 5 | `"baseBranchPatterns": ["dev"]` |

The engine's own workflows are already on `main`; only the skeleton lags.

## Impact

Every downstream consumer must hand-adapt. `exo-pet/org-config` did exactly that
twice: once to retarget the plan caller and Renovate base
(exo-pet/org-config#6), and again when wiring the apply caller
(exo-pet/org-config#10). Copying the skeleton unedited yields a `plan` that
never triggers (no PRs target `dev`) and an `apply` that never triggers (nothing
pushes to `dev`) — silent no-ops rather than errors, which is the bad failure
mode for a write-path workflow.

## Suggested fix

Retarget every `dev` reference in `template/` to `main` and cut a `v1.0.1`, so
downstream orgs can pin a skeleton that matches the engine they call.
