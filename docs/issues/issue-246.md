---
type: issue
state: open
created: 2026-09-24T06:06:23Z
updated: 2026-09-25T17:11:02Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/246
comments: 0
labels: docs, priority:low, area:docs, effort:small, semver:patch
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-26T07:11:56.771Z
---

# [Issue 246]: [Correct the ruleset-internals prose: Otterdog does not model `allowed_merge_methods`, and repo merge settings own the policy until upstream #768](https://github.com/vig-os/org-config/issues/246)

## Summary

Two prose claims in this repo say — or imply — that Otterdog models what is
*inside* a repository ruleset's rules. It does not, and the gap is not
theoretical: an apply silently reverted a hand-set merge-method restriction on
**10 rulesets across 4 repos** on 2026-08-08 and nothing noticed for six weeks.

Otterdog (every version through 1.6.0, the current pin included) does not model
the `allowed_merge_methods` parameter of a ruleset's `pull_request` rule:

- `plan` never diffs it — the field is in no model, so no divergence is visible;
- `apply` PUTs the `pull_request` rule **without** it, and GitHub's
  default-on-omit is *all three methods*, so every apply that touches a ruleset
  silently re-widens it.

Upstream bug filed today: **eclipse-csi/otterdog#768**.

## The incident (2026-08-08)

A routine apply by the org-config App (actor type `Bot`, 2026-08-08 09:34 CEST)
rewrote ten rulesets, each dropping a hand-set `["merge"]` to
`["merge","squash","rebase"]`. Verified row by row against
`GET /repos/vig-os/{repo}/rulesets/{id}/history/{version}`:

| Repo | Ruleset | Version before | Value | Version after | Value |
| --- | --- | --- | --- | --- | --- |
| `commit-action` | Dev protection (18922479) | 43169790 | `["merge"]` | 45947057 | all three |
| `commit-action` | Main protection (11211130) | 43172655 | `["merge"]` | 45947058 | all three |
| `commit-action` | Release protection (18922485) | 43169793 | `["merge"]` | 45947060 | all three |
| `devkit` | Dev protection (13444367) | 43632127 | `["merge"]` | 45947051 | all three |
| `devkit` | Main protection (13444364) | 45871550 | `["merge"]` | 45947052 | all three |
| `devkit` | Release protection (14268611) | 45865257 | `["merge"]` | 45947053 | all three |
| `sync-issues-action` | Dev protection (13401803) | 43216877 | `["merge"]` | 45947054 | all three |
| `sync-issues-action` | Main protection (13401788) | 43216879 | `["merge"]` | 45947055 | all three |
| `sync-issues-action` | Release protection (19011481) | 43212244 | `["merge"]` | 45947056 | all three |
| `org-config` | Main protection (19092020) | 43742326 (User, 2026-07-20) | `["merge"]` | 45947063 | all three |

All ten are still `["merge","squash","rebase"]` live today. `org-config`'s Main
protection is the cleanest single proof: a **human** version carrying
`["merge"]`, the next version a **bot** one carrying all three, with no config
change between them and none since (47302295, 2026-08-22, kept the widened
value).

The irony is recorded in this repo. `docs/pull-requests/pr-117.md:172` and
`docs/pull-requests/pr-119.md:210` both document hand-`PUT`s on **2026-08-07**
that rebuilt each payload from a fresh `GET` specifically so that
`allowed_merge_methods` and every other parameter "passed through verbatim" —
the care was taken, correctly, and the next morning's apply wiped it anyway.

## Decision (2026-09-24)

**Repo merge settings own the merge-method policy.**
`allow_merge_commit` / `allow_squash_merge` / `allow_rebase_merge` **are**
Otterdog-modelled, are declared in `otterdog/vig-os/house-defaults.libsonnet`
(`houseMergePolicy`: merge commits only), and are therefore plan-diffed on every
config PR and drift-guarded daily. All four affected repos sit on that policy by
construction, so merge-only is still enforced where a contributor actually meets
it — the widened ruleset parameter cannot offer a button the repo settings do
not expose.

The ruleset-level `allowed_merge_methods` therefore stays at the platform
default **by decision**, not by neglect, until Otterdog models the field.

Rejected alternatives, and why:

- **Re-narrow the ten rulesets by hand.** Permanent toil: the next apply
  touching any of them re-widens it, with no signal.
- **Add `unmanaged-control` rows asserting `["merge"]`.** The rows would be
  correct and would open an issue every time the engine's own apply re-widened
  the value — self-inflicted drift noise, and the table would be asserting a
  state the tool actively fights. The controls table is for what the engine
  cannot touch, not for re-litigating what the engine overwrites.
- **Both.** A dual source of truth for one policy (repo settings + ruleset
  parameter), with the drift layer refereeing a fight between our own two legs.

Deferred capability, unused today: per-branch merge-method granularity (e.g. a
release branch allowing only merge commits while another branch allows squash).
Nothing in `vig-os` needs it — the policy is uniform per repo.

A neighbouring unmodelled parameter needs **no** action:
`require_extra_approval_for_unattributed_changes` is equally invisible to
Otterdog, but GitHub's default-on-omit is evidently `true` — it reads `true` in
every version above, human and bot alike — which is the value we want. It is
recorded here so the next reader does not re-derive it.

## What is wrong in the tree

1. `unmanaged-controls.toml`, "Repository ruleset internals" section comment:
   says a row would "duplicate a modelled control" because "otterdog models
   rulesets and the plan already diffs them". Over-broad: Otterdog models the
   ruleset **object** (and, on a public repo, diffs the fields it models), not
   every rule parameter inside it. For `allowed_merge_methods` the plan diffs
   nothing at all.
2. `README.md` (~L54-57): the enumeration of "the controls Otterdog **cannot
   model**" lists SHA-pinning, fork-PR approval, new-repo security defaults and
   org-secret visibility/readers, and omits ruleset `pull_request`-rule
   internals.

## Scope

Prose only in the accompanying PR. **No** jsonnet change, **no** ruleset change,
**no** new TOML row — each of those is explicitly the rejected alternative
above.

## Acceptance

- [x] (a) Both prose claims corrected — the TOML section comment states
      precisely what Otterdog models vs. not, the decision, and the exit
      criterion; the README enumeration includes ruleset `pull_request`-rule
      internals (PR #247)
- [x] (b) Upstream bug filed: eclipse-csi/otterdog#768
- [ ] (c) **BLOCKED on upstream.** When the ADR-0005 otterdog pin reaches a
      version in which #768 is fixed, declare `allowed_merge_methods` in the
      jsonnet for the protected-branch rulesets as ordinary config, set to
      each repo's **declared merge policy** — house is merge-only, but
      `h5v`, `nvd-mirror`, `qms`, `qx`, `vigos-mvp` and `vs-dolt` carry
      `orgs.legacyMergePolicy` and `org-config-testbed` carries
      `orgs.upstreamMergePolicy`, so a blanket `["merge"]` would silently
      narrow seven repos — and note it in the changelog. This issue stays
      open as that tracker; the PR for (a) does not close it.

## Context

Related: #205 (list-addressable paths, which made ruleset internals *assertable*
and whose section comment is the one being corrected), #107 /
eclipse-csi/otterdog#729 (private-repo ruleset reads). The `template/` copies of
the affected files carry no equivalent claim to fix, and the affected repos'
`houseMergePolicy` declaration is untouched.


