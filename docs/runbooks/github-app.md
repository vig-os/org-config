# Runbook: org-management GitHub App

Human-executed procedure for creating and installing the single GitHub App that authenticates all
plan / apply / drift automation in this project. Everything below is done by a human org owner
(@c-vigo) in the GitHub web UI and the Actions secrets settings — no step is automated, and this
App is **never** created or configured as code (it is the credential that config-as-code runs on).

Tracks issue #5 (M0). Auth model is recorded in ADR-0004; the secrets rule is ADR-0003.

## Purpose

One GitHub App is the machine identity for the whole fleet:

- **One App**, suggested slug `vig-os-org-config`, **owned by the `vig-os` org**.
- **Installed once per managed org** (`vig-os` first; `exo-pet`, `exoma-ch`, `MorePET` at rollout),
  scoped to **all repositories** on that org.
- Each org's config repo mints **per-job, least-privilege installation tokens** from it via
  `actions/create-github-app-token` — read-only for `plan` and scheduled `drift`, write only in
  `apply` (ADR-0004).

One App owned centrally, installed per org, keeps a single identity and a single key-rotation
surface while the audit trail for each org's changes stays inside that org's own config repo.

## Prerequisites

- You are an **owner** of the `vig-os` org (App creation is owner-only).
- For a downstream install, you are also an owner of that target org.
- `exo-pet` must be on the **Team** plan before its config repo receives *write* credentials
  (issue #6); Free orgs onboard read-only (plan + drift) first.

## Create the App

Go to <https://github.com/organizations/vig-os/settings/apps/new> and fill in:

- **GitHub App name**: `vig-os-org-config` (the public name; the slug derives from it).
- **Homepage URL**: this repository, `https://github.com/vig-os/org-config`.
- **Webhook**: **uncheck "Active"** — this App ingests no events (see
  [What this App must NOT be given](#what-this-app-must-not-be-given)). Leave the webhook URL and
  webhook secret **empty**.
- **Permissions**: set exactly the table below and nothing else.
- **Where can this GitHub App be installed?**: **Only on this account** (`vig-os`-owned; installed
  per org by an owner, not published to the Marketplace).

### Permissions

Grant the minimum surface Otterdog needs to read and apply org + repo settings, plus the Issues
write the strict-drift layer uses to open deduplicated `drift` issues. Set every unlisted
permission to **No access**.

| Category     | Permission     | Access       | Why                                                       |
| ------------ | -------------- | ------------ | --------------------------------------------------------- |
| Repository   | Administration | Read & write | repo settings, branch protection, repo rulesets           |
| Repository   | Contents       | Read         | read config / CODEOWNERS — verify in #16                  |
| Repository   | Issues         | Read & write | strict-drift layer opens / updates `drift` issues         |
| Repository   | Metadata       | Read         | mandatory baseline (auto-selected); never remove          |
| Organization | Administration | Read & write | org settings and org rulesets                             |
| Organization | Members        | Read         | inventory sweep only; membership mgmt deferred — verify in #16 |
| Organization | Secrets        | Read & write | apply org Actions secrets (SOPS/age plaintext at apply)   |
| Organization | Variables      | Read & write | apply org Actions variables                               |

Two rows are marked **verify in #16** — their need is not yet confirmed and the M2 spike
(issue #16, "verify App-token coverage of the Otterdog settings surface") settles them:

- **Repository → Contents (Read)** — expected for reading a repo's config / CODEOWNERS, but whether
  Otterdog's apply path actually requires it (vs. Metadata alone) is unconfirmed.
- **Organization → Members (Read)** — teams / membership management is a v1 non-goal; this is only
  the inventory sweep's undeclared-actor check. Drop it if #16 shows apply does not touch it.

If #16 finds a managed setting that an installation token **cannot** reach, record it in ADR-0004's
Corrections log and decide manage-vs-exclude there — do not silently widen this table.

### Webhooks

**Disabled.** Drift is detected by a **scheduled `otterdog plan`** plus an org-inventory sweep, not
by webhook events. There is deliberately no webhook URL and no webhook secret on this App, on any
org. This is a hard constraint, not an oversight — see the final section.

### Installation

After the App is created:

1. Click **Install App** and install it on **`vig-os`**.
2. Choose **All repositories** (the undeclared-repo sweep must see every repo, including ones not
   yet declared in config).
3. From the App's **General** page, copy the **Client ID** and **generate a private key**
   (**Generate a private key** → downloads a `.pem`). Store both in the bootstrap secrets below,
   then delete the downloaded `.pem` from disk.

## Bootstrap secrets

Store the App credentials as **repository Actions secrets** on the org's config repo (this repo,
`vig-os/org-config`, for `vig-os`):

| Secret name                   | Value                                    |
| ----------------------------- | ---------------------------------------- |
| `ORG_CONFIG_APP_CLIENT_ID`    | the App's Client ID                      |
| `ORG_CONFIG_APP_PRIVATE_KEY`  | the full `.pem` private key, PEM-encoded |

These are **bootstrap secrets and are never managed as code** (ADR-0003): they are the credential
the config-as-code engine runs *on*, so they cannot live inside the config it manages (that would
be a chicken-and-egg loop and would put the org-admin key in a SOPS blob the same key can rewrite).
They are set once, by hand, in the repo's Actions secrets and rotated by hand.

Application secrets and variables that this App *manages* (via Otterdog + SOPS/age) are a separate
concern and do live as code — these two entries do not.

Per-job least privilege is enforced downstream: every workflow job mints its own installation token
with `actions/create-github-app-token`, narrowing `permissions:` to exactly what that job needs —
read-only for `plan` / `drift`, write only for `apply` (ADR-0004). The stored key itself is never
handed to a job at full breadth.

## Key rotation

The private key is the whole App's secret; rotate it on schedule and on any suspected exposure. The
**Client ID does not change** on rotation, so only `ORG_CONFIG_APP_PRIVATE_KEY` is touched.

1. On the App's **General** page → **Private keys** → **Generate a private key**. GitHub keeps the
   old key valid alongside the new one, so there is no outage window.
2. Update `ORG_CONFIG_APP_PRIVATE_KEY` in **every** org config repo where the App is installed
   (start with `vig-os/org-config`; repeat for each downstream org's private `org-config` repo).
3. Trigger a read-only `plan` run in each updated repo and confirm it authenticates.
4. Only after every install is confirmed green, return to the App and **delete the old key**.
5. If rotating due to suspected compromise, delete the old key **immediately** in step 4 and audit
   the App's recent activity.

## Downstream-org installation

Each downstream org (`exo-pet`, `exoma-ch`, `MorePET`) is governed by its **own private `org-config`
repo created from this template** (not a fork — ADR/issue #1 topology) living **inside that org**.
To bring a downstream org online:

1. As an owner of the target org, open the App's public install page
   (`https://github.com/apps/vig-os-org-config`) and **Install** it on that org, scoped to
   **All repositories**.
2. In that org's private `org-config` repo, set the two Actions secrets exactly as above:
   `ORG_CONFIG_APP_CLIENT_ID` and `ORG_CONFIG_APP_PRIVATE_KEY` (same App, so the same Client ID and
   key as `vig-os`).
3. Respect the sequencing rule: a Free-plan private config repo has no enforceable protection yet is
   org-admin-equivalent, so a Free org onboards **read-only (plan + drift) first**; write
   credentials for `apply` wait until that org is on Team (`exo-pet` via issue #6).

No new App is created per org — one App, N installations, N credential copies of the same key.

## What this App must NOT be given

Keep the surface exactly at the table above. In particular, do **not** grant or attach:

- **A webhook or webhook secret** — on any org. Drift is scheduled-plan-driven, so a webhook adds
  no capability and multiplies a shared secret across every org install (webhook-secret sprawl) for
  nothing. Webhooks stay off everywhere.
- **Any billing or plan permission** — this is **not App-capable anyway** (billing, plan upgrades,
  and seat changes are account/owner actions). `exo-pet`'s Team upgrade (#6) is a human billing step,
  never something this App does.
- **Anything beyond the confirmed least-privilege set** — no Actions (workflow) write, no Packages,
  Pages, Deployments, or Pull-requests scopes unless a future spike proves a concrete need and
  records it in ADR-0004. Widen the table only through that path, never opportunistically.
- **Repo-transfer or App-management scope** — likewise not App-capable; these remain human owner
  actions and must not be worked around.
