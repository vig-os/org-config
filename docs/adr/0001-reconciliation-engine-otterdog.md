---
id: adr-0001-reconciliation-engine-otterdog
type: adr
status: accepted
source: internal
date: 2026-07-17
owner: carlos.vigo@exoma.ch
tags:
  - governance
  - org-config
  - reconciliation
  - otterdog
  - iac
refs:
  - vig-os/org-config#1
  - vig-os/org-config#8
---

# ADR-0001 — Reconciliation engine: Otterdog

- Status: Accepted
- Date: 2026-07-17
- Component / area: `org-config` reconciliation engine
- Reviewers: Carlos Vigo (v1 plan approved in working session 2026-07-17; issue #1 implementation-plan comment)
- Supersession triggers: see [Open questions / supersession triggers](#open-questions--supersession-triggers)

## Context

`org-config` must keep the four GitHub organizations (`vig-os`, `exo-pet`, `exoma-ch`, `MorePET`) declaratively
managed: settings, rulesets, secrets, and per-repo configuration live in version control, drift is detected, and every
change flows issue → branch → PR. The original proposal (issue #1) was to **build a full custom Octokit reconciler**
(org + teams + repos + rulesets + secrets, with a diff/plan/apply engine and a drift daemon).

The 2026-07 reevaluation ([issue #1 comment][reeval]) retired two premises that had justified building rather than
adopting:

- **"Terraform needs an external state backend" is stale.** OpenTofu ≥ 1.7 encrypts state/plan client-side (PBKDF2
  passphrase from an Actions secret, encrypted `tfstate` committed in-repo); `terraform-backend-git` adds SOPS/age
  state with branch locking; and `integrations/github` v6.12 closed the custom-property and org-ruleset coverage gaps.
- **The design assumed plan-gating features our orgs cannot buy.** All four orgs are on the GitHub **Free** plan
  (verified live 2026-07-06): private-repo branch protection and rulesets are not enforced, org-level rulesets need
  Team+, and CODEOWNERS/required-reviewers on private repos need Pro/Team/Enterprise. No reconciler fixes a billing
  gate — hence the P0 to upgrade `exo-pet` to Team (issue #6), tracked separately.

With reconciliation itself being a solved problem, the open question became: **which existing stateless engine do we
adopt, and how much do we still build in-house?**

## Alternatives considered

Mandatory. All seven options from the reevaluation, verified against the live orgs and current upstream sources
(2026-07). State/coverage/drift detail is in the [reevaluation comment][reeval]; upstream links are in
[References](#references).

| Option | State model | Verdict |
|---|---|---|
| **Otterdog** (eclipse-csi, v1.3.4) | Stateless; config repo in-org, live API diff | **Chosen** — adopt as engine |
| OpenTofu + `integrations/github` v6.12+ | Encrypted in-repo | **Fallback engine** — misses undeclared repos |
| Safe-Settings (github, v2.1.21) | Stateless (admin repo) | **Rejected** — silent auto-revert; needs hosted Probot |
| ipdxco/github-as-code | Hard-coded AWS S3 + DynamoDB | **Rejected** — no LICENSE (unforkable), 0 releases |
| Peribolos (kubernetes-sigs/prow) | Stateless CLI | **Deferred** — teams/members complement, out of v1 scope |
| Pulumi / Crossplane | DIY backend / k8s | **Rejected** — extra runtime over the same TF provider |
| Custom Octokit reconciler | Stateless (to be built) | **Rejected** — ~8–12k LOC for a solved problem |

Detail behind each verdict — Otterdog's coverage (org/repo settings, rulesets, secrets, variables, environments,
custom properties; production-proven on ~310 Eclipse orgs, EPL-2.0, Python) and its Jsonnet/bus-factor caveats;
OpenTofu's teams/membership reach and `plan -detailed-exitcode`; and the full **adversarial case against the custom
reconciler** (scale, wrong bottleneck, security surface, GitHub absorbing the niche) — is in the
[reevaluation comment][reeval] and is the decisive input here.

## Decision

Adopt **[Otterdog](https://github.com/eclipse-csi/otterdog)** (eclipse-csi) as the reconciliation engine, one config
repo per org (its native model), driven by our standard workflow: plan-on-PR comment, apply-on-merge, GitHub App auth.
Build **only the thin strict-drift layer in-house** — a scheduled `otterdog plan` plus an org-inventory sweep that
opens deduplicated `drift` + `critical` issues and flags undeclared repos. Record **OpenTofu + client-side-encrypted
in-repo state** as the designated fallback engine.

## Rationale

- **The engine is already the target architecture.** Otterdog's config-repo-in-the-managed-org model is exactly the
  forkable, per-org design this issue set out to build — production-proven across ~310 Eclipse Foundation orgs, EPL-2.0
  licensed, and Python (our stack). Adopting it removes ~8–12k LOC of bespoke diff/plan/schema-validation code with no
  in-house precedent.
- **The genuinely unmet requirement is small.** Scheduled drift runs that open deduplicated critical issues and
  undeclared-repo detection are a few-hundred-LOC wrapper around any engine's diff — not a reason to own the engine.
- **App-auth fits.** Every permission the plan/apply/drift flows need is GitHub-App-capable; only repo transfer, App
  installs, and billing are not, and those are human-gated regardless of engine.
- **Owning less code ages better.** GitHub keeps absorbing this niche natively (org rulesets on Team, immutable
  releases GA, required-reviewer ruleset rule GA, Actions execution policies in preview), so a thin wrapper over a
  maintained engine is lower long-term cost than a bespoke reconciler.

## Consequences

- **Bus-factor insurance is mandatory.** Otterdog's low bus factor is the main accepted risk. Mitigations: **pin** the
  engine to an exact tagged version (`uvx otterdog`, Renovate-bumped) so no surprise upgrades, and maintain a
  **mirror-fork** of the upstream repo so the toolchain survives upstream disappearance. CI stays self-sufficient on
  pinned `uvx otterdog` + `gh` so forks and emergencies never depend on the `vig-os/devcontainer` flake.
- **A fallback engine is pre-selected.** If Otterdog misfits or is abandoned, migrate to **OpenTofu +
  `integrations/github` v6.12+** with client-side-encrypted in-repo state — no re-architecture of the config-repo or
  secrets model required. This is a decision, not just an option.
- **In-house scope is bounded to the drift layer.** We build the scheduled `otterdog plan` + inventory sweep →
  deduplicated critical issues, absorbing existing imperative assets (`setup-gh-repo.sh`, `label-taxonomy.toml`,
  `renovate-default.json`) as config inputs, and reusing `sync-issues-action` App-auth + `commit-action` retry. We do
  **not** build a reconciliation engine, a config-schema validator, or an auto-revert daemon.
- **Downstream ADRs are triggered.** Drift semantics (ADR-0002), secrets backend (ADR-0003), auth model (ADR-0004),
  repo tooling (ADR-0005), distribution topology & versioning (ADR-0006), and CI & testing strategy (ADR-0007) each
  refine a facet of this decision and must stay consistent with it.
- **Cross-repo dependency.** The `exo-pet` GitHub Team upgrade (issue #6) is a prerequisite for granting that org's
  config repo write credentials; it is recorded as a decision in `exo-pet/meta` (referenced as `exo-pet/meta#ADR-NNNN`,
  never copied here).

## Corrections

<!-- None yet. Record here, with date and source, any assumption above later found wrong — preserved for audit. -->

## Open questions / supersession triggers

Re-open this decision if any of the following holds:

- **Otterdog is abandoned or its bus factor is realized** (no maintenance, unpatched security issue) — execute the
  OpenTofu fallback.
- **Otterdog stops covering a needed resource type** that the fallback engine covers, and no reasonable wrapper closes
  the gap.
- **GitHub ships native multi-org declarative configuration** that makes a third-party engine redundant.
- **Team/membership management at scale** becomes an in-scope requirement beyond what Otterdog handles — revisit
  Peribolos (deferred) or the OpenTofu engine.

## References

- Decision issue: [vig-os/org-config#8][issue8]
- Full discussion and reevaluation: [vig-os/org-config#1][issue1]
  - Reevaluation comment (options table, adversarial case), 2026-07-06: [permalink][reeval]
  - Implementation-plan comment (v1 definition, milestones), 2026-07-17: [permalink][plan]
- Otterdog (eclipse-csi): <https://github.com/eclipse-csi/otterdog>
- OpenTofu state encryption: <https://opentofu.org/docs/language/state/encryption/>
- `terraform-backend-git`: <https://github.com/plumber-cd/terraform-backend-git>
- `integrations/terraform-provider-github` (v6.12 coverage): <https://github.com/integrations/terraform-provider-github>
- Safe-Settings: <https://github.com/github/safe-settings>
- ipdxco/github-as-code: <https://github.com/ipdxco/github-as-code>
- Peribolos (kubernetes-sigs/prow): <https://docs.prow.k8s.io/docs/components/cli-tools/peribolos/>
- OWASP CICD-SEC-4 (Poisoned Pipeline Execution): <https://owasp.org/www-project-top-10-ci-cd-security-risks/CICD-SEC-04-Poisoned-Pipeline-Execution>
- Org rulesets on GitHub Team (2025-06-16): <https://github.blog/changelog/2025-06-16-organization-rulesets-now-available-for-github-team-plans/>

[issue1]: https://github.com/vig-os/org-config/issues/1
[issue8]: https://github.com/vig-os/org-config/issues/8
[reeval]: https://github.com/vig-os/org-config/issues/1#issuecomment-4891615046
[plan]: https://github.com/vig-os/org-config/issues/1#issuecomment-5001102649
