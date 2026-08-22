---
type: issue
state: closed
created: 2026-08-14T11:46:37Z
updated: 2026-08-14T11:49:16Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/173
comments: 0
labels: none
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-14T12:06:01.337Z
---

# [Issue 173]: [Reusable drift workflow cannot check out a private downstream caller (permissions: {})](https://github.com/vig-os/org-config/issues/173)

Follow-up to #169, found in the first real downstream run (exo-pet/org-config, engine pinned at v1.2.0): the `drift` job declares `permissions: {}`, so `actions/checkout` of the **caller's own repository** fails with `fatal: repository not found` when that repo is private — a zero-scope `GITHUB_TOKEN` cannot read a private repo, and every downstream org-config consumer is private by design (ADR-0006). The engine's own runs never see this because vig-os/org-config is public, which is also why the #169 own-run validation stayed green.

The reusable `plan` and `apply` jobs already grant `contents: read`; `drift` is the odd one out. Fix: job-level `permissions: contents: read` on the drift job — read-only, consistent with the header's "the default checkout is read-only" security model, and it also covers the #169 engine sub-checkout (public, so any valid token reads it).

Validation plan: after merge, exercise the fix from a throwaway branch of exo-pet/org-config pinned to the merge SHA via `workflow_dispatch` BEFORE cutting v1.2.1, so the release ships downstream-verified.
