---
type: issue
state: closed
created: 2026-08-14T07:54:29Z
updated: 2026-08-14T08:11:37Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/169
comments: 0
labels: none
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-14T08:59:20.842Z
---

# [Issue 169]: [Reusable drift workflow is not self-contained: downstream callers lack the drift layer](https://github.com/vig-os/org-config/issues/169)

The reusable `drift.yml` runs `uv run drift-layer` from the **caller's** checkout. A downstream org-config repo (scaffolded from `template/`) contains only config data — no `src/drift_layer/`, no `pyproject.toml`, no `uv.lock` — so the reconcile step cannot run and `template/drift.yml` ships disabled ("keep drift disabled" header). Consequence: no downstream org has drift detection; `drift-allowlist.toml` and `unmanaged-controls.toml` are inert documentation for every consumer.

Fix: make the reusable workflow self-contained. On downstream runs (`github.repository != 'vig-os/org-config'`), add a second SHA-pinned checkout of this public engine repo at `github.job_workflow_sha` — the commit SHA of the called reusable-workflow file, i.e. automatically the exact SHA the caller pins in `uses:` (single pin, no version skew possible) — into a subdirectory, and run the reconcile step via `uv run --project <engine-dir> drift-layer …` with all data paths still resolving in the caller's checkout. Engine own-run semantics stay byte-identical (step skipped). Update `template/drift.yml` to ship enabled, plus docs and changelog.
