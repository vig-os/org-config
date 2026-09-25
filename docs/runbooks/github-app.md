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
- Each org's config repo authenticates its otterdog jobs (`plan`, `apply`, scheduled `drift`) with
  the **full installation token** minted via `actions/create-github-app-token`: GitHub's
  token-narrowing API cannot express the Actions Variables scope otterdog reads, so the App's own
  grant — not a per-job `permissions:` block — is the permission boundary. Per-job narrowing is
  retained **only** for the drift layer's issue operations (ADR-0004).

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
- **Where can this GitHub App be installed?**: **Any account** — public by decision (2026-09-25,
  [#261](https://github.com/vig-os/org-config/issues/261)). This is a deliberate posture with a
  cost, not a default; the reason, the threat model and how to verify the live setting are in
  [Visibility](#visibility) below.

### Permissions

Grant the minimum surface Otterdog needs to read and apply org + repo settings, plus the Issues
write the strict-drift layer uses to open deduplicated `drift` issues. Set every unlisted
permission to **No access**.

| Category     | Permission                | Access       | Why                                               |
| ------------ | ------------------------- | ------------ | ------------------------------------------------- |
| Repository   | Actions                   | Read         | list repo environments (mapped under Actions)     |
| Repository   | Administration            | Read & write | repo settings, security, Actions perms, BPRs, rulesets |
| Repository   | Contents                  | Read         | read committed config (`fetch-config`) — confirmed #16 |
| Repository   | Custom properties         | Read & write | set repo custom-property VALUES (schema is org-level) |
| Repository   | Issues                    | Read & write | strict-drift layer opens / updates `drift` issues |
| Repository   | Metadata                  | Read         | mandatory baseline (auto-selected); never remove  |
| Repository   | Pages                     | Read & write | Pages config (read at plan, write at apply)       |
| Repository   | Secrets                   | Read & write | repo Actions secrets (read names, write at apply) |
| Repository   | Variables                 | Read & write | repo Actions variables — see narrowing gap below  |
| Repository   | Webhooks                  | Read & write | repo webhooks                                     |
| Organization | Administration            | Read & write | org settings, Actions perms, installs, rulesets   |
| Organization | Custom organization roles | Read         | `security_manager` role lookup on every plan      |
| Organization | Custom properties         | Read & write | property schema (read); schema writes need Admin  |
| Organization | Members                   | Read & write | teams + team members; creating a team needs write |
| Organization | Secrets                   | Read & write | org Actions secrets (SOPS/age plaintext at apply) |
| Organization | Variables                 | Read & write | org Actions variables — see narrowing gap below   |
| Organization | Webhooks                  | Read & write | org webhooks                                      |

This is the **verified outcome of the #16 spike** (static enumeration of the otterdog 1.3.4
`import` / `plan --no-web-ui` read path, endpoint→permission mapping per GitHub's
[permissions-required-for-github-apps] reference), replacing the earlier "verify in #16" flags:

- **Repository → Contents (Read)** — confirmed: `fetch-config` reads the committed config via the
  contents API.
- **Organization → Members (Read & write)** — the **read** level was confirmed and widened in scope
  by #16: Otterdog's own read path requires it (teams, team members, and the teams assigned to the
  `security_manager` role), not just the inventory sweep. The **write** level was confirmed by a
  live `apply` on `exo-pet` (2026-09-25, `exo-pet/org-config#81`, run `36119473230`): the first
  downstream org to declare a team got a green plan and then `POST /orgs/{org}/teams` →
  `403 Resource not accessible by integration`, exiting 1 with nothing mutated — a clean failure,
  not a partial one. **Read plans a team; only write creates one.** The same level covers
  `PATCH` / `DELETE /orgs/{org}/teams/{team_slug}`,
  `PUT` / `DELETE /orgs/{org}/teams/{team_slug}/memberships/{user}` and — easy to miss —
  `PUT /orgs/{org}/organization-roles/teams/{team_slug}/{role_id}`, the call that assigns a
  `security_manager` team, which GitHub lists under **Members**, not under Custom organization
  roles. Granted on the App and approved on `exo-pet`'s installation, after which the identical
  dispatch re-ran green (run `36120273830`, #257).
- **Repository → Custom properties (Read & write)** — confirmed by the first live `apply` (run
  `29584038705`, verified 2026-07-17): setting a repo's custom-property **values** (the `type`
  property) 403'd with only the org-level grant. Organization → Custom properties covers the
  property **schema** (definitions); writing a repository's property **value** needs the separate
  repository-level permission. Granted, then the apply re-ran green.
- Write levels are granted **now** so `apply` (#19) needs no second App-settings round-trip. Because
  otterdog jobs run on the **full installation token** (narrowing cannot carry Actions Variables —
  see below), this grant is the permission boundary for **every** otterdog job, `plan` / `drift`
  included; ADR-0004's Corrections log records the full-token decision.
- **Variables narrowing gap (the reason otterdog jobs run un-narrowed):** GitHub's token-narrowing
  schema (`app-permissions` in the create-installation-access-token API) has **no key for Actions
  Variables**, so a *narrowed* token can never carry this permission even though the App grant
  exists — and otterdog's `GET /orgs/{org}/actions/variables` read is **fatal on 403**. The #16
  spike (run 29574758804) confirmed a 14-scope narrowed read token failed at exactly and only that
  endpoint. Otterdog jobs therefore use the **full installation token** and the App grant is their
  boundary; per-job narrowing is reserved for the drift layer's issue operations. The full-token
  decision and the manage-vs-exclude reasoning live in ADR-0004's Corrections log (#16).

**Widening a permission after the App exists is a two-step change, and the second step is per
org.** Editing the App's **Permissions & events** page updates the *App*, not its *installations*:
every existing installation stays on the permission set it last accepted, and its tokens keep
403'ing until an owner of that org approves the new request (GitHub mails the request and surfaces
it on that org's **Settings → GitHub Apps → Configure** page). So a widening lands per org, not
fleet-wide.

**Approve it on the org that needs it, not on every org.** `Read & write` on Members is what the
App *declares*; an installation should take it when that org *declares its first team*, and not
before. An org whose config carries `teams: []` keeps its installation on **Read** as least
privilege — `vig-os` itself does (`otterdog/vig-os/vig-os.jsonnet:55`) — because Members write is
not confined to teams. The same level also grants `PUT /orgs/{org}/memberships/{username}`, which
sets `role` and therefore can promote a member to **admin**, plus
`DELETE /orgs/{org}/members/{username}` and `POST /orgs/{org}/invitations`: inviting, promoting and
removing owners, none of which Organization → Administration write includes. So the App's blast
radius on an org that approves this goes from *can reconfigure the org* to *can change who owns
it*, which is worth paying only where a team is actually declared.
`GET /orgs/{org}/installations` is the cheap confirmation of where it stands: the `permissions`
object it reports per installation, **not** the App's own settings page, is what a token minted for
that org can actually do.

The #16 spike also confirmed the **web-UI-only settings surface**: 12 org settings (in otterdog's
schema marked `"provider": "web"`, e.g. `default_branch_name`, `two_factor_requirement`,
`has_discussions`) are reachable only via browser automation with a human account's
username/password/TOTP — **no App permission covers them**. They are excluded from App-managed
config; details and the manage-vs-exclude decision live in ADR-0004's Corrections log.

If a future change finds another managed setting that an installation token **cannot** reach,
record it in ADR-0004's Corrections log and decide manage-vs-exclude there — do not silently widen
this table.

#### Read path vs apply path

The #16 methodology enumerated otterdog's **read** path, so any permission whose write level is
reached only by `apply` could be recorded one level too low — which is exactly what happened to
Members. Every row above was therefore re-checked against otterdog 1.5.0's
`providers/github/rest/*_client.py` write endpoints, mapped through the
[permissions-required-for-github-apps] reference (#257). **The single Access column stands:** a
GitHub App grant is one level per permission, so that column must always carry the *apply*-path
level, and after the Members fix it does for every resource this fleet declares. Three apply-path
levels are deliberately **not** granted, each because nothing declared today reaches them. Each is
a 403 waiting for the first org that declares its trigger, so they are listed here rather than left
to be rediscovered the way Members was:

- **Organization → Custom properties is granted `Read & write`, but writing the property *schema*
  needs `Admin`.** GitHub lists `PUT` / `DELETE /orgs/{org}/properties/schema/{name}` under the
  **admin** level of that permission; `write` reaches only `PATCH /orgs/{org}/properties/values`.
  Untriggered today because `vig-os`'s single property (`type`) already exists and matches the
  config, so no schema write is ever attempted. The first org to declare a **new** org custom
  property fails exactly as #257 did — raise this row to **Admin** then, and re-approve per install.
- **Repository → Contents is granted `Read`, and renaming a branch needs `write`.** When a repo's
  declared `default_branch` names a branch that does not exist, otterdog does not create it — it
  **renames** the current default via `POST /repos/{org}/{repo}/branches/{branch}/rename`, which
  GitHub lists under repository **Contents (write)** (renaming the *default* branch additionally
  needs Administration write, which is held — Contents is the missing half). Pointing
  `default_branch` at a branch that already exists is a plain `PATCH /repos/{org}/{repo}`
  (Administration) and is unaffected. Not widened pre-emptively because Contents write is push
  access to every file in every repo the installation covers — a large price for a rename.
- **There is no Repository → Environments grant, and environment secrets/variables need one.** The
  environment object itself is `PUT /repos/{org}/{repo}/environments/{name}` (Administration, held)
  and is listed under Actions (Read, held). Its **secrets and variables** are a separate repository
  permission, **Environments**. Otterdog reads or writes them only when the base template defines
  `newEnvSecret` / `newEnvVariable`, and the pinned `otterdog-defaults` `v0.13.1` defines neither,
  so the resource is invisible to `plan` and `apply` alike. That pin is held for an unrelated reason
  (`max_cache_size_gb` answers `402` on a Free plan), so the coupling is accidental: a base-template
  bump that introduces those functions needs **Environments: Read & write** in the same change.

[permissions-required-for-github-apps]: https://docs.github.com/en/rest/authentication/permissions-required-for-github-apps

### Webhooks

**Disabled.** Drift is detected by a **scheduled `otterdog plan`** plus an org-inventory sweep, not
by webhook events. There is deliberately no webhook URL and no webhook secret on this App, on any
org. This is a hard constraint, not an oversight — see the final section.

### Visibility

**Decision (2026-09-25, #261): keep the App public — "Any account" — pending the UI verification
below.** The decision is recorded now; the live value behind it is an API *observation* only
(status code to an anonymous call — see [Verifying the setting](#verifying-the-setting)), so until
that checklist has been walked in the UI, read this as the posture we have chosen and expect to
find, not as a confirmed reading of the form. The downstream-org model is the reason for choosing
it: one App, N installations. *Only on this account* means installable on `vig-os` and nowhere
else, so [Downstream-org installation](#downstream-org-installation) below would have to become one
App per org — N private keys, N rotations, N grant tables held in step — which is precisely the
design ADR-0004 rejected under *"One App, not four"*. `exo-pet` already runs an installation of
this App, and `exoma-ch` / `MorePET` are meant to follow it through the same door. The costs below
are accepted knowingly.

**A flip to private is a four-place edit, not a one-paragraph swap.** The setting has to be stated
where it is set, so if this decision ever changes, all of these move together — treat it as a
checklist rather than archaeology:

1. the creation step at the top of this file, **Where can this GitHub App be installed?**, whose
   value is the setting itself;
2. this Decision paragraph, plus the `CHANGELOG.md` entry, which moves from `### Changed` to
   `### Security` — a flip is a posture event, not a documentation correction;
3. [Downstream-org installation](#downstream-org-installation) step 1, which tells another org's
   owner to install from the public page and says that step is why the App is public — under
   *Only on this account* that whole section has to be rebuilt around one App per org;
4. **Key rotation** step 6, whose `GET /app/installations` sweep exists only because a public App
   can be installed by strangers.

Everything else in this section survives a flip as written: the trade-off below is stated in both
directions, and the verification checklist works for either value.

What the setting controls, per GitHub's [Making a GitHub App public or private][app-visibility]: a
**private** registration "can only be installed on the account that owns the app"; a **public** one
can be installed by "any user on GitHub" and gets a landing page with an **Install** button. Public
is **not** a Marketplace listing — that is a separate opt-in this App has not taken, so discovery
means knowing the slug. Neither value changes what the App may do on an org that has installed it.

**Public gives a stranger nothing and costs us two things.** Installing it grants an App whose
private key only `vig-os` holds; every token is minted from that key
(`actions/create-github-app-token`), so the installer cannot mint one, and the App subscribes to no
events (`"events": []`) and carries no webhook by hard constraint
([What this App must NOT be given](#what-this-app-must-not-be-given)), so nothing of theirs flows
back to us either. The capability runs one way, from the installer to the key holder. What public
does cost:

- **An installation set we neither control nor hear about.** Any account owner can add an
  installation, and with webhooks off there is no `installation` event to receive, so
  `GET /app/installations` (JWT — i.e. the private key) is the only inventory. Sweep it at every
  key rotation. A stray installation is inert while the key is sound; what it widens is the blast
  radius of a *key compromise*, from our orgs to our orgs plus whoever installed it.
- **A world-readable grant table.** `GET /apps/vig-os-org-config` answers `200` to an anonymous
  caller and returns the Client ID and the full `permissions` object,
  `organization_administration: write` included. That is reconnaissance — *this org runs an
  org-admin App whose key sits in some repo's Actions secrets* — not a credential. Treat the Client
  ID as public whatever it happens to be stored as: it is currently held as an Actions secret,
  which hides nothing that this endpoint does not already publish, and whether it stays a secret or
  becomes a variable is [#270](https://github.com/vig-os/org-config/issues/270). The same grant
  table is published by every other public App this org owns, and the one still lacking a decision
  of its own is `vigos-devkit-upgrade`, tracked as
  [#271](https://github.com/vig-os/org-config/issues/271).

**Private would cost the multi-org model instead**, plus one thing that must not be discovered the
hard way: GitHub's documentation does not say whether a public App already installed on accounts it
does not own *can* be made private at all. Until that is established, the flip is not a setting
change to try casually — assume a migration (a new App and a new key per org, cut over, retire the
old one).

**The coupling worth knowing (#256).** An App named as a **ruleset bypass actor** is written by
resolving its slug through `GET /apps/{slug}`, which this engine's installation token is observed
to read only for a public App — so for such an App, visibility is a configuration-relevant setting,
and making it private leaves every ruleset naming it unrepairable by `apply`, with a green plan and
no warning. **This App is not one of those**: neither `otterdog/vig-os/vig-os.jsonnet` nor
`exo-pet`'s config names `vig-os-org-config` as a bypass actor or a status-check app, so its own
visibility is load-bearing only for the installation model above. The Apps for which it *is*
load-bearing are `commit-action-bot` and `vig-os-release-app`, named across ten `vig-os` rulesets;
that is recorded beside the first `bypass_actors+` list in the jsonnet and in
`unmanaged-controls.toml`.

#### Verifying the setting

The API cannot answer this: `GET /apps/{app_slug}` carries **no visibility field**. The only API
signal is the status code returned to an *unauthenticated* caller — `200` for a public App, `404`
for a private one (control, probed the same day: a private App owned by a sibling org answers
`404` anonymous and `200` to an org-owner token). GitHub documents neither that mapping nor the
endpoint's auth requirements, so it is an observation, not a contract — and it is also why **no
`unmanaged-controls.toml` row can assert this**: the controls transport reads authenticated and so
never sees the discriminator.

Check the UI, which is the authority:

1. Go to <https://github.com/organizations/vig-os/settings/apps>.
2. Next to **vig-os-org-config**, click **Edit**.
3. In the left sidebar, click **Advanced**.
4. Read the button under **Danger zone**. It names the *action*, not the state: **Make private**
   means the App is currently **public** — the expected value. **Make public** would mean it is
   private.
5. Click nothing. If what you read contradicts the Decision above, that is drift in the App itself:
   open an issue and reconcile it there, rather than flipping the setting back by hand.

[app-visibility]: https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/making-a-github-app-public-or-private

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

Downstream, otterdog jobs mint the **full installation token** with `actions/create-github-app-token`
(no `permissions:` narrowing): the token-narrowing API cannot express the Actions Variables scope
otterdog reads, so the App grant is the permission boundary for `plan`, `apply`, and `drift`'s
otterdog leg alike (ADR-0004). Per-job narrowing is retained **only** for the drift layer's issue
operations. The stored private key is never handed to a job directly — a short-lived installation
token is always minted per job.

## Running otterdog with the installation token

The engine consumes the installation token through otterdog's **env credential provider**. Two
mechanics, both confirmed by the #16 spike, are load-bearing and easy to miss:

- **`python-dotenv` is an undeclared dependency of the env provider.** Install otterdog with it
  pinned (e.g. `uvx --with python-dotenv==1.1.0 …` in the CI/local invocation); otherwise the env
  provider fails to load before any auth is attempted.
- **`import` resolves *full* web credentials even under `--no-web-ui`.** `import_configuration.py`
  reads `username` / `password` / `twofa_seed` from the env provider regardless of `--no-web-ui`,
  but never exercises them with `-n`. Supply **dummy** values for those three env vars to unblock
  `import` — the App installation token does the actual work. `plan -n` is token-only by
  construction (`diff_operation.py`) and needs no such dummies.

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
6. While you hold the key, sweep `GET /app/installations` (JWT) and confirm every installation is
   one of ours. The App is public, so the set can grow without notice and there is no event to
   catch it ([Visibility](#visibility)); rotation is the one moment this check is free.

## Downstream-org installation

Each downstream org (`exo-pet`, `exoma-ch`, `MorePET`) is governed by its **own private `org-config`
repo created from this template** (not a fork — ADR/issue #1 topology) living **inside that org**.
To bring a downstream org online:

1. As an owner of the target org, open the App's public install page
   (`https://github.com/apps/vig-os-org-config`) and **Install** it on that org, scoped to
   **All repositories**. This step is the whole reason the App is public — see
   [Visibility](#visibility).
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
- **Anything beyond the confirmed least-privilege set** — no Actions **write** (Read is granted only
  for the environments read mapping), no Workflows, Packages, Deployments, or Pull-requests scopes
  unless a future spike proves a concrete need and records it in ADR-0004. The #16 spike is the
  precedent: it widened this table by exactly its enumerated read path, nothing more. Widen only
  through that path, never opportunistically.
- **Repo-transfer or App-management scope** — likewise not App-capable; these remain human owner
  actions and must not be worked around.
