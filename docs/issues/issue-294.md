---
type: issue
state: open
created: 2026-09-28T12:33:27Z
updated: 2026-09-29T08:51:41Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/294
comments: 4
labels: chore, security, priority:medium, area:workflow, effort:large
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-29T09:51:27.288Z
---

# [Issue 294]: [chore(config): evaluate main protection, merge mechanisms and repo settings across the org](https://github.com/vig-os/org-config/issues/294)

## Context

`vig-os/h5v` just merged a 128-file change rewriting every workflow in the repo
(`vig-os/h5v#7`, the devkit 0.3.1 → 1.17.0 migration) with **no required review
and no required status check**, because `h5v` has no ruleset. It is a public repo
on an org where rulesets are available to public repos, so nothing about that was
a plan limitation — the protection simply was never declared.

That is one repo, but it is not a one-repo problem. The table below is the live
org read on **2026-09-28**, and the declared config in
`otterdog/vig-os/vig-os.jsonnet` matches it: **this is not drift.** Otterdog and
the drift run are doing their job. What is inconsistent is the *policy we
declare*, which has accreted per-repo rather than from a stated rule.

This issue is to decide the rule, not to fix one repo.

## Live state (read 2026-09-28)

Org plan: **free**. 13 public repos, 1 private.

| Repo | Vis | Rulesets | Merge (m/s/r) | del-branch | Secret scanning | Default |
|---|---|---|---|---|---|---|
| `commit-action` | public | 5 | `m/-/-` | yes | enabled | `main` |
| `devkit` | public | 5 | `m/-/-` | yes | enabled | `main` |
| `sync-issues-action` | public | 5 | `m/-/-` | yes | enabled | `main` |
| `devkit-smoke-test` | public | 3 | `m/-/-` | yes | enabled | `main` |
| `org-config` | public | 2 | `m/-/-` | yes | **disabled** | `main` |
| `scitadel` | public | 2 | `-/s/-` | yes | **disabled** | `main` |
| `h5v` | public | **0** | `m/s/r` | **no** | **disabled** | `main` |
| `nvd-mirror` | public | **0** | `m/s/r` | **no** | **disabled** | `main` |
| `qx` | public | **0** | `m/s/r` | **no** | **disabled** | `main` |
| `tessera` | public | **0** | `m/s/r` | **no** | enabled | `dev` |
| `vigos-mvp` | public | **0** | `m/s/r` | **no** | enabled | `main` |
| `vs-dolt` | public | **0** | `m/s/r` | **no** | enabled | `main` |
| `org-config-testbed` | public | 0 | `-/s/r` | yes | — | `main` |
| `qms` | **private** | n/a (403) | `m/s/r` | **no** | n/a | **`worktree-agent-ab0adbce`** |

`web_commit_signoff_required` and Dependabot vulnerability alerts are on
everywhere — those two are already consistent and are not in scope here.

`org-config-testbed` is deliberately on the vendored upstream defaults; treat it
as exempt by construction, not as a gap.

## What the table says

**1. Six public repos have no `main` protection at all** — `h5v`, `nvd-mirror`,
`qx`, `tessera`, `vigos-mvp`, `vs-dolt`. All six are public, so all six *can*
have rulesets on this plan. The four repos that do have them (`commit-action`,
`devkit`, `sync-issues-action`, `devkit-smoke-test`) show the house shape:
Dev/Main/Release protection, Signed commits, Tag protection.

**2. The merge mechanism splits cleanly along the same line.** `houseMergePolicy`
is merge-commit-only (`m/-/-`); every unprotected repo instead allows all three
methods (`m/s/r`) via `orgs.legacyMergePolicy`. So "legacy" is currently doing
double duty as both a merge policy and a de-facto "unprotected" cohort marker.
Worth noting for scoping: per #246, **otterdog does not model ruleset
`allowed_merge_methods`**, so the repo-level fields are the only lever we have
until upstream #768 — the merge decision belongs in `newRepo`, not in the
ruleset.

`scitadel` is a deliberate third shape (`-/s/-`, squash-only, declared inline
rather than via a named mixin). That may be right for a Rust crate; the question
is whether it should be a *named* policy so the intent is legible.

**3. `delete_branch_on_merge: false` is declared on five repos** and correlates
exactly with the unprotected cohort. On `h5v` the merged branch had to be deleted
by hand. Is this deliberate anywhere, or is it legacy inherited alongside the
merge policy?

**4. Secret scanning is disabled on five public repos** — `h5v`, `nvd-mirror`,
`org-config`, `qx`, `scitadel` — and enabled on the other seven. It is free for
public repositories, so there is no cost argument for the split. `org-config`
being one of them is the sharp edge: it is the repo holding SOPS-encrypted
secrets and App credentials.

**5. `qms` needs its own decision, and is arguably broken.** Its default branch
is **`worktree-agent-ab0adbce`** and its only three branches are
`worktree-agent-*` — there is no `main`. Last push 2026-03-25. It is also the
one private repo, so rulesets are genuinely unavailable on Free: for `qms` the
lever is either the classic branch-protection API (also paid on private), making
it public, or accepting it as discipline-only and saying so. A leaked agent
worktree branch serving as the default branch should be fixed regardless of what
we decide about protection.

## Decisions to make

- [x] **State the rule.** Which repos *must* carry `Main protection`, and what
      does it require (approvals, required checks, up-to-date-before-merge,
      linear history)? Candidate: every non-archived public repo that receives
      real changes; testbeds explicitly exempt.
- [x] **Decide the tiering.** Is the current Dev/Main/Release/Signed/Tag set the
      standard for all, or is there a legitimate lighter tier for repos that
      never cut releases (`nvd-mirror`, `vs-dolt`)? Note `devkit-smoke-test`,
      `org-config` and `scitadel` already sit on reduced sets.
- [x] **Decide the merge mechanism per tier**, and whether `legacyMergePolicy`
      should be *retired* as repos are brought up, or kept as a permanent named
      shape. If it is a transitional state, it should say so in
      `house-defaults.libsonnet` and have an exit condition.
- [x] **`delete_branch_on_merge`** — pick one value as the house default and list
      the exceptions with reasons.
- [x] **Secret scanning + push protection** — enable across public repos, or
      record why not. `org-config` first.
- [x] **`qms`** — fix the default branch, then decide: public (and protected),
      or documented as discipline-only. (deferred to #306)
- [x] **Record whatever is decided where it is enforceable**: the house shapes in
      `house-defaults.libsonnet`, per-repo application in `vig-os.jsonnet`, and
      anything otterdog cannot model as a row in `unmanaged-controls.toml` so the
      drift run asserts it instead of trusting it. A decision that lands only in
      prose is the failure mode this repo exists to prevent.

## Notes on scope

The point of the audit is the **rule**, not fourteen individual PRs. Expect the
output to be: a short policy statement (probably an ADR in `docs/adr/`), the
`house-defaults.libsonnet` shapes that encode it, and then the per-repo
application — which can land incrementally, highest-risk repos first.

Two constraints that shape any answer:

- **Free plan.** Rulesets are public-repo-only, and the classic
  branch-protection API is paid on private repos. Any rule that depends on
  protecting a private repo needs a plan decision first. (Note the trap recorded
  elsewhere in our docs: `repos/{org}/{repo}/branches/main/protection` answering
  `404 Branch not protected` does **not** mean unprotected — it is blind to
  rulesets. Check `repos/{org}/{repo}/rulesets`.)
- **Otterdog cannot model ruleset merge methods** (#246), so merge policy stays
  on the repo fields for now.

## Related

- #246 — otterdog does not model `allowed_merge_methods`; repo merge settings own
  the policy until upstream #768. Directly constrains the merge half of this.
- #120 — org-wide `sha_pinning_required` once unpinned repos are handled. Same
  shape of problem: an org-wide control gated on bringing a cohort up first.
- #112 — consolidate GitHub App secrets to client-ID-only. The `h5v` migration
  above removed the last numeric `*_APP_ID` references in that repo.
- Ruleset work already in flight for `tessera` on
  `feature/234-tessera-main-flake-gate` — whatever this issue decides should
  land consistently with it rather than duplicating it.

---

# [Comment #1]() by [c-vigo]()

_Posted on September 28, 2026 at 05:43 PM_

## Audit results (2026-09-28, read-only) and decisions

### Corrections to the issue body

- **`tessera` is protected.** It has otterdog-declared *classic* branch protection on `dev` and `main` (`nix flake check`@15368). Counting rulesets alone missed it, which is the same trap the body warns about, in reverse. So **5 repos are unprotected, not 6.** What tessera lacks is a PR/review requirement, `enforce_admins`, signed commits, and tag protection.
- The #234 tessera work already merged (`b376f2c`). It is classic protection, not a ruleset.
- tessera gets `m/s/r` from inline repo fields, not from `legacyMergePolicy`, so "legacy" and "unprotected" are not the same cohort.
- `delete_branch_on_merge: false` is declared on **7** repos, not 5.
- The org defaults for new repos have secret scanning and push protection on. The 5 disabled repos are explicit jsonnet overrides, and none of them carries a comment. Dependabot security updates are on only in `devkit`.

### Misconfigurations found

- `scitadel`: required checks have `integration_id: null`, so any app or commit status can satisfy them. It does not require its own `CI Summary`, has no Signed or Tag ruleset, and its ruleset names are not house-style.
- Main bypass differs on every repo:
  - `OrganizationAdmin`/`always` on devkit, devkit-smoke-test and org-config
  - `RepositoryAdmin`/`pull_request` on commit-action
  - none on sync-issues-action
  - `enforce_admins=false` on tessera
- commit-action Main duplicates `required_signatures` and lacks `dismisses_stale_reviews`.
- `qx` ships releases (v0.14.2) with no protection. Its only PR check is a matrix job, so it needs an aggregator before any check can be required.
- `nvd-mirror` has no PR workflow and `vigos-mvp` has no workflows. A copied house ruleset would block every merge on both.
- The Signed and Tag rulesets are inlined per repo (5× and 3×). There are no shared helpers.

### Decisions

- **No archiving.** Every repo gets a tier.
- **Main protection:** 1 approval, `#OrganizationAdmin` bypass in `pull_request` mode, `dismisses_stale_reviews`, required `15368:CI Summary`, strict.
  - Repos without an aggregator get the same rule minus the required check until they grow one: nvd-mirror, vigos-mvp, vs-dolt.
- **Merge commit only, no squash or rebase, on every repo.** This includes scitadel and tessera. `legacyMergePolicy` is deleted. The same rule holds for `exo-pet`, which already complies: all 9 repos are `m/-/-`.
- `delete_branch_on_merge` and secret scanning plus push protection go back to the vendored defaults (on). The per-repo overrides are removed.
- `org-config-testbed` stays exempt. It tests the vendored upstream defaults.
- `qms` is out of scope for now.

### Plan (incremental PRs, all `Refs: #294`)

1. Re-enable secret scanning and push protection on h5v, nvd-mirror, org-config, qx and scitadel.
2. ADR-0008 plus ruleset helpers in `house-defaults.libsonnet`, deletion of `legacyMergePolicy`, and conversion of the existing ruleset repos.
3. Tiers for h5v, nvd-mirror, vigos-mvp and vs-dolt.
4. scitadel: pinned checks and `CI Summary`, Signed and Tag rulesets, merge commit only.
5. qx: a `CI Summary` aggregator in qx, then the tier.
6. tessera: rulesets instead of classic protection, merge commit only, default branch back to `main`.


---

# [Comment #2]() by [c-vigo]()

_Posted on September 29, 2026 at 07:13 AM_

## Progress (2026-09-29)

Steps 1–6 of the plan are merged and applied. Live state was read back after each apply.

| PR | What |
|---|---|
| #298 | Secret scanning and push protection re-enabled on h5v, nvd-mirror, org-config, qx and scitadel. |
| #299 | ADR-0008, the house ruleset helpers, and the Main standard on the existing ruleset repos. `legacyMergePolicy` is deleted; that is a template-contract break, so the next engine release is v2.0.0. |
| #300 | Tier rulesets on h5v (A), nvd-mirror, vigos-mvp and vs-dolt (B). h5v's issue sync was moved to `sync/issue-mirror` first (vig-os/h5v#9, #10). |
| #301 | scitadel, qx and tessera moved to tier A. vig-os/qx#311 added qx's `CI Summary` beforehand. |

### Apply notes from #301

The first apply was partial. Two GitHub behaviours caused it; both are worth knowing for future work:

- **Squash settings.** A repo PATCH that disables squash cannot also change `squash_merge_commit_title`/`message`; GitHub answers 422 `no_squash_merge_strategy`. The fix was to set the squash messages to the declared defaults by hand first, then re-apply.
- **Ruleset names are unique case-insensitively.** `Main protection` collided with scitadel's old `main protection`. The old rulesets were renamed to `* (legacy)`, which kept them enforcing, then re-applied, and only then deleted.

The hand deletions otterdog never performs are done:
- scitadel's two legacy rulesets
- tessera's classic branch protection on `dev` and `main`

Rulesets alone now protect both repos.

### Remaining

- [x] Tag and Release rulesets on `devkit-smoke-test`; Tag ruleset on `org-config`. (#302)
- [x] scitadel: fold `rust-ci.yml` (clippy `-D warnings`, macOS tests) into `CI Summary`, so those checks gate merges again. (decided: exit via vig-os/devkit#1761; vig-os/scitadel#227 closed, vig-os/scitadel#239 filed)
- [ ] tessera: add Signed commits once contributors sign. tessera also keeps `dev` as its default branch until `main` carries the devkit scaffold (see the ADR-0008 exceptions). (tracked in #305)
- [ ] Cut v2.0.0.
- [x] Undecided: Dependabot security updates across the org. (decided: tier A only, #304; overlap watch #307)
- [x] Docs: ADR-0002/0006 still say "all orgs on Free", and `docs/runbooks/github-app.md` has stale line references. (#303)
- [ ] `qms`: deferred. (tracked in #306)

---

# [Comment #3]() by [c-vigo]()

_Posted on September 29, 2026 at 08:50 AM_

## Progress (2026-09-29, later)

| PR | What |
|---|---|
| #302 | Tag and Release rulesets on `devkit-smoke-test`, Tag ruleset on `org-config`. Applied: 3 added. |
| #303 | Stale plan claims and line references from this audit corrected (ADR-0002/0006, `docs/runbooks/github-app.md`). |
| #304 | `Release protection` on `org-config`, Dependabot security updates on the tier-A repos. Applied ([run 36544476831](https://github.com/vig-os/org-config/actions/runs/36544476831), success): 1 added, 8 changed. Read back: `org-config` lists Main, Release, Signed and Tag rulesets. |

### Decisions

- `org-config` gets a `Release protection` ruleset (#304).
- Dependabot security updates on tier A only; tier B, the testbed and `qms` stay off (#304, ADR-0008).
- scitadel is not gated on `rust-ci.yml` job names; vig-os/devkit#1761 is the exit for that ADR-0008 row.

### Filed

- vig-os/devkit#1761: feed extra jobs into the managed `CI Summary`.
- vig-os/scitadel#239: dead `contract-tests` job. vig-os/scitadel#227 closed as superseded.
- #305: tessera Signed commits and Tag bypass exceptions.
- #306: `qms` decision.
- #307: Dependabot / Renovate duplicate-PR watch until 2026-10-29.

Remaining: cut v2.0.0, then close.


---

# [Comment #4]() by [c-vigo]()

_Posted on September 29, 2026 at 08:51 AM_

Reopened: closed automatically by the #302 merge through the linked development branch, not by decision. Stays open until v2.0.0 ships (see the progress comment above).

