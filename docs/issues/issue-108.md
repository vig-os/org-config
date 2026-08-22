---
type: issue
state: closed
created: 2026-08-07T10:37:26Z
updated: 2026-08-07T10:48:27Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/108
comments: 1
labels: refactor, priority:medium, area:workspace, effort:medium, semver:patch
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-08T03:28:19.231Z
---

# [Issue 108]: [House repo defaults: single-source the merge policy across engine and downstream](https://github.com/vig-os/org-config/issues/108)

The house repository merge policy — merge commits only, with `PR_TITLE` /
`PR_BODY` as the merge-commit title/message — has no single source. It is
hand-copied onto individual repo blocks in `otterdog/vig-os/vig-os.jsonnet`
(`allow_merge_commit: true` appears 12 times, the full five-field policy five
times), and the vendored Eclipse base
(`otterdog/vig-os/vendor/otterdog-defaults/otterdog-defaults.libsonnet`) declares
the exact opposite (`allow_rebase_merge`/`allow_squash_merge` true,
`allow_merge_commit` false, `merge_commit_title: 'MERGE_MESSAGE'`).

Consequences:

- Every newly declared repo starts on the *upstream* policy and silently keeps
  it unless someone remembers to paste the five lines.
- Downstream org configs (`exo-pet/org-config`) import the vendored defaults
  directly and repeat the overrides inconsistently, so the policy is neither
  discoverable nor enforceable fleet-wide.
- The current file already shows the drift this causes: five repos carry the
  full policy, six carry only `allow_merge_commit: true` (so rebase and squash
  stay enabled), and three are on yet other combinations.

## Proposed fix

Add a small, org-neutral overlay libsonnet next to the org entry point that
imports the vendored Eclipse defaults and re-exports them with `newRepo`
overridden to apply the house merge policy, plus named mixins for the repos that
deliberately stay on another policy. Org configs then import the overlay instead
of the vendor path — one line — and every repo declared afterwards inherits the
house policy by construction. The overlay is a single file that can be dropped
next to a downstream org's own `vendor/` tree, so `exo-pet` and future orgs get
the same behavior without vendoring the engine.

`otterdog/vig-os/vig-os.jsonnet` is then deduplicated against the overlay. This
must be a **pure refactor**: the evaluated config has to be byte-identical before
and after, so repos that currently deviate from the house policy keep their
current effective settings (aligning them is a live change and belongs to a
separate issue).

## Also in scope

The same change ships the downstream skeleton refresh tracked in #106: the
overlay has to be part of `template/`, and the skeleton's onboarding runbook is
the place that tells a downstream which file to copy and which import line to
write. Doing both in one pass keeps `template/` consistent and lets a single
`v1.0.1` carry them.

## Acceptance

- Overlay file exists and evaluates in both layouts (engine config dir and a
  downstream `otterdog/<org>/` dir with its own vendored defaults).
- `otterdog/vig-os/vig-os.jsonnet` imports the overlay; redundant per-repo merge
  fields removed.
- `jsonnet otterdog/vig-os/vig-os.jsonnet` output identical before and after.
- `otterdog plan` unchanged (the standing `vs-dolt` artifact only).
- `template/` ships the overlay and documents the two-step downstream adoption.

---

# [Comment #1]() by [c-vigo]()

_Posted on August 7, 2026 at 10:48 AM_

Delivered in PR #109 (merge `5aa117ec48d5718996eeb0ecaed324532877f6e6`) and released as
[`v1.0.1`](https://github.com/vig-os/org-config/releases/tag/v1.0.1).

## What shipped

| | |
| --- | --- |
| Overlay | `otterdog/vig-os/house-defaults.libsonnet` |
| Downstream copy | `template/otterdog/YOUR_ORG/house-defaults.libsonnet` (verbatim) |
| Engine config | `otterdog/vig-os/vig-os.jsonnet` now `import 'house-defaults.libsonnet'` |
| Release | `v1.0.1`, tag object `560da12053c27debcbe040dc04d602d044f504a5` on commit `b07dc31b76540ae3c703fbb799920b7274aa3b8e` |

The overlay re-exports the vendored Eclipse base template with the house merge
policy (`allow_merge_commit: true`, rebase/squash off, `merge_commit_title:
'PR_TITLE'`, `merge_commit_message: 'PR_BODY'`) folded into `newRepo`, plus three
named mixins — `houseMergePolicy`, `upstreamMergePolicy`, `legacyMergePolicy` —
so a repo that deliberately sits on another policy names it instead of restating
five fields. It imports `vendor/…` relative to itself and names no org, so the
same file works in this repo and beside a downstream org's own vendored tree.

## Acceptance evidence

- **Pure refactor, verified.** `jsonnet otterdog/vig-os/vig-os.jsonnet` captured
  before and after: byte-identical (1799 lines, `diff` clean).
- **Plan unchanged.** The PR's plan run
  ([31171181361](https://github.com/vig-os/org-config/actions/runs/31171181361))
  reported `Plan: 0 to add, 1 to change, 0 to delete` — the standing benign
  `vs-dolt` `code_scanning_default_languages` artifact only.
- **Downstream layout verified.** The overlay was evaluated in a simulated
  `otterdog/exo-pet/` tree (its own `vendor/`, no engine files) — the relative
  import and both mixins resolve.
- **Declared set unchanged.** Every `orgs.newRepo('<name>')` literal is preserved,
  which is what the inventory sweep's extraction is anchored on; `just test` green
  (43 passed) with `tests/conftest.py::DECLARED_REPOS` untouched.
- `just precommit` green, including `otterdog validate --local` (0 errors).

## Deliberately out of scope

Keeping the eval byte-identical means six repos that predate the policy (`h5v`,
`nvd-mirror`, `qms`, `qx`, `vigos-mvp`, `vs-dolt`) carry an explicit
`+ orgs.legacyMergePolicy`, `org-config-testbed` carries
`+ orgs.upstreamMergePolicy`, and `scitadel`/`tessera` keep their now-commented
deviations. **Narrowing any of those to the house policy is a live settings
change** (it removes merge buttons contributors may be using) and belongs to a
separate, deliberate issue — the overlay makes that debt visible rather than
silently fixing it.

## Downstream adoption (two steps)

1. Copy `otterdog/vig-os/house-defaults.libsonnet` verbatim to
   `otterdog/<org>/house-defaults.libsonnet`, beside the existing `<org>.jsonnet`
   and `vendor/` tree. Do not edit it.
2. In `<org>.jsonnet`, change
   `local orgs = import 'vendor/otterdog-defaults/otterdog-defaults.libsonnet';`
   to `local orgs = import 'house-defaults.libsonnet';`, drop each repo's now
   redundant house merge fields, and add `+ orgs.legacyMergePolicy` (or
   `+ orgs.upstreamMergePolicy`) to any repo not on the house policy so its plan
   stays empty.

#106 is closed by the same PR: the eight `dev` references in `template/` are
retargeted to `main` and the example engine pins bumped to `v1.0.1`, so `v1.0.1`
is the first tag whose skeleton matches the engine it calls — the tag downstream
orgs (`exo-pet/org-config`) should re-pin to.

