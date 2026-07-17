---
id: adr-0004-auth-model-github-app
type: adr
status: accepted
date: 2026-07-17
owner: carlos.vigo@exoma.ch
---

# ADR-0004 — Auth model: GitHub App, least-privilege tokens

- Status: Accepted
- Date: 2026-07-17
- Component / area: `org-config` CI automation identity
- Reviewers: Carlos Vigo (v1 plan approved in working session 2026-07-17; issue #1 plan comment)
- Supersedes / Superseded by: —

## Context

The Otterdog engine (`org-config#ADR-0001`) reconciles org and repo settings from CI: it needs an
identity with org-administration scope to run `plan`, `apply`, and scheduled `drift`. That identity is,
by construction, org-admin-equivalent and lives at the end of a pipeline that executes config from a
repository — the OWASP CI/CD poisoned-pipeline surface ([CICD-SEC-4]). The choice of credential therefore
sets both the operational failure modes (does automation break when a person leaves or rotates a token?)
and the security blast radius (what can a compromised job reach?).

Constraints feeding this decision:

- All four managed orgs (`vig-os`, `exo-pet`, `exoma-ch`, `MorePET`) are on GitHub Free (issue #1
  reevaluation, verified live 2026-07-06).
- The engine is driven by our standard workflow style — plan-on-PR comment, apply-on-merge — with
  separate scheduled drift runs (issue #1 plan comment; `org-config#ADR-0007`).
- Issue #1 established that every permission Otterdog requires is App-capable; only repo transfer, App
  installation management, and billing are not.
- The App private key is a bootstrap secret governed by `org-config#ADR-0003` (never managed as code).

Issue #5 tracks the concrete App creation and bootstrap; this ADR governs the model it implements.

## Alternatives considered

Mandatory. Verdicts are relative to the constraints above.

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| GitHub App (1 App, per-org) | Org-scoped; no human dep; auditable | Transfer/install/billing gaps | Chosen |
| Classic PAT | Trivial to mint | Human-owned; over-scoped; leaves with the person | Rejected |
| Fine-grained PAT | Per-repo/perm scoping | Human-owned; 1yr max expiry; manual rotation | Rejected |
| Per-org separate Apps | Hard org isolation | 4x keys/rotation; more bootstrap secrets to leak | Rejected |

## Decision

One GitHub App, **owned by `vig-os` and installed per managed org**, is the sole automation identity for
`plan`, `apply`, and `drift`. Every CI job mints a short-lived installation token via
[`actions/create-github-app-token`] narrowed to exactly the permissions that job needs — **read-only for
`plan` and `drift`, write only in `apply`** — so no long-lived token is ever stored or shared across jobs.
A classic PAT is retained **only** as a documented, audited break-glass credential for the App-incapable
operations (repo transfer, install management, billing) and outages, never as the routine path. The App
private key is a **per-org bootstrap secret** held outside managed config per `org-config#ADR-0003`
(stored as repo Actions secrets `ORG_CONFIG_APP_CLIENT_ID` / `ORG_CONFIG_APP_PRIVATE_KEY`, issue #5).

## Rationale

- **No human-token dependency.** An App identity does not vanish when a person leaves, rotates a personal
  credential, or loses access — the failure mode that makes PATs unfit for governing four orgs.
- **Org-scoped and auditable.** Installation is an explicit, logged per-org event; the App appears as a
  distinct actor in the audit log, and its access is visible and revocable per org without touching the
  others.
- **Least privilege minimizes the CICD-SEC-4 surface.** Per-job tokens scoped down with
  `actions/create-github-app-token` mean a compromised or poisoned `plan`/`drift` job holds a read-only
  token; write capability exists only inside the environment-gated, serialized `apply` job
  (`org-config#ADR-0007`). This bounds the blast radius of the config-repo backdoor that exists regardless
  of engine.
- **One App, not four.** A single shared identity keeps one manifest, one key-rotation runbook, and one
  audit story; per-org Apps would multiply exactly the bootstrap secrets we most want to minimize, for no
  isolation gain that per-org *installations* do not already provide.

## Consequences

- **App-incapable operations stay manual.** Repo transfer, App installation management, and billing/plan
  changes cannot be done with App tokens. These remain human steps — e.g. the App-creation click
  (issue #5) and the exo-pet Team-plan upgrade (issue #6) — and are the sole sanctioned use of the
  break-glass PAT.
- **Bootstrap secret, not code.** The private key is provisioned and rotated out of band per
  `org-config#ADR-0003`; a rotation and downstream-install runbook lives at `docs/runbooks/github-app.md`
  (issue #5).
- **Per-job token wiring is a standing CI requirement.** Every workflow job must mint its own narrowed
  token rather than reuse a broad one; this is a review checkpoint for `plan`/`apply`/`drift` workflows.
- **Coverage assumption carries risk (see Open items).** The model assumes App installation tokens reach
  the entire Otterdog settings surface. The M2 spike (issue #16) must verify this empirically; any setting
  that turns out to need non-App auth is recorded in the Corrections log below with a manage-vs-exclude
  decision, and may narrow what this auth model can govern.

## Open items

> **RESOLVED (issue #16, M2 — run 29574758804):** App-token coverage of the Otterdog settings surface
> was *assumed complete* (issue #1 reevaluation) but unverified. The M2 spike ran `import` + `plan`
> against `vig-os` with an App token only and confirmed App-token-only operation is viable, with one
> structural constraint: installation-token narrowing cannot express Actions Variables, so otterdog
> jobs use the **full** installation token (App grant = boundary). It also found **12 web-UI-only org
> settings** that no App token can reach (excluded from managed config). Both outcomes, plus the
> `import` dummy-credential quirk, are recorded in the **Corrections** log below — the designated
> landing place. No open item remains here.

## Corrections

> **2026-07-17 — spike #16 (definitive run 29574758804):** the Decision above assumed per-job
> least-privilege token **narrowing for all workflows** (read-only `plan` / `drift`, write-only
> `apply`). The spike falsified this for the otterdog jobs. GitHub's installation-token narrowing API
> (`app-permissions` on create-installation-access-token) has **no key for Actions Variables**, while
> otterdog's `GET /orgs/{org}/actions/variables` read is **fatal on 403** — an empirical 14-scope
> narrowed read token failed at exactly and only that endpoint. **Correction:** the otterdog jobs
> (`plan`, `apply`, and the otterdog leg of scheduled `drift`) run on the **full installation
> token**; the App's own grant is the permission boundary, not a per-job `permissions:` block.
> Per-job narrowing survives **only** for the drift layer's issue operations. Two further spike
> facts recorded here: (a) **12 org settings are web-UI-only** (otterdog schema `"provider": "web"`,
> e.g. `default_branch_name`, `two_factor_requirement`, `has_discussions`) — unreachable by any App
> token, hence excluded from managed config; (b) `otterdog import` resolves the **full** web
> credentials even under `--no-web-ui` but never exercises them with `-n`, so supplying **dummy**
> `username` / `password` / `twofa_seed` env values unblocks it (the App token does the actual work;
> `plan -n` is token-only by construction). The auth-model verdict — App-only identity plus
> break-glass PAT — stands unchanged; only the narrowing *granularity* is amended, so status remains
> **Accepted**.

## Supersession triggers

This decision should be re-opened if:

- The issue #16 spike finds settings that App tokens cannot cover, forcing a hybrid (App + credential/PAT)
  auth model rather than App-only-plus-break-glass.
- GitHub removes or materially restricts an App installation-token permission the engine depends on.
- The reconciliation engine changes (supersession of `org-config#ADR-0001`) in a way that mandates a
  different automation identity.
- A move off GitHub Free changes the available auth mechanisms enough to reweigh the alternatives.

## References

- `org-config#1` — issue body *Auth & Self-Protection*; reevaluation (App-capable permissions note;
  CICD-SEC-4 surface minimization); plan comment (per-job least privilege).
- `org-config#5` — create org-management GitHub App and bootstrap credentials (this ADR governs it).
- `org-config#11` — tracking issue for this ADR.
- `org-config#16` — M2 spike: verify App-token coverage of the Otterdog settings surface.
- `org-config#ADR-0001` — reconciliation engine (Otterdog).
- `org-config#ADR-0003` — secrets backend; App private key as a per-org bootstrap secret.
- `org-config#ADR-0007` — CI/testing model; environment-gated, serialized `apply`.
- [`actions/create-github-app-token`] — per-job least-privilege installation tokens.
- OWASP CI/CD Top 10 — [CICD-SEC-4] Poisoned Pipeline Execution.

[`actions/create-github-app-token`]: https://github.com/actions/create-github-app-token
[CICD-SEC-4]: https://owasp.org/www-project-top-10-ci-cd-security-risks/CICD-SEC-04-Poisoned-Pipeline-Execution
