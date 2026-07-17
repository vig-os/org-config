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

Mandatory. Three independent axes were evaluated.

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
| Config from `dev`; engine to tags | Config live on merge; engine still pinnable | Two cadences | **Chosen** |

### Axis C — mutation-test target

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| `org-config-testbed` repo in `vig-os` | Real API, disposable, declared | No org-level singletons | **Chosen** |
| `vig-os-sandbox` org | Covers org-level apply | Extra org; unneeded for v1 repo scope | Deferred (see triggers) |
| Mutate production settings | Zero setup | Destructive against live governance | Rejected: unacceptable risk |

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
- `apply` is **environment-gated** (required reviewer) and runs only from trunk (`dev`).
- All mutations are **concurrency-serialized** — a reconciler racing itself manufactures phantom drift.

**Split cadence:** config **applies from `dev` on merge**; the engine **releases to `main` + version tags** through the
devkit pipeline for downstream pins (ADR-0006).

**Test pyramid:**

- **L0 — static validation** (fmt/lint/schema/`otterdog validate`): runs on every PR including forks.
- **L1 — unit tests** of the drift layer over **recorded `otterdog plan` fixtures**, TDD; a pure-function core with an
  injected GitHub client so logic is testable without the network. The pinned Otterdog version doubles as
  fixture-format stability.
- **L2 — live read-only `otterdog plan`** against `vig-os` on every same-repo PR: plan is non-mutating, so this is
  free E2E read-path coverage.
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
- Downstream orgs pin the engine by tag/SHA; a breaking workflow change is a tagged release, not a silent `dev` merge.

## Corrections

_None yet._

## Open questions / supersession triggers

- **`vig-os-sandbox` org** is revisited if either trigger fires: (a) an **org-level apply escape** — a need to
  exercise destructive org-singleton changes end-to-end; or (b) a **pre-pilot rehearsal** need before onboarding a
  downstream org.
- A GitHub plan change that enables enforceable org rulesets on Free (removing the plan-only compromise) reopens the
  org-level coverage decision.
- An Otterdog upgrade that breaks the recorded plan-fixture format invalidates the L1 stability assumption and forces
  a fixture refresh (and possibly a pin policy revisit).
- If read-only `plan` ever mutates state, the L2 "free E2E" premise collapses and L2 must move behind the apply gate.

## References

- Issue #1 — plan comment (2026-07-17), section "CI & testing (→ ADR-0007)"; issue #14 (this ADR's decision summary)
- Implementing work: #15 (L0 toolchain), #18 (plan-on-PR), #19 (apply-on-merge), #23 (testbed / L3)
- ADR-0001 (engine), ADR-0002 (drift semantics), ADR-0006 (distribution topology & versioning, #13)
- `.github/workflows/ci.yml` header banner; devkit ADR "conditional container toolchain" (#991, Option A)
- OWASP CI/CD Top 10 — CICD-SEC-4: Poisoned Pipeline Execution
- Otterdog — <https://github.com/eclipse-csi/otterdog>
