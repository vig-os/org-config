---
id: adr-0008-repository-protection-and-merge-policy
type: adr
status: accepted
date: 2026-09-28
owner: carlos.vigo@exoma.ch
tags: [rulesets, branch-protection, merge-policy, repo-settings, free-plan]
refs: [vig-os/org-config#294, vig-os/org-config#246, vig-os/org-config#167]
---

# ADR-0008 — Repository protection & merge policy

- Status: Accepted
- Date: 2026-09-28
- Component / area: repository rulesets and merge settings of every repo this engine declares
- Reviewers: Carlos Vigo (decisions recorded on #294, 2026-09-28)
- Trigger conditions: n/a (Accepted)
- Supersedes / Superseded by: n/a

## Context

`vig-os/h5v` merged a 128-file rewrite of every workflow in the repo with no required review and no required status
check, because `h5v` had no ruleset (#294). It is a public repo on an org where rulesets are available to public repos,
so nothing about that was a plan limitation: the protection had simply never been declared.

The read-only audit of 2026-09-28 (#294) found the declared config and the live org in agreement, so this was not
drift. The problem was that the policy we declared had grown repo by repo instead of coming from a stated rule:

- **Five public repos had no protection at all**: `h5v`, `nvd-mirror`, `qx`, `vigos-mvp` and `vs-dolt`. `tessera` has
  classic branch protection on `dev` and `main`, but no PR requirement, no signing and no tag protection.
- **The `Main protection` bypass was different on every repo.** It was `#OrganizationAdmin` in `always` mode on
  `devkit`, `devkit-smoke-test` and `org-config`, `#RepositoryAdmin` in `pull_request` mode on `commit-action`, and
  absent on `sync-issues-action`. `commit-action`'s Main also required signatures a second time on top of its
  `Signed commits` ruleset, and it did not dismiss stale reviews.
- **The merge mechanism followed the same split.** `houseMergePolicy` is merge commits only. The unprotected repos
  used `orgs.legacyMergePolicy` (all three methods), and `scitadel` was squash-only. So "legacy" had come to mark two
  things at once: a merge policy and an unprotected cohort.
- **`delete_branch_on_merge: false`** was declared on seven repos without a comment.
- **Secret scanning was off on five public repos**, `org-config` among them. It was switched back on by the first
  #294 PR.
- The `Signed commits` and `Tag protection` rulesets were copied out in full per repo (five and three times), with no
  shared definition.

Two platform constraints bound any answer:

- **Free plan.** Rulesets can be enforced only on public repositories. Classic branch protection is a paid feature
  on private repositories. Organization rulesets need Team or above, and otterdog's `validate` refuses any org
  ruleset below Enterprise (README, Known limitations). So every rule here is a **per-repository** ruleset and can
  apply only to a **public** repo.
- **Otterdog does not model `allowed_merge_methods`** on a ruleset's `pull_request` rule. `apply` re-sends a ruleset
  without it, so GitHub's default of all three methods comes back on every apply (#246, eclipse-csi/otterdog#768).
  The repo-level `allow_*_merge` fields are modelled, plan-diffed and drift-guarded, so they are the only merge lever
  we have until #768 ships.

## Alternatives considered

Mandatory. Which repos must carry `Main protection`:

| Option | Verdict | Reason |
|---|---|---|
| Every active public repo, in tiers | **Chosen** | No repo that takes changes is left unprotected |
| Only releasing repos | Rejected | `h5v` was releasing and still unprotected; too easy to miss |
| Archive the idle repos instead | Rejected | Owner decision: no archiving, every repo gets a tier |

What `Main protection` requires:

| Option | Verdict | Reason |
|---|---|---|
| 1 approval, stale dismissal, required aggregator, strict, admin `pull_request` bypass | **Chosen** | Review covers what merges; override leaves a PR |
| 0 approvals, required checks only | Rejected as the default | Kept only where a bot flow cannot be approved (Exceptions) |
| Admin bypass in `always` mode | Rejected | It allows direct pushes to `main`, with no PR left behind |
| Copy each repo's CI jobs as required checks | Rejected | One aggregator context per repo; a matrix leg rename cannot block merges |

Merge mechanism:

| Option | Verdict | Reason |
|---|---|---|
| Merge commit only, on every repo | **Chosen** | One history shape across the fleet; PR title and body kept on the merge commit |
| Per-repo named policies (house / legacy / squash) | Rejected | Keeps the accidental split; `legacyMergePolicy` is deleted |
| Declare the policy in the ruleset (`allowed_merge_methods`) | Deferred | Unmodelled by otterdog (#246); apply would re-widen it |

## Decision

### Tiers

| Tier | Who | Rulesets |
|---|---|---|
| **A — releasing** | A public repo that cuts releases and has a CI aggregator | `mainProtection(checks)`, `signedCommits()`, `tagProtection(releaseApp)`; plus `devProtection` / `releaseProtection` where its release train uses `dev` / `release/*` |
| **B — active, no aggregator** | A public repo that takes changes but has no single CI context to require | `mainProtection([])`: the Main standard without required checks, until it grows an aggregator. Plus `signedCommits()` where every writer to the repo already signs; a writer that lands unsigned commits (an upstream it syncs from, a bot on the Actions token) rules it out |
| **Exempt** | `org-config-testbed` | None. It deliberately runs on the vendored upstream defaults (`upstreamMergePolicy`), because that is what it tests |

### The `Main protection` standard

`mainProtection(checks)` in `house-defaults.libsonnet`:

- **1 approving review**, and `dismisses_stale_reviews: true`, so the approval always covers the code that merges.
- **Review threads must be resolved.** **Code-owner review is off**: with a single owner who also authors the PRs,
  that gate can never be met and only ever produces a bypass (#115).
- **Required status checks**: the repo's CI aggregator, in canonical form (`15368:CI Summary`, or the repo's
  existing aggregator, e.g. `devkit`'s `Test Summary` plus its two CodeQL legs). A repo may add a check that no
  aggregator covers (`commit-action` and `sync-issues-action` add `Dist Check`). Checks are **strict**: they must
  have run against an up-to-date branch.
- **Bypass**: `#OrganizationAdmin` in **`pull_request`** mode only. An org owner can merge a PR past the rules, which
  is how the devkit release lane's one-off bootstrap merge works. An org owner can never push to `main` directly.

`devProtection` / `releaseProtection` stay at 0 approvals with their required checks and bot bypass actors. The one
review that counts happens on the release PR into `main`, which is what keeps the release train at a single human
approval (#167, vig-os/devkit#1504, vig-os/devkit#1506).

Signing is a separate `Signed commits` ruleset on `~ALL` with no bypass, and it is never also a flag on `Main
protection`. `Tag protection` makes every tag immutable, and only the release App named as its bypass actor can
create, move or delete one.

### Repository settings

- **Merge commits only, on every repo** (`houseMergePolicy`, folded into `newRepo`), with the PR title and body as the
  merge commit's title and message. This includes `scitadel`, which was squash-only, and `tessera`, which allowed all
  three. The `exo-pet` fleet already complies. **`legacyMergePolicy` is deleted.** `upstreamMergePolicy` stays for the
  exempt testbed.
- **`delete_branch_on_merge`** follows the vendored default (`true`). Per-repo overrides are removed.
- **Secret scanning and push protection** follow the vendored default (`enabled`). Both are free on public repos.
- **Dependabot security updates** are off: every repo follows the vendored default
  (`dependabot_security_updates_enabled: false`), except `qx` (see Exceptions). Vulnerability fix PRs come from
  Renovate, which targets each repo's integration branch. Dependabot alerts stay on everywhere. New repos default to
  off (`new-repo-dependabot-security-updates` in `unmanaged-controls.toml`). **Decided (2026-09-29, #307)**,
  replacing the same-day tier-A opt-in (see Corrections).
- The ruleset shapes carry **no merge policy**, because the repo fields own it (#246). When the ADR-0005 otterdog pin
  reaches a version that fixes eclipse-csi/otterdog#768, `allowed_merge_methods` is declared to match, as `["merge"]`.

### Exceptions

A deviation from the rule above exists only if it is listed here, with its reason, and has a comment next to the
override in `otterdog/vig-os/vig-os.jsonnet`.

| Repo | Deviation | Reason | Exit |
|---|---|---|---|
| `devkit-smoke-test` | Main: **0 approvals** | Its PRs into `main` are bot-authored release-validation PRs merged by devkit's release train. No human reviews them, and vig-os/devkit#1506 removed the approval gate (#167) | Permanent while the repo is bot-only |
| `devkit-smoke-test` | Main: **not strict** | A release PR that is behind `main` stops `promote-release` (`BEHIND`), and no human is present to update the branch in the middle of an automated train | Permanent while the repo is bot-only |
| `devkit-smoke-test` | Main: **review threads not required** | A thread left by any commenter would stall an unattended train. This is the live value, kept | Permanent while the repo is bot-only |
| `qx`, `tessera` | `Tag protection` bypass is `#OrganizationAdmin` (always mode), not a release App | Both release by a maintainer, an org owner, pushing the tag by hand: `qx`'s `release.yml` is tag-triggered, and `tessera`'s release-plz only opens release PRs. No App writes tags there | An App takes over tagging (for `tessera`, `release-plz release` or the devkit train, tessera#441) |
| `nvd-mirror` | `Signed commits` excludes `refs/heads/gh-pages` | `refresh.yml` force-pushes an unsigned orphan commit to `gh-pages` every six hours with the Actions token, and github-actions cannot be a ruleset bypass actor. `gh-pages` holds generated feeds, not source | Permanent while the mirror publishes from a branch |
| `tessera` | No `Signed commits` | Its main contributor pushes unsigned commits (all open PRs, and the alpha promotion on `main`). Under merge-commit only, a signing rule would make those PRs unmergeable | That contributor signs |
| `tessera` | `dev` as default branch | `dev` is still the integration branch after the first alpha: every PR, Dependabot and release-plz target it. Flipping would run the scheduled workflows from `main`'s stale copies | `main` carries the devkit scaffold, or tessera#441 moves it to the devkit train |
| `scitadel` | Main gates only `CI Summary`, not `rust-ci.yml` (known gap, recorded 2026-09-29) | `rust-ci.yml`'s `clippy -D warnings` and macOS test jobs still run but cannot gate a merge: the managed `CI Summary` aggregator cannot include jobs from another workflow. Listing those job names as extra required checks was considered and rejected: a job rename would block every merge, and it would put the repo's CI layout into the org config | vig-os/devkit#1761 gives consumers a way to feed extra jobs into the managed `CI Summary` |
| `qx` | Dependabot security updates on (`dependabot_security_updates_enabled: true`) | No Renovate yet, so Dependabot is its only source of vulnerability fix PRs | `qx` adopts Renovate and it is proven to run |
| `h5v`, `scitadel`, `tessera`, `devkit-smoke-test` | No vulnerability fix PR for some advisories (known gap, recorded 2026-09-29) | Advisories in ecosystems Renovate does not yet cover (Cargo; `uv` for `devkit-smoke-test`) get alerts but no fix PR. Renovate is not yet running on `h5v`, `scitadel` and `tessera` at all: none has ever had a `renovate/*` PR or a Dependency Dashboard | The per-repo Renovate coverage PRs land and Renovate is verified running |
| `org-config-testbed` | Upstream merge defaults, no rulesets | Exempt by construction | n/a |

## Rationale

- **Tiers instead of one shape.** A required check that can never report blocks every merge. `nvd-mirror` has no PR
  workflow and `vigos-mvp` has no workflows at all, so copying the tier-A ruleset onto them would lock them. Tier B
  gives them the review half now and the check half once an aggregator exists.
- **One aggregator context.** Requiring each CI job by name couples the ruleset to job and matrix names. Requiring
  one summary job that fails when any job fails keeps the ruleset stable while CI changes.
- **`pull_request` bypass, not `always`.** Both let an owner get past a stuck gate. Only `pull_request` mode forces
  that to happen as a PR merge, so every override leaves a reviewable PR and a merge commit. Nothing in the fleet
  relies on an owner pushing to `main` directly: every release PR into `main` is App-authored, and the devkit lane's
  bootstrap is a bypass *merge*.
- **Signing in its own ruleset.** A `~ALL` ruleset covers every branch with one rule. Repeating the flag on Main added
  nothing, and on `commit-action` it had become a duplicate that could drift from the real one.
- **Merge commits only.** Every PR is one reviewed unit whose title is already a Conventional Commit subject, and the
  release trains merge with `gh pr merge --merge`. A mixed fleet gains nothing from the other two methods, and each
  one it allows is another history shape to read. Squash in particular discards the per-commit signing and TDD
  history the conventions ask for.
- **Shared constructors.** Five copies of `Signed commits` and three of `Tag protection` differed only by accident,
  as with commit-action's duplicate signature flag. A constructor with the actors and checks as parameters makes the
  intended differences the only ones left.

## Consequences

- `house-defaults.libsonnet` now carries the ruleset shapes (`mainProtection`, `devProtection`,
  `releaseProtection`, `signedCommits`, `tagProtection`) next to the merge policy. It stays org-neutral: bypass
  actors and checks are parameters. `template/otterdog/YOUR_ORG/house-defaults.libsonnet` stays byte-identical.
- Deleting `legacyMergePolicy` is a **breaking change to the template contract** (ADR-0006). A downstream config that
  still names `orgs.legacyMergePolicy` fails to evaluate once it copies the new overlay. It has to restate the five
  fields inline, as `qms` does here, or move to the house policy. `exo-pet`'s config does not use it.
  **Decided (2026-09-28): the copied overlay is part of the SemVer contract, so the next engine release is
  v2.0.0.**
- Turning on 1 approval with stale dismissal on a solo-maintained repo means its owner merges self-authored PRs
  through the `pull_request` bypass. That is the accepted cost, `org-config` included: its `production`
  environment approval gates the apply, and the Main approval gates the merge.
- Contributors lose the squash and rebase buttons on the converged repos, and merged branches are deleted
  automatically.
- A tier-B repo is still not check-gated. That gap is visible in the Exceptions table, not hidden.

## Corrections

<!-- Preserve here any assumption above later shown wrong, with date and source, for audit. -->

- **2026-09-29 — Dependabot security-update PRs do not land "where a required aggregator checks them" (issue
  [#307](https://github.com/vig-os/org-config/issues/307)).** The tier-A opt-in decided earlier the same day (#294,
  #304) read: *"Dependabot alerts are already on everywhere; this only adds the automated fix PRs, and only where a
  required aggregator checks them."* Dependabot security-update PRs always target the default branch, whatever
  `target-branch` says, and on devkit-managed repos they fail the managed `Commit Messages` gate: the `dependabot/*`
  branch name is not allowed, and the titles are not Conventional Commits. vig-os/devkit-smoke-test#433 to #437 and
  vig-os/h5v#11 were all blocked on `Commit Messages` / `CI Summary`. The Repository settings bullet above now
  records the replacement decision: Renovate is the vulnerability-fix channel, and security updates are off except
  on `qx`.
- **2026-09-30 — `qms` is archived, reversing "no archiving" for that one repo (issue
  [#306](https://github.com/vig-os/org-config/issues/306)).** The Tiers table left `qms` **Deferred** pending its own
  decision, and the alternatives above rejected archiving as an owner decision. #306 decided to archive `qms`: it is
  private on a Free-plan org, so no ruleset can be enforced on it, and its content has moved to the destination org's
  controlled-document store, which is on a plan with enforceable rulesets. The migration was verified on 2026-09-30.
  The repository keeps its history read-only. It stays declared in `vig-os.jsonnet` with `archived: true` and its
  frozen live settings, and it is no longer in the Tiers or Exceptions tables. "No archiving" still holds for every
  other repo.

## Open questions / supersession triggers

- **eclipse-csi/otterdog#768 ships** in the ADR-0005 pin: declare `allowed_merge_methods: ['merge']` in the ruleset
  shapes and drop the "repo fields are the only lever" caveat.
- **A GitHub plan change** (Team for `vig-os`, or private-repo rulesets on Free): private repos become protectable and
  org rulesets could replace the per-repo copies. Re-weigh both.
- **devkit changes its release train** so that a human reviews smoke-test PRs, or `promote-release` updates a
  `BEHIND` branch itself: re-decide the `devkit-smoke-test` exceptions.

## References

- #294: audit, decisions and PR plan (<https://github.com/vig-os/org-config/issues/294#issuecomment-5875396772>)
- #246 / eclipse-csi/otterdog#768: `allowed_merge_methods` is unmodelled, so repo fields own the merge policy
- #115, #187: why code-owner review is off. #118, #184: stale-review dismissal. #188: strict plus update-branch
- #167, vig-os/devkit#1504, vig-os/devkit#1506: the single-approval release train
- #147, #148: the admin bypass on `devkit-smoke-test`. #195: `org-config`'s former 0-approval Main, retired by this
  ADR
- ADR-0005 (otterdog pin), ADR-0006 (template contract and versioning), ADR-0007 (Axis D, the `Plan` check stays
  advisory)
- GitHub Docs: About rulesets:
  <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets>
