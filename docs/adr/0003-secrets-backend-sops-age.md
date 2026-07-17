---
id: adr-0003-secrets-backend-sops-age
type: adr
status: accepted
date: 2026-07-17
owner: carlos.vigo@exoma.ch
tags: [secrets, sops, age, security, bootstrap]
refs: [vig-os/org-config#10, vig-os/org-config#1]
---

# ADR-0003 — Secrets backend: SOPS/age with bootstrap exclusions

- Status: Accepted
- Date: 2026-07-17
- Component / area: `org-config` secrets management
- Reviewers: Carlos Vigo (v1 plan approved in working session 2026-07-17; issue #1 plan comment)

## Context

The Otterdog engine (ADR-0001) manages org and repo configuration declaratively, including GitHub Actions and
Dependabot secrets and variables. Secret *values* must reach the engine at apply time without being committed in
plaintext and without appearing in CI logs.

Two constraints shape the choice:

1. **The config repo is org-admin-equivalent and a supply-chain target** (OWASP CICD-SEC-4). Whatever holds the
   decryption capability is a high-value credential.
2. **This repo is public** (ADR-0006 distribution topology) and dogfoods vig-os's own config. Git history in a public
   repo is permanent and world-readable, so any key that can decrypt committed ciphertext retroactively exposes *every*
   historical value if it leaks.

Reevaluation answer #4 (issue #1) already settled the backend as SOPS/age — "no existing tool does this better." This
ADR records that decision, fixes the bootstrap exclusion, and states the public-repo sizing rule.

## Alternatives considered

Mandatory.

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| SOPS + age | in-repo ciphertext, PR-reviewable; decrypt at apply | one age root key; manual rotation | Chosen |
| Passthrough Actions secrets | native; values never in git | no audit trail; opaque drift; not declarative | Rejected |
| External vault (Vault / cloud SM) | central rotation, ACL, audit | runtime dep + cost; forks can't reach | Rejected |

## Decision

Use **SOPS with age** for all engine-managed secret values.

- **Ciphertext committed in-repo.** `.sops.yaml` creation rules scope which paths and fields encrypt; the encrypted
  files live under version control so every change is a reviewable, diffable PR.
- **Decrypt only at apply.** Values are decrypted in-memory by the apply workflow, masked (`::add-mask::`, no `set -x`
  over secret vars), and **never written to logs**.
- **Rotation via PR + re-apply.** Changing or rotating a value is a normal change: re-encrypt under the new value or
  recipient in a PR, merge, re-apply. No out-of-band mutation.
- **Bootstrap exclusion (by design).** The **GitHub App private key** and the **age private key** are never managed as
  code. They are provisioned out-of-band and held only as CI/environment secrets — never committed, never SOPS-managed.
  Rationale: chicken-and-egg (the App key authenticates the apply and the age key decrypts everything the pipeline
  needs, so neither can be bootstrapped by the pipeline it enables) and blast radius (one poisoned commit must not own
  both authentication and decryption).
- **Public-repo rule.** Keep the SOPS-managed set in this public repo **small and rotatable**, because a leaked age key
  retroactively exposes this world-readable git history. Sensitive-heavy orgs (e.g. `exo-pet`) hold their secrets in
  their own **private** config repos, not here.

## Rationale

- **Auditability is the whole point.** Ciphertext-in-repo yields PR review, blame, and a versioned trail — exactly what
  passthrough Actions secrets and an external vault do not give inside the config-as-code flow.
- **Bootstrap capping.** Excluding the App key and age key from code management keeps recovery possible when the
  pipeline is down and caps the blast radius of any single compromised commit.
- **Permanent public history.** A leaked age key would decrypt every value ever committed to this public repo.
  Minimizing and routinely rotating the managed set bounds the damage; anything truly sensitive lives in a private repo
  whose history is not world-readable.
- **No new runtime.** age needs no server. Forks and break-glass operations decrypt with a local key, honoring the
  "CI stays self-sufficient, forks never depend on shared infra" rule (ADR-0007).

## Consequences

- `.sops.yaml` creation rules and the age recipient list are themselves reviewed config; adding a recipient or an
  encrypted path is a PR.
- The age private key and the App private key become documented, human-gated **bootstrap items** (runbook), rotated on
  personnel change or suspected leak. Rotating the age key requires re-encrypting the entire managed set.
- Pre-commit and CI must guard against committing plaintext (leak scanner / `sops` filter) so an unencrypted value can
  never land in public history.
- Downstream **private** config repos inherit the same pattern but may hold a larger secret set; cross-repo secrets are
  referenced, never copied (SSoT).
- Interacts with ADR-0004 (auth model — App key handling) and ADR-0007 (CI credential rules, masking, least-privilege
  tokens).

## Corrections

None yet. This section preserves assumptions later found wrong, for audit.

## Open questions / supersession triggers

- Manual age-key custody becomes a bottleneck, or an auditor requires hardware-backed keys → revisit toward
  `sops` with a cloud KMS/HSM backend.
- GitHub ships reviewable, diffable, declarative secret management natively → the in-repo-ciphertext rationale weakens;
  reconsider passthrough.
- Managed secret set or org count grows enough that central rotation/ACL/audit outweighs a vault's runtime cost →
  reconsider an external vault.
- Any age-key leak forces immediate rotation of the entire managed set and supersedes the current recipient list.

## References

- vig-os/org-config#10 — this ADR's decision issue
- vig-os/org-config#1 — Secret Management section; reevaluation answer #4; plan comment (public-repo ciphertext caveat)
- ADR-0001 — engine choice (Otterdog); ADR-0004 — auth model; ADR-0006 — distribution topology; ADR-0007 — CI & testing
- SOPS — <https://github.com/getsops/sops>
- age — <https://github.com/FiloSottile/age>
- OWASP CICD-SEC-4 — Poisoned Pipeline Execution
