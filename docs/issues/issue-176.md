---
type: issue
state: open
created: 2026-08-14T12:25:05Z
updated: 2026-08-14T12:25:05Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/176
comments: 0
labels: none
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-15T02:54:02.803Z
---

# [Issue 176]: [Reusable apply workflow breaks downstream callers: preview job's pull-requests:write exceeds the template caller's grant](https://github.com/vig-os/org-config/issues/176)

Found by exo-pet's first apply dispatch on a ≥v1.1.0 pin (v1.2.1): the run dies with **startup_failure**, zero jobs.

Cause: #105 added the engine-only `preview` job to the reusable `apply.yml`, which nests `./.github/workflows/plan.yml` and therefore declares `permissions: pull-requests: write`. GitHub validates the caller-permission cap at workflow-graph assembly — **before** `if:` evaluation — so even though `preview` is skipped for downstream callers (`if: inputs.org_github_id == ''`), a caller granting only `contents: read` fails at startup. `template/.github/workflows/apply.yml` grants exactly `contents: read`, so every consumer scaffolded from the template is broken from v1.1.0 onward. The engine's own runs are unaffected (its trigger is not `workflow_call`).

Interim (applied in exo-pet): add `pull-requests: write` to the caller's job grant with a comment noting it exists only to satisfy the cap. Proper fix candidates, for the next release:
1. Move `preview` out of the reusable `apply.yml` into an engine-only workflow (it is engine-only by design and never runs via `workflow_call`), restoring the `contents: read` caller contract; or
2. Keep it and update `template/apply.yml` to grant `pull-requests: write` with the explanatory comment.

Option 1 preserves least-privilege for every consumer and keeps the reusable surface honest.
