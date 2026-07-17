---
id: adr-0006-distribution-topology-and-versioning
type: adr
status: accepted
date: 2026-07-17
owner: carlos.vigo@exoma.ch
tags: [distribution, versioning, templates, secrets, plan-gating]
refs: [vig-os/org-config#1, vig-os/org-config#13]
---

# ADR-0006 — Distribution topology & versioning

- Status: Accepted
- Date: 2026-07-17
- Component / area: `vig-os/org-config` distribution & release model
- Reviewers: Carlos Vigo (v1 plan approved in working session 2026-07-17; issue #1 plan comment)
- Supersedes / Superseded by: n/a

## Context

ADR-0001 chose Otterdog as the reconciliation engine, whose native model is **one config repo per managed org**. That leaves
two questions this ADR settles: *where does the config per org physically live*, and *how do downstream orgs consume
the reusable engine we build here*.

Four orgs are in scope — `vig-os`, `exo-pet`, `exoma-ch`, `MorePET` — all on the **GitHub Free plan** (verified live
2026-07-06, issue #1). Two constraints dominate the topology:

- **Fork visibility is fixed by GitHub.** A fork of a public repository is always public and cannot be made private; a
  fork also drags the upstream's full commit history with it. Downstream orgs need *private* config repos and do not want
  the engine's history.
- **A config repo is org-admin-equivalent.** Whatever holds Otterdog config plus the App credentials to apply it can rewrite
  org settings — it is a CI/CD supply-chain backdoor (OWASP CICD-SEC-4). On the Free plan a **private** repo has *no
  enforceable* branch protection or rulesets (Free-plan private repos return HTTP 403 on ruleset enforcement; org rulesets
  need Team+). So an unprotectable private config repo holding write credentials is the worst-case blast radius, and the
  sequencing of *when* each org gets write credentials matters as much as *where* the repo lives.

A sub-question: `vig-os`'s own config must live somewhere. Its only private repo is `qms`; everything else is public.
Declaring a private repo by name inside public config is the exposure to weigh against splitting the source of truth.

Full analysis: issue #1 reevaluation (2026-07-06) and implementation-plan (2026-07-17) comments, section "Distribution
topology (→ ADR-0006)".

## Alternatives considered

Mandatory. Distribution topology (full detail in Rationale below):

| Option | Verdict | Reason |
|---|---|---|
| A — fork per org | Rejected | Public forks can't be private; drags engine history |
| B — private repo from template | **Chosen** | Consumes tagged reusable workflows; config + ciphertext + callers |
| C — central multi-org repo | Rejected | Single blast radius; exo-pet QMS audit must stay in-org |

Sub-decision — where `vig-os`'s own config lives (no private sibling):

| Option | Verdict | Reason |
|---|---|---|
| Declare `qms` by name in public config | **Chosen** | Keeps SSoT + full drift sweep; exposes only a repo *name* |
| Private overlay repo (public base + private sibling) | Rejected | Splits the source of truth across two repos |
| Unnamed exclusion (omit `qms` from config) | Rejected | Drift sweep can't tell deliberate omission from real drift |

## Decision

**This repo stays public and is engine + template + `vig-os`'s own config (dogfooding).** It publishes the reusable
workflows, the defaults library, and the strict-drift action, and it manages the `vig-os` org from its own trunk — including
declaring the private `qms` repo by name.

**Each downstream org (`exo-pet`, `exoma-ch`, `MorePET`) gets its own private `org-config` repo created from this template
(GitHub "Use this template"), never a fork.** That repo lives **inside the org it governs** (the PR audit record belongs
where it audits) and holds only: config data, SOPS/age ciphertext, and ~5-line caller workflows that `uses:` this repo's
reusable workflows **pinned to a tag or SHA**.

**Sequencing rule (Free-plan safety).** Because a Free-plan private config repo is unprotectable yet org-admin-equivalent,
an org upgrades to **GitHub Team before its config repo receives write credentials**. Free orgs onboard **read-only**
(plan + drift App permissions) first; write (apply) credentials follow the Team upgrade. Concretely, `exo-pet` upgrades to
Team (#6) before its config repo gets an apply-capable App install.

**Versioning.** `DEVKIT_TAG_PREFIX=v` → releases tag as **`v1.0.0`** (SemVer, devkit convention). **No floating major tags**
(no `v1`); downstream callers pin an **exact tag or SHA** (SHA recommended for `exo-pet`), bumped by **Renovate**.

## Rationale

- Option A is disqualified by a hard GitHub platform rule, not a preference: fork visibility follows the parent and
  cannot be narrowed to private, so a fork can never satisfy the private-config requirement.
- Template instantiation (B) gives each org a private, history-free repo while keeping the engine consumed by an explicit
  version pin — the same "no copied engine code" property a fork gives, without the visibility and history problems,
  and with the audit trail physically inside the governed org.
- Option C concentrates four orgs' admin authority (and `exo-pet`'s medtech audit trail) into one repo; a single compromised
  workflow or reviewer bypass there reaches every org. Per-org repos bound the blast radius to one org and keep each org's
  governance evidence local to it.
- Declaring `qms` by name costs only the visibility of a repo *name* (low sensitivity) while preserving a single source of
  truth and a complete undeclared-repo drift sweep; both alternatives trade that away.
- Pinning exact tags/SHAs (no floating `v1`) makes every engine bump an explicit, reviewable, Renovate-driven change —
  important when the "engine" can rewrite org settings across four orgs.

## Consequences

- This repo carries a dual role: public engine/template **and** live `vig-os` config. CI must keep the credential rules
  of a public repo (plan on same-repo PRs only; environment-gated apply) — see ADR-0007.
- Downstream onboarding is a two-step gate, not one: (1) Team upgrade, then (2) write credentials. Free orgs get useful
  read-only plan/drift coverage in the interim.
- Engine releases and downstream pins are decoupled: a downstream org can stay on an older pinned tag until Renovate proposes
  a bump, so breaking engine changes never silently reach a governed org.
- **Revisit trigger:** if `vig-os` itself accumulates sensitive private repos or webhooks (raising its own blast radius to
  downstream levels), it adopts the same private-config pattern as the other orgs, and this repo drops back to
  **engine + template only** (its config moving to a private sibling). At that point the sub-decision above is re-opened.

## Corrections

<!-- None yet. Preserve here any assumption above later shown wrong, with date and source, for audit. -->

## Open questions / supersession triggers

- GitHub makes forks of public repos privatable, or ships private-repo ruleset enforcement on Free — would re-open
  Option A and the sequencing rule respectively.
- `vig-os` gains sensitive private repos/webhooks — triggers the private-sibling revisit above.
- Otterdog abandons the one-config-repo-per-org model (ADR-0001 engine change) — invalidates the topology's premise.
- A central-review need outweighs blast-radius isolation (e.g. a shared compliance gate across orgs) — would re-weigh
  Option C.

## References

- Issue #1 — implementation plan, section "Distribution topology (→ ADR-0006)":
  <https://github.com/vig-os/org-config/issues/1#issuecomment-5001102649>
- Issue #1 — reevaluation (plan-gating & Free-plan limits):
  <https://github.com/vig-os/org-config/issues/1#issuecomment-4891615046>
- Issue #13 — ADR-0006 decision summary: <https://github.com/vig-os/org-config/issues/13>
- GitHub Docs — Creating a repository from a template:
  <https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template>
- GitHub Docs — About forks (fork visibility follows the parent):
  <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/about-forks>
- GitHub Docs — Reusing workflows (cross-repository / cross-org access to reusable workflows):
  <https://docs.github.com/en/actions/using-workflows/reusing-workflows>
- Eclipse `otterdog-configs` (central multi-org model, rejected as Option C):
  <https://github.com/eclipse-csi/otterdog-configs>
- OWASP CICD-SEC-4 — Poisoned Pipeline Execution:
  <https://owasp.org/www-project-top-10-ci-cd-security-risks/CICD-SEC-04-Poisoned-Pipeline-Execution>
