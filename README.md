# org-config

GitHub organization configuration as code for the [`vig-os`](https://github.com/vig-os)
organization. This repository is the declarative source of truth for org-level
settings, repository configuration, access, and branch rulesets — managed via a
GitOps workflow (plan on pull request, apply on merge, with drift detection).

It is also the **engine** other organizations consume: the plan/apply/drift
workflows are reusable (`workflow_call`), so a downstream org runs its own
governance from a private config repo pinned to a release of this one.

The design and roadmap are tracked in issue
[#1](https://github.com/vig-os/org-config/issues/1); the decisions behind it in
[`docs/adr/`](docs/adr/).

## How it works

Reconciliation is [Otterdog](https://github.com/eclipse-csi/otterdog)
(ADR-0001), pinned to an exact version in `justfile.project` (ADR-0005). The
desired state is the committed jsonnet under `otterdog/vig-os/`, evaluated
against the vendored Eclipse base template in `otterdog/vig-os/vendor/` through
`otterdog/vig-os/house-defaults.libsonnet` — an org-neutral overlay that folds
the house repository merge policy (merge commits only, `PR_TITLE` / `PR_BODY`)
into `newRepo`, so it is declared once here and shipped to every downstream org
in `template/`. Three repo-owned workflows drive it:

| Workflow | Trigger | What it does |
| --- | --- | --- |
| [`plan.yml`](.github/workflows/plan.yml) | pull request touching the config, or manual | Read-only `otterdog plan` against the live org; posts the exact diff as a PR comment. Same-repo PRs only — fork PRs get static checks and never see credentials. |
| [`apply.yml`](.github/workflows/apply.yml) | push to `main` touching the config, or manual | Mutating `otterdog apply`, inside the reviewer-gated `production` environment. |
| [`drift.yml`](.github/workflows/drift.yml) | daily 03:17 UTC, or manual | Read-only plan fed to the in-house drift layer, which reconciles divergence into deduplicated issues; also sweeps the live repo inventory against the declared set. |

All mutating runs share one `otterdog-mutate` concurrency group that never
cancels in progress, so an apply, a drift scan, and the E2E harness can never
race each other into phantom drift (ADR-0007).

### Human gate on every mutation

`apply` runs in the `production` environment, which requires a reviewer and
restricts deployments to `main`. Entering the environment pauses the run, so no
write token touches the live org until a human approves that specific
deployment. `plan` and `drift` never mutate org state.

### Drift is issue-only

Per ADR-0002, drift is **never** auto-reverted. The drift layer
([`src/drift_layer/`](src/drift_layer/)) parses the plan, drops allow-listed
divergence, and reconciles the remainder into `drift`+`critical` issues with a
full lifecycle: open on first sight, **update** (not duplicate) on recurrence,
auto-close once the divergence is gone. The inventory sweep feeds
undeclared/absent repositories into the same lifecycle under an `inventory`
label.

A third leg asserts the controls Otterdog **cannot model** — Actions SHA-pinning,
the fork-PR approval policy, the new-repository security defaults, org-secret
visibility and reader lists. These have no field in its schema, so they appear
in no plan diff: without an assertion they can be flipped in the UI and nothing
notices. [`unmanaged-controls.toml`](unmanaged-controls.toml) declares each one
as an endpoint, a field path and the expected value; findings join the same
lifecycle under an `unmanaged-control` label. The leg degrades **per row** — a
control that cannot be read leaves its own issue untouched rather than being
reported as drift or silently resolved. Check any row against live state without
writing an issue:

```bash
DRIFT_REPOS_TOKEN=... uv run drift-layer --controls-report --org vig-os
```

[`drift-allowlist.toml`](drift-allowlist.toml) holds the two governance
exceptions — `[[expected]]` (known-benign settings divergence) and
`[[unmanaged]]` (repos intentionally outside declarative scope). Both are edited
through the normal PR flow, so "what is tolerated" stays reviewed and versioned.
A control whose live value is knowingly wrong is *not* allow-listed: its row
gets a `tolerated` value instead, so the table keeps recording the desired value
and the row goes green by itself once reality catches up.

### Secrets

Org and repo secret **values** are committed as SOPS/age ciphertext under
[`secrets/`](secrets/) (ADR-0003) and decrypted in memory during apply — never
logged, never written to disk in cleartext. Only the age private key and the
GitHub App credentials are bootstrap secrets held outside the repo.

### Auth

A single GitHub App authenticates every workflow (ADR-0004), with tokens minted
per leg and narrowed where the API allows it — for example, all drift issue
writes run on a token scoped to `issues: write` on this repo alone, never on the
org-admin token. Setup is documented in
[`docs/runbooks/github-app.md`](docs/runbooks/github-app.md).

### Testing

Four layers (ADR-0007): static validation (`just validate` — actionlint, zizmor,
`jsonnetfmt`, `otterdog validate`), unit tests over the drift layer against
recorded plan fixtures, the free read-path E2E that is `plan` on every config
PR, and a weekly destructive E2E
([`testbed-e2e.yml`](.github/workflows/testbed-e2e.yml)) that induces real drift
on the sacrificial `org-config-testbed` repo and asserts the whole issue
lifecycle against the production reconciler.

## Requesting a change

To change any managed org or repository setting (org settings, repo settings,
rulesets/branch protection, teams & permissions, secrets/variables, webhooks),
**do not edit the jsonnet directly** — open a request and let the pipeline apply
it:

1. Open a [**change-request** issue](https://github.com/vig-os/org-config/issues/new?template=change-request.yml)
   describing the target repo(s), the setting area, and the desired end state.
2. A maintainer turns an accepted request into an Otterdog config pull request.
3. The **plan** workflow posts the exact diff as a PR comment — nothing is applied
   yet.
4. On merge to `main`, **apply** runs in the reviewer-gated `production`
   environment, so every mutation pauses for human approval.
5. Scheduled **drift** detection reconciles the committed config against the live
   org and opens an issue for any out-of-band change.

`main` is the single applied-state branch: changes merge straight to it and a
release forks `release/X.Y.Z` from it and merges back.

## Governing another organization

Downstream orgs do **not** fork this repo (ADR-0006). Each org gets its own
**private** `org-config` repo, created from this repo's template, holding only
its config data, its SOPS ciphertext, and thin caller workflows that `uses:` the
reusable workflows here — pinned to an exact release tag or commit SHA, never a
floating major. Renovate proposes the pin bumps.

[`template/`](template/) is that skeleton, and
[`template/README.md`](template/README.md) is the onboarding runbook (create the
private repo, install the App, set the three secrets, import the live org, wire
the callers). The private `exo-pet/org-config` repo is the pilot consumer
([#25](https://github.com/vig-os/org-config/issues/25)).

A **Free-plan** org onboards read-only first: a private repo on Free has no
enforceable branch protection, so `plan` and `drift` are wired immediately and
`apply` waits for the Team upgrade.

## Known limitations

- **Every plan reports one benign change.** `otterdog import` splits
  `javascript-typescript` into two `code_scanning_default_languages` values that
  its own validator rejects, so the committed config keeps the schema-valid
  form and the `vs-dolt` diff never converges
  ([upstream #694](https://github.com/eclipse-csi/otterdog/issues/694)). It is
  allow-listed in `drift-allowlist.toml`, so it raises no drift issue — but a
  clean plan reads `0 add, 1 change, 0 delete`, not all zeros.
- **Rulesets are not machine-writable at the pinned otterdog version.** Any
  ruleset whose required status checks carry a numeric app prefix (`15368:…`)
  fails to apply ([#69](https://github.com/vig-os/org-config/issues/69),
  [upstream #695](https://github.com/eclipse-csi/otterdog/issues/695)). Ruleset
  changes are applied by hand via `gh api` until that is fixed upstream; the
  committed jsonnet stays the source of truth.

## Working in this repo

`just` drives everything; run `just` for the recipe list.

```bash
just validate   # L0: actionlint, zizmor, jsonnetfmt --test, otterdog validate --local
just test       # unit tests over the drift layer
just precommit  # validate + the full pre-commit suite
```

## License

Apache-2.0 — see [`LICENSE`](LICENSE). Downstream config repos created from
[`template/`](template/) are **not** Apache-2.0: they hold org-admin-equivalent
configuration and carry their own proprietary notice.
