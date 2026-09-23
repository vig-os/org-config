---
type: issue
state: open
created: 2026-09-23T11:55:43Z
updated: 2026-09-23T12:18:41Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/234
comments: 3
labels: priority:low, change-request
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-23T21:09:32.426Z
---

# [Issue 234]: [[CHANGE-REQUEST] tessera main: update the required status context if tessera changes main's CI](https://github.com/vig-os/org-config/issues/234)

> **Scope note (2026-09-23):** this issue was originally filed proposing changes to tessera's CI. That is tessera's call, not this repo's. Narrowed to the org-config side only: **one field, when a tessera-owned trigger fires.** The implementation plan in the first comment is **superseded** — its tessera steps are out of scope here.

## Target repo(s)

`vig-os/org-config` — `tessera` › `branch_protection_rules` › `main` › `required_status_checks` in `otterdog/vig-os/vig-os.jsonnet`. No tessera changes are proposed or required by this issue.

## Current behavior

`main` requires `CI Summary` (applied 2026-09-23 via #231). Config and live agree — live reads `CI Summary` bound to app `15368`, `strict: true` — and there is no outstanding drift. **Nothing is wrong today and no action is needed now.**

## Why a follow-up exists

`main` and `dev` carry different `ci.yml` files, and a `pull_request` run uses the workflow files from the PR's merge ref (head). So the contexts reported on a PR into `main` depend on where it branched from:

| PR shape | contexts reported on a PR into `main` |
|---|---|
| branched off `main` | `Dependency Review`, `CI Summary` |
| `dev` / `release/*` (promotions) | `nix flake check (x86_64-linux)`, `nix flake check (aarch64-linux)`, `nix flake check` |

The two sets are disjoint — no `CI Summary` job exists anywhere on `dev`; no flake check exists on `main`. So whichever single context this repo declares, one PR shape cannot satisfy it. Today's declaration is the right one for today's live CI, because `main`-origin PRs are the only shape that currently merges at all.

**This repo cannot fix that, and should not try.** Which contexts `main` emits is a tessera decision.

## Desired change — only once triggered

**Trigger:** tessera changes what `main`'s CI emits (most likely by unifying `main`'s `ci.yml` with dev's, which already targets `main`). Whether, when and how tessera does that is entirely theirs to decide.

**Then, here — one field:**

```jsonnet
required_status_checks: [
  'nix flake check',
],
```

Un-prefixed, binding it to the `github-actions` app, matching live `dev` (`app_id: 15368`). Also update the comment block above it (added in #231), which currently explains why `CI Summary` is correct.

**Prefix rule, the org-config-specific knowledge worth keeping** (#226, #231): in a *classic* `branch_protection_rule` otterdog resolves the prefix as an **app slug** via `GET /apps/{slug}` — un-prefixed means `github-actions`, and there is **no numeric branch**. The numeric `15368:` form used elsewhere in this config is **ruleset-only** syntax (`models/ruleset.py`, `elif app_slug.isdigit()`); verified identical in otterdog 1.4.0 and 1.5.0. A `15368:` prefix here 404s at **apply**, past the `production` gate, while `plan` stays green. `tessera` is the only repo in this config still using classic branch protection rules.

Also re-check `requires_strict_status_checks: true` at that point: strict forces a re-run of both arch legs whenever `main` moves, and live `dev` deliberately runs `strict: false`.

## Acceptance criteria

- [ ] Plan shows `0 to add, 1 to change, 0 to delete` — the single `required_status_checks` field.
- [ ] Apply completes green (this is where a wrong prefix form would fail).
- [ ] Live `/repos/vig-os/tessera/branches/main/protection` lists `nix flake check` bound to app `15368`.
- [ ] Next scheduled drift run is clean for `tessera`.

## Urgency

Low, and **blocked on an external trigger** — nothing to do until tessera changes `main`'s CI. Close this if tessera decides to leave `main`'s CI as it is, since the current declaration would then stay correct indefinitely.

## Additional context

History: #226 (diagnosis) → #231 (applied `CI Summary`). A verification draft ([tessera#428](https://github.com/vig-os/tessera/pull/428), closed) established separately that `dev` → `main` currently conflicts on `README.md` and so produces no merge ref and no CI at all — tessera's to resolve if and when they cut the first alpha, noted here only so the blocked-promotion symptom is not mistaken for this issue.

---

# [Comment #1]() by [c-vigo]()

_Posted on September 23, 2026 at 11:56 AM_

## Implementation plan

Two repos, four steps. The ordering is the hard part: the tessera PR that fixes `main`'s CI is itself blocked by the rule that the fix makes correct.

### Step 1 — Confirm the mechanism empirically (cheap, do first)

Everything here rests on *`pull_request` runs workflows from the merge ref, not the base*. Confirm it before changing anything:

- Open a **draft** PR in tessera, head `dev` → base `main`. Do not merge it.
- Read its checks. Expected: `nix flake check (x86_64-linux)`, `nix flake check (aarch64-linux)`, `nix flake check`, and **no** `CI Summary` — i.e. the promotion PR cannot satisfy today's required context.
- Close the draft.

If instead `CI Summary` appears, the premise is wrong, this issue is void, and #231's state is already correct — stop and re-evaluate.

### Step 2 — tessera: give `main` the same CI as `dev`

One PR in `vig-os/tessera`, base `main`: replace `main`'s `.github/workflows/ci.yml` with dev's version (jobs `check` + `gate`; it already lists `main` in `pull_request.branches` and `push.branches`).

Decide explicitly whether `Dependency Review` survives the swap. dev's `ci.yml` drops it, so a straight copy removes dependency scanning from `main` PRs. Options: accept (dev is the tree that matters and `main` only ever receives promotions), or port the `dependency-review` job into dev's `ci.yml` first so both branches keep it. **Recommend porting it into dev** — losing a security check as a side effect of a protection fix is the kind of quiet regression this whole thread is about.

**The ordering trap:** this PR's head branches off `main` but carries the *new* ci.yml, so it reports `nix flake check` and **not** `CI Summary` — the context currently required. It cannot merge cleanly. Two ways through:

- **(a) One deliberate admin merge** (`enforce_admins` is off). Simplest; one documented bypass, recorded on the PR, to retire the bypass permanently. **Recommended.**
- **(b) Temporarily empty `required_status_checks` on `main`** in org-config, apply, merge the tessera PR normally, then set the final value. Avoids the bypass but costs two extra config changes, two applies, and leaves `main` briefly ungated — more moving parts and a wider window than (a).

### Step 3 — org-config: require the real check

Branch `feature/234-…` off `main`. In `otterdog/vig-os/vig-os.jsonnet`, `tessera` › `branch_protection_rules` › `main`:

```jsonnet
required_status_checks: [
  'nix flake check',
],
```

Un-prefixed = bound to the `github-actions` app, matching live `dev` (`app_id: 15368`). Update the comment block above it (added in #231) — it currently explains why `CI Summary` is the right context, which stops being true here. Keep `requires_strict_status_checks: true`; re-check that call once the matrix is in play, since strict forces a re-run of both arch legs whenever `main` moves, and live `dev` deliberately runs `strict: false`.

CHANGELOG `### Changed` bullet, `Refs: #234`, then `just validate && just precommit && just test` before pushing (the full suite locally, not a partial run).

Expected plan on the PR: `0 to add, 1 to change, 0 to delete`, the single `required_status_checks` field. Merge, then approve the `production`-gated apply — this one writes live state, so read its preview.

### Step 4 — Verify against reality

- Live `/branches/main/protection` → `nix flake check`, `app_id: 15368`, `strict: true`.
- Re-open the step 1 draft PR (`dev` → `main`): it should now be mergeable with no override. That is the acceptance criterion that actually matters.
- Confirm the next scheduled drift run is clean for `tessera` (config and live agree, no new issue).

### Sequencing note

Steps 2 and 3 should land in the same session. Between them, `main` requires a context that its own new CI no longer produces — the same broken state, just briefly and knowingly. Do not leave that gap open across days, and do not start the alpha cut inside it.


---

# [Comment #2]() by [c-vigo]()

_Posted on September 23, 2026 at 12:03 PM_

## Step 1 result — inconclusive on its own question, and it found a prerequisite

Ran as written: draft PR [tessera#428](https://github.com/vig-os/tessera/pull/428), head `dev` → base `main`, now closed. No commits added, nothing merged.

**Zero checks appeared — not `nix flake check`, not `CI Summary`, nothing.** The cause is not the workflow files:

- The PR is `CONFLICTING` / `mergeStateStatus: DIRTY`. `README.md` diverged on both sides since merge-base `3463824`: `dev` holds blob `bc9ca37`, `main` holds `cf19d3e` (the landing README from [tessera#383](https://github.com/vig-os/tessera/pull/383), the single commit `main` is ahead by).
- GitHub cannot build a merge ref for a conflicted PR, and `pull_request` workflows run from that merge ref — so **no run was created at all**. tessera's most recent workflow run of any kind predates the PR.

So step 1 neither confirmed nor refuted the head-ref premise. It did surface something the plan missed.

### Consequence 1 — a prerequisite this issue did not account for

The alpha-cut promotion is blocked *before* branch protection enters the picture. Whatever happens with required contexts, `dev` → `main` cannot merge until `main`'s #383 README commit is merged back into `dev` (or the conflict is resolved on the promotion branch). That is a tessera change and it comes first.

It also slightly recasts the urgency argument in the issue body: the promotion path is already blocked today for an unrelated reason, so the required-context defect is not the *only* thing standing between here and the alpha cut.

### Consequence 2 — the verification needs redesigning

A plain `dev` → `main` PR cannot answer the question while the conflict stands. Options, cheapest first:

1. **Do the prerequisite first**, then re-run step 1 exactly as written — the promotion-shaped PR then produces a merge ref and reports real contexts. Slowest, but it tests the thing that actually matters and the prerequisite is needed regardless.
2. **Throwaway branch**: cut from `dev`, merge `main` into it, resolve the README trivially, push to tessera, open a draft PR into `main`, read the contexts, close, delete the branch. Answers the question in minutes; costs one throwaway branch in tessera.
3. **Accept the documented semantics** (`pull_request` runs from the merge ref, so head's workflow files govern) and skip empirical confirmation. Not recommended — the premise being wrong is the one scenario in which this whole issue is void, and the cost of checking is low.

Recommend (1) if the prerequisite is being done soon anyway, (2) otherwise.

### Unchanged

The core finding stands on the file contents alone and does not depend on step 1: dev's `ci.yml` has jobs `check` and `gate` only, both named `nix flake check`, with **no** `CI Summary` job anywhere on `dev`, while `main`'s `ci.yml` emits `Dependency Review` + `CI Summary` and no flake check. Two branches, two disjoint context sets, one required context — which is the defect this issue exists to fix.


---

# [Comment #3]() by [c-vigo]()

_Posted on September 23, 2026 at 12:18 PM_

Superseded by the narrowed issue body above: the tessera steps in the plan comment (unify `main`'s `ci.yml`, port `dependency-review`, reconcile the README) are **out of scope** — how tessera runs its CI is tessera's decision. What remains here is the one-field org-config change, and only once tessera changes what `main` emits. Kept for history, not for execution.

