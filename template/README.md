# Downstream org-config onboarding

This is the **downstream skeleton** for governing a GitHub org with
[`vig-os/org-config`](https://github.com/vig-os/org-config) (ADR-0006). Your org
gets its **own private `org-config` repo** that holds only config data, SOPS/age
ciphertext, and thin caller workflows that `uses:` the reusable
`plan`/`apply`/`drift` workflows **pinned to an exact tag or SHA** of the public
engine repo. You never fork the engine and never copy its code.

Everything in this `template/` directory is what your repo's **root** should look
like. During onboarding you copy `template/*` to your repo root and fill in the
placeholders.

## What you are creating

- A **private** `org-config` repo **inside the org it governs** (the PR audit
  trail belongs where it audits). Never a fork — a fork of a public repo is
  always public and drags the engine's history (ADR-0006).
- Caller workflows pinned to a released tag of `vig-os/org-config`; **no floating
  major tags**. SHA-pinning is recommended for medtech orgs (e.g. `exo-pet`).
- Bumps to those pins are proposed by **Renovate** (`renovate.json`).

## Prerequisites

- You are an **owner** of the target org (App install and secrets are
  owner-only).
- You have decided the org's plan. **Free-plan orgs onboard read-only first**
  (see [Free-plan posture](#free-plan-posture-read-only-first)).

## Step 1 — Create the private repo from this template

1. On `vig-os/org-config`, choose **Use this template -> Create a new
   repository**. Make the new repo **private** and create it **inside your org**.
2. In the new repo, move the contents of `template/` to the repo **root** and
   delete everything else the template copied (the engine's `src/`,
   `otterdog/vig-os/`, the engine workflows, ADRs, and so on). Your root should
   end up with: `otterdog.json`, `otterdog/<org>/`, `.github/workflows/`,
   `.github/CODEOWNERS`, `.sops.yaml`, `drift-allowlist.toml`, and
   `renovate.json`.
3. Replace every placeholder: `YOUR_ORG` (this org's GitHub login), `YOUR_ORG_ADMIN`
   (an owner user or team in CODEOWNERS), the `@vX.Y.Z` pins, and the `.sops.yaml`
   age recipient.

## Step 2 — Install the GitHub App

The org is authenticated by the **one** central `vig-os-org-config` GitHub App —
you do **not** create a new App. Follow the **Downstream-org installation**
section of the engine's runbook,
[`docs/runbooks/github-app.md`](https://github.com/vig-os/org-config/blob/main/docs/runbooks/github-app.md):

1. As an org owner, open the App's install page and **install it on this org**,
   scoped to **All repositories**.
2. Respect the sequencing rule: a Free-plan private config repo is
   org-admin-equivalent yet unprotectable, so grant **read-only (plan + drift)**
   permissions first; write (apply) waits for the Team upgrade.

## Step 3 — Set the three secrets

Set these as **repository Actions secrets** on this private `org-config` repo
(same App, so the same Client ID and key as every other install):

| Secret | Value | Needed for |
| --- | --- | --- |
| `ORG_CONFIG_APP_CLIENT_ID` | the App's Client ID | plan, apply, drift |
| `ORG_CONFIG_APP_PRIVATE_KEY` | the App's PEM private key | plan, apply, drift |
| `SOPS_AGE_KEY` | this org's age **private** key | apply only, if you declare secrets |

`SOPS_AGE_KEY` is only needed once you commit `secrets/*.yaml` ciphertext. Its
**public** half goes in `.sops.yaml`; the private half lives **only** here as a
secret and is never committed (ADR-0003).

## Step 4 — Import the org config

1. Bootstrap `otterdog/<org>/<org>.jsonnet` from the live org (see
   [`otterdog/README.md`](otterdog/README.md) for the layout and an
   `otterdog import` starting point), then normalize away base-template defaults
   so the first plan shows an empty diff.
2. Open a PR to `dev`. The **plan** caller runs a read-only
   `otterdog plan` against the live org and posts the diff as a PR comment —
   nothing is applied.

## Free-plan posture (read-only first)

Per ADR-0006, a **Free-plan** org runs **plan-first / read-only**:

- Wire the **plan** caller (`.github/workflows/plan.yml`) immediately — it only
  reads, and gives useful review-time coverage.
- **drift** is also read-only (it opens issues, never touches org state), but its
  reconciler currently needs the shared drift layer present in this repo; until
  that layer ships as a vendored artifact (a `vig-os/org-config` follow-up), keep
  drift disabled and rely on plan.
- Do **not** wire **apply** yet. A Free private repo has no enforceable branch
  protection, so holding write credentials there is the worst-case blast radius.

## After the Team upgrade (enable apply)

Once the org is on **GitHub Team** and the App install is granted write:

1. Create a `production` **environment** in this repo's settings with a
   **required reviewer** and a deployment-branch policy limited to `dev`. The
   reusable apply workflow runs in that environment, so every mutation pauses for
   human approval.
2. Add the **apply** caller (`.github/workflows/apply.yml`). It runs
   `otterdog apply` from `dev` on merge, serialized so mutations never race.

## Keeping the pins current

`renovate.json` enables the `github-actions` manager so Renovate proposes bumps
to the `vig-os/org-config` reusable-workflow pin. Review each bump like any
dependency update — a bump changes the engine that can rewrite this org's
settings. For SHA pins, keep the `# vX.Y.Z` comment beside the digest so the
human-readable version stays visible.
