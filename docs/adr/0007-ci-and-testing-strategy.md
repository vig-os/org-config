---
id: adr-0007-ci-and-testing-strategy
type: adr
status: accepted
date: 2026-07-17
owner: carlos.vigo@exoma.ch
tags: [ci, testing, otterdog, security]
refs: []
---

# ADR-0007 — CI & testing strategy

- Status: Accepted
- Date: 2026-07-17
- Component / area: `org-config` CI, plan/apply/drift workflows, test pyramid
- Reviewers: Carlos Vigo (v1 plan approved in working session 2026-07-17; issue #1 plan comment)
- Trigger conditions: n/a (Accepted)
- Supersedes / Superseded by: n/a

## Context

This repo governs GitHub organizations declaratively: Otterdog is the engine (ADR-0001), drift is issue-only
(ADR-0002), and the repo is public and self-managing (ADR-0006). CI must therefore answer three questions that a
normal app repo does not:

1. **How to add config-specific checks** (`jsonnetfmt`, `actionlint`, `zizmor`, `otterdog validate`) without forking
   the devkit-managed `ci.yml`, which is regenerated on every upgrade and whose local edits are silently lost (see its
   own header banner). The mode-aware managed `ci.yml` runs a fixed `resolve-toolchain → lint → test → commit-checks`
   pipeline and drives everything through `just` recipes.
2. **How to hold org-admin credentials safely on a public repo.** The config repo is an org-admin backdoor regardless
   of engine (OWASP CICD-SEC-4, Poisoned Pipeline Execution). Any fork can open a PR; any workflow that checks out
   PR-head code with write-scoped or `pull_request_target` credentials is a takeover primitive.
3. **How to test a reconciler** whose real output is mutations against a live GitHub org, where a naive E2E run either
   costs nothing (read-only `plan`) or is destructive (`apply`).

The release cadence is also split by nature: governance config changes should go live promptly, whereas the reusable
engine (workflows, defaults library, drift action) is a versioned artifact downstream orgs pin (ADR-0006).

## Alternatives considered

Mandatory. Four independent axes were evaluated (Axis D was decided later, in #236).

### Axis A — where config-specific CI checks live

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Edit managed `ci.yml` | One file; obvious | Overwritten on devkit upgrade; drifts from gold | Rejected: not durable |
| `justfile.project` + flake hooks | Upgrade-safe seam; same in CI and local | Split across two files | **Chosen** |
| Fork the CI pipeline | Full control | Loses devkit maintenance; re-owns mode matrix | Rejected: cost > benefit |

### Axis B — apply cadence

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Apply config from `main` | Single release train | Governance fixes queue behind engine releases | Rejected: too slow |
| Config from trunk; engine to tags | Config live on merge; engine still pinnable | Two cadences | **Chosen** (trunk was `dev`; `main` since #63) |

### Axis C — mutation-test target

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| `org-config-testbed` repo in `vig-os` | Real API, disposable, declared | No org-level singletons | **Chosen** |
| `vig-os-sandbox` org | Covers org-level apply | Extra org; unneeded for v1 repo scope | Deferred (see triggers) |
| Mutate production settings | Zero setup | Destructive against live governance | Rejected: unacceptable risk |

### Axis D — enforcement status of the L2 plan check (added 2026-09-23, #236)

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Advisory check + comment | Plan stays a judgement artifact (ADR-0002); no false gate on runner/auth health | A red plan does not block a merge | **Chosen** |
| Require the check as-is | One-line ruleset change | A path-filtered workflow's check stays `Pending` forever, blocking every non-config PR | Rejected: unavailable |
| Job-level skip shim + static summary job | Requirable — a job skipped by an `if:` conditional reports *Success*, so a broad trigger plus a job-level gate costs ~10 s and no live API call on a non-config PR | Green means three things (clean / skipped / fork PR); needs a paths-filter step, two extra jobs, the templated job name made static, a new ruleset context; propagates to `template/` and every consumer org | Rejected for now (see triggers) |
| Require only where it runs | Would be exactly right | Not expressible in a GitHub ruleset | Rejected: unavailable |
| Fail `plan` on a non-empty diff | A real gate | Inverts ADR-0002 — a diff is a judgement call, not a failure | Rejected |

## Decision

**The devkit-managed `ci.yml` is never edited.** Config-specific validation is added only through the two
upgrade-safe extension points: `justfile.project` recipes (invoked by the managed `lint`/`test` jobs) and
flake-generated pre-commit hooks — `jsonnetfmt`, `actionlint`, `zizmor`, and `otterdog validate`.

**Plan, apply, and drift are separate repo-owned workflows** (not part of managed CI), each with per-job,
least-privilege GitHub App tokens minted for exactly the scope that job needs.

**Public-repo credential rules (binding):**

- `plan` runs only on **same-repo PRs** (`github.event.pull_request.head.repo.full_name == github.repository`); forks
  get L0 static checks only, never plan.
- **Never** use `pull_request_target` with a PR-head checkout (OWASP CICD-SEC-4 / Poisoned Pipeline Execution).
- `apply` is **environment-gated** (required reviewer) and runs only from trunk (`main` since #63 — see the
  2026-09-23 trunk correction below).
- All mutations are **concurrency-serialized** — a reconciler racing itself manufactures phantom drift.

**Split cadence:** config **applies from trunk (`main`) on merge**; the engine **releases as version tags** through
the devkit pipeline for downstream pins (ADR-0006).

**Test pyramid:**

- **L0 — static validation** (fmt/lint/schema/`otterdog validate`): runs on every PR including forks.
- **L1 — unit tests** of the drift layer over **recorded `otterdog plan` fixtures**, TDD; a pure-function core with an
  injected GitHub client so logic is testable without the network. The pinned Otterdog version doubles as
  fixture-format stability.
- **L2 — live read-only `otterdog plan`** against `vig-os` on same-repo PRs that touch the config, the plan workflow,
  or the otterdog pin (`plan.yml`'s `paths:` filter — see the 2026-09-23 correction below): plan is non-mutating, so
  this is free E2E read-path coverage. **L2 is advisory by decision, not by accident (#236, Axis D):** `Plan` is not
  and will not be a required status check — `Main protection` requires exactly one context, `CI Summary`. Three
  facts make enforcement the wrong control rather than merely an unavailable one. First, `plan` exits **0** on a
  non-empty diff — a nonzero exit means invalid config, auth, or a harness failure, never drift — so requiring it
  would gate merges on App-credential and API health, conditions of the runner rather than properties of the PR.
  Second, the config-validity half of that signal is *already* behind the required check: `otterdog validate
  --local` runs as an L0 hook via `just precommit` in the `Lint & Format` job, offline and credential-free, on
  every PR including forks. Third, the diff itself — the thing enforcement is reached for — is explicitly not a
  failure under ADR-0002, and the plan comment says so in as many words. The enforcing control sits at the
  **mutation** boundary instead, where it belongs: the `production` environment reviewer pauses every apply with
  the exact tree's plan in the same run's job summary (#105, #176), backed by a tip-of-branch supersession guard
  (#99). A merge in this repo is not a mutation.
- **L3 — scheduled mutation E2E** on the disposable `org-config-testbed` repo (issue #23); **never per-PR**.
- **Org-level settings** are per-org singletons no dummy repo can cover — v1 accepts **plan-only** coverage there.

## Rationale

Editing `ci.yml` loses the edit on the next upgrade and forfeits the devkit's mode matrix; the recipe + hook seam is
the maintainer-sanctioned extension point and gives identical local/CI behavior. The same-repo guard plus the ban on
`pull_request_target`-with-checkout closes the standard public-repo PPE takeover path while still letting a fork's PR
receive useful static feedback. Least-privilege per-job tokens and environment-gated, serialized apply bound the blast
radius of the org-admin credential the repo unavoidably holds. The plan/apply cadence split reflects that governance
fixes are urgent while the engine is a pinned dependency. The pyramid maximizes free signal (L0 forks, L1 fixtures, L2
read-only live plan) and confines the one expensive/destructive layer (L3) to a sacrificial repo on a schedule.

## Consequences

- Reviewers must reject any PR that patches `ci.yml` for project logic; the fix always lands in `justfile.project` or
  a hook.
- New checks are added as recipes/hooks and thereby run in every mode and on developer machines, not just in CI.
- The drift layer must be written as a pure core with an injected client, and plan fixtures committed, before behavior
  is trusted (implementation: issues #15 L0, #18 plan-on-PR, #19 apply-on-merge, #23 testbed/L3).
- Org-level configuration changes ship with plan-only assurance until a sandbox org exists; treat org-singleton apply
  as a manual, reviewed operation.
- Downstream orgs pin the engine by tag/SHA; a breaking workflow change is a tagged release, not a silent trunk
  merge.
- A PR proposing an unintended live diff **can merge on green CI**, and this is accepted (#236): the diff is visible
  in the plan comment, the drift run would raise it as a `drift`+`critical` issue (ADR-0002), and nothing reaches
  the live org until a human approves the `production` deployment with that same plan in front of them. The blast
  radius of merging a bad config is a commit, not an applied org.
- `Main protection` deliberately gains **no** second required context. `org-config` is solo-maintained with an
  unconditional `#OrganizationAdmin` bypass and `required_approving_review_count: 0`; a gate the only maintainer
  routinely clicks past is the #115 / #167 / #195 / #226 pathology this repo has repeatedly removed.
- The Axis D decision propagates downstream unchanged: `template/`'s plan caller keeps its `paths:` filter, and a
  consumer org wires no plan context into its ruleset. On a private consumer below Enterprise, where environment
  required reviewers return HTTP 422, the human gate is the `workflow_dispatch` that runs apply (template Mode B) —
  a different mechanism for the same property: no mutation without a human who has read a plan.

## Corrections

Entries are added here only if an assumption above is later found wrong, preserved verbatim for audit:

> **2026-09-23 (#235):** the L2 bullet above claimed the live read-only plan runs *"against `vig-os` on every
> same-repo PR"*. It never has. `plan.yml` carried a `pull_request` `paths:` filter in its very first commit
> (`f101cc6`, 2026-07-17 — the day this ADR was accepted), so L2 fires only on a same-repo PR into `main` that
> touches `otterdog.json`, `otterdog/**`, `.github/workflows/plan.yml` or — since #230 — `justfile.project`, which
> holds the ADR-0005 `otterdog_version` pin the workflow greps at run time. A PR that changes the engine, the
> tests, the docs or the release train gets no plan at all, by design: a plan is a live-API round trip against the
> org on a full App installation token (ADR-0004 Corrections), and running one on a README typo diffs the same
> committed config against the same live org for no new signal. The filter is why L2 is cheap, not an oversight —
> but it is a real coverage boundary, and #230 is what a wrong boundary costs: #229's pure pin bump touched no
> config path, so the empty plan that was its acceptance evidence had to be produced by hand (`workflow_dispatch`
> run 35844030809). The same harness also runs on `workflow_dispatch` and, via `workflow_call`, as
> `apply-engine.yml`'s pre-approval preview on a trunk push (#105) — neither is per-PR coverage. Corrected above.
>
> Unaffected: the binding credential rule in the Decision — plan runs **only** on same-repo PRs — is an upper bound
> on who may reach the App token, never a promise that every such PR is planned, and L3's "never per-PR" stands.
> `README.md`'s testing summary already said "`plan` on every config PR" and needs no change.

> **2026-09-23 (#237):** four statements above still described the pre-#63 branch topology, where `dev` was the
> trunk and `main` a separate release branch. The binding credential rule said apply *"runs only from trunk
> (`dev`)"*, the split cadence said config *"applies from `dev` on merge"* while the engine *"releases to `main` +
> version tags"*, Axis B's chosen option read *"Config from `dev`; engine to tags"*, and a Consequences bullet
> contrasted a tagged release with *"a silent `dev` merge"*. #63 retired `dev`: `main` is the single trunk and
> applied-state branch (PRs target it, `apply-engine.yml` runs on pushes to it), and the engine releases as
> version tags cut by the devkit release train, not by promotion to a separate branch. The decisions themselves
> survive unchanged — apply is still trunk-only and environment-gated, and the split cadence
> (config-on-merge vs engine-by-tag) is intact; only the branch names were stale. The credential-rule staleness is
> the one that mattered: a reader auditing where the write token can run was told a branch that no longer exists.
> Corrected above.

## Open questions / supersession triggers

- **`vig-os-sandbox` org** is revisited if either trigger fires: (a) an **org-level apply escape** — a need to
  exercise destructive org-singleton changes end-to-end; or (b) a **pre-pilot rehearsal** need before onboarding a
  downstream org.
- A GitHub plan change that enables enforceable org rulesets on Free (removing the plan-only compromise) reopens the
  org-level coverage decision.
- An Otterdog upgrade that breaks the recorded plan-fixture format invalidates the L1 stability assumption and forces
  a fixture refresh (and possibly a pin policy revisit).
- If read-only `plan` ever mutates state, the L2 "free E2E" premise collapses and L2 must move behind the apply gate.
- **The Axis D "stay advisory" verdict (#236) has three revisit triggers.** (a) A merged-but-unintended config
  change that the `production` approval failed to catch would promote the skip-shim from rejected to scheduled —
  as of #236 there is no such incident, and `plan.yml` has never once concluded `failure` (57 runs). (b) A
  multi-maintainer `org-config` removes the "always-bypassed gate" objection: with a second reviewer, the merge
  boundary becomes a real checkpoint and a required `Plan` becomes worth its cost. (c) GitHub making a required
  check conditional on the paths a PR touches would make "require only where it runs" real, free of the
  skip-shim's green-means-three-things defect; adopt it if it ships. Adopting the skip-shim supersedes the L2
  trigger set above and the 2026-09-23 correction that records it; both must be re-stated, not quietly left
  behind.

## References

- Issue #1 — plan comment (2026-07-17), section "CI & testing (→ ADR-0007)"; issue #14 (this ADR's decision summary)
- Implementing work: #15 (L0 toolchain), #18 (plan-on-PR), #19 (apply-on-merge), #23 (testbed / L3)
- ADR-0001 (engine), ADR-0002 (drift semantics), ADR-0006 (distribution topology & versioning, #13)
- `.github/workflows/ci.yml` header banner; devkit ADR "conditional container toolchain" (#991, Option A)
- OWASP CI/CD Top 10 — CICD-SEC-4: Poisoned Pipeline Execution
- Otterdog — <https://github.com/eclipse-csi/otterdog>
