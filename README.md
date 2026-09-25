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
| [`apply.yml`](.github/workflows/apply.yml) | push to `main` touching the config, or manual — via [`apply-engine.yml`](.github/workflows/apply-engine.yml) | Mutating `otterdog apply`, inside the reviewer-gated `production` environment. `workflow_call`-only: it has no triggers of its own and a single `contents: read` job, so a consumer needs nothing beyond that grant. `apply-engine.yml` is this repo's own trigger for it and runs the pre-approval plan preview in the same run, next to the approval prompt. |
| [`drift.yml`](.github/workflows/drift.yml) | daily 03:17 UTC, or manual | Read-only plan fed to the in-house drift layer, which reconciles divergence into deduplicated issues; also sweeps the live repo inventory against the declared set. |

All mutating runs share one `otterdog-mutate` concurrency group that never
cancels in progress, so an apply, a drift scan, and the E2E harness can never
race each other into phantom drift (ADR-0007).

### Human gate on every mutation

`apply` runs in the `production` environment, which requires a reviewer and
restricts deployments to `main`. Entering the environment pauses the run, so no
write token touches the live org until a human approves that specific
deployment. `plan` and `drift` never mutate org state.

### The plan report also checks declared App slugs

Otterdog's read and write paths resolve a GitHub App differently, so one class of
config is green in the diff and red on apply. `apply` writes every App-shaped
actor — ruleset `bypass_actors`, ruleset and branch-protection required status
checks, environment reviewers — by resolving its slug through
`GET /apps/{slug}`; the read path never makes that call, mapping a live
`actor_id` back to a slug from `GET /orgs/{org}/installations` instead. The plan
report therefore carries two checks the diff itself cannot make, run with the
same installation token the job already minted
([#259](https://github.com/vig-os/org-config/issues/259)):

- **`GET /apps/{slug}` per declared slug.** A `403`/`404` means `apply` will
  fail on any add or change of that resource — including one already live, since
  a patch re-sends the whole list. Three of the four sites abort the patch; an
  environment reviewer is instead dropped silently, leaving a protection that was
  never written, so the report separates them.
- **Membership of the org's App installations**, for the sites whose read path
  needs it. A declared App the org has no installation for can never read back as
  written — a ruleset bypass actor is dropped outright, a ruleset status check
  reads back numeric — so `plan` proposes the same change forever and `apply`
  never converges.

The two are independent, and both read the **declared** config only: an actor
that exists live but is declared nowhere needs a live ruleset read and is not
covered. A read that fails for any other reason — a bad credential, a rate-limit
`403` (told apart from a permission `403` by `x-ratelimit-remaining` /
`retry-after`, which carry the only difference), a `5xx`, no answer at all — is
reported as **not checked**, never as a finding: a false "`apply` will fail"
costs more than a missing one.

A slug that is unresolvable *by design* — the standard case is a private App
owned by a sibling org, on a ruleset that is already live and correct — gets an
`[[app_actor]]` entry in `drift-allowlist.toml` (slug + reason). The check still
names it on every run, under **known and suppressed** with that reason, so the
suppression is visible and reviewed rather than silent, and the finding list
keeps meaning something. This org has no such entry: all three slugs it declares
resolve.

The finding is **advisory** — it lands in the PR comment and the job summary and
never changes the job's exit code. `Plan` is not a required check *in this
repository* (ADR-0007 Axis D); a caller may wire its plan context into its own
ruleset, and one does, which is why every step of this check is fail-soft —
guarded, `continue-on-error`, and degrading to "could not be checked" rather
than to a red gate ([#268](https://github.com/vig-os/org-config/issues/268)).
Downstream callers inherit it on their next engine pin bump with no change to
their caller workflow.

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
visibility and reader lists, and the parameters inside a repository ruleset's
`pull_request` rule (`allowed_merge_methods`,
`require_extra_approval_for_unattributed_changes`): Otterdog models the ruleset
*object*, not every rule parameter in it. These have no field in its schema, so
they appear in no plan diff: without an assertion they can be flipped in the UI
and nothing notices — and an unmodelled *rule* parameter is worse than merely
invisible, because apply re-sends the rule without it and GitHub restores its
default ([upstream #768](https://github.com/eclipse-csi/otterdog/issues/768),
which silently re-widened ten rulesets here on 2026-08-08). Not every such
control gets a row: merge methods are owned by the modelled repo settings
instead, and [`unmanaged-controls.toml`](unmanaged-controls.toml) records that
decision where a row would otherwise go. [`unmanaged-controls.toml`](unmanaged-controls.toml) declares each one
as an endpoint, a field path and the expected value; findings join the same
lifecycle under an `unmanaged-control` label. Field paths reach into JSON
**lists** as well as objects — `[type=required_status_checks]` selects one
element of a list, `[].context` projects a field out of every element, and
`compare = "set"` asserts the result as an unordered set — so a repository
ruleset's internals are assertable, including the rule parameters Otterdog's
schema does not model. The leg degrades **per row** — a control
that cannot be read, a path matching zero or several elements, or a collection
too long to arrive in one page, leaves its own issue untouched rather than being
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
floating major. Renovate proposes the pin bumps, and that one pin also carries
the otterdog version a consumer runs, since the reusable workflows default
`otterdog_version` to this repo's own pin
([#228](https://github.com/vig-os/org-config/issues/228)).

[`template/`](template/) is that skeleton, and
[`template/README.md`](template/README.md) is the onboarding runbook (create the
private repo, install the App, set the three secrets, import the live org, wire
the callers). The private `exo-pet/org-config` repo is the pilot consumer
([#25](https://github.com/vig-os/org-config/issues/25)).

A **Free-plan** org onboards read-only first: a private repo on Free has no
enforceable branch protection, so `plan` and `drift` are wired immediately and
`apply` waits for the Team upgrade.

A **private** consumer also has no environment required reviewers (they need
Enterprise), so its apply is dispatch-only — the dispatch is the approval gate —
and merged-but-unapplied would otherwise be silent. A fourth reusable workflow,
[`apply-reminder.yml`](.github/workflows/apply-reminder.yml), exists for exactly
that case: it comments each pending apply onto a pinned tracker issue whose
assignees are the notification list, and `apply` closes the loop on the same
thread ([#202](https://github.com/vig-os/org-config/issues/202)). It is
downstream-only machinery — this repo is public, its apply is reviewer-gated, and
nothing here calls it.

## Known limitations

- **Organization-level rulesets are unusable below Enterprise.**
  `GitHubOrganization.validate()` raises an `ERROR` — *"use of organization
  rulesets requires an 'enterprise' plan"* — whenever a config declares any, so
  an org ruleset cannot be declared here at all. Upstream
  [#731](https://github.com/eclipse-csi/otterdog/pull/731) removed the plan gate
  from the org ruleset *read* path but left this *validate* gate in place; filed
  as [upstream #763](https://github.com/eclipse-csi/otterdog/issues/763).
  Anything org-wide stays hand-managed. **Repository** rulesets are no longer
  affected: the otterdog 1.5.0 pin ungated their read path on private repos of
  any plan, closing
  [#107](https://github.com/vig-os/org-config/issues/107) /
  [upstream #729](https://github.com/eclipse-csi/otterdog/issues/729)
  ([#225](https://github.com/vig-os/org-config/issues/225)).

- **A GitHub App bypass actor on a ruleset is writable only while the engine's
  own token can read the App.** Otterdog resolves an App bypass actor on the
  **write** path through `GET /apps/{app_slug}`, and every otterdog job here
  authenticates as an App *installation* (ADR-0004 Corrections). GitHub's
  reference for that endpoint documents no authentication requirement at all,
  so the boundary below is an **observation**, not a documented mechanism. As
  probed on 2026-09-25, a **public** App answers `200` to any caller — both
  Apps this org names in `bypass_actors` (`commit-action-bot`,
  `vig-os-release-app`) do, and installation-token applies have written both —
  while a **private** App answers `404` unauthenticated, `200` to an org-owner
  PAT and `403` to an installation token, which is the status in the failing
  traceback. `apply` then fails atomically with `failed retrieving app node
  id: … (status=403, "Resource not accessible by integration")`: the live
  ruleset is untouched, but the merged config cannot be applied. The **read**
  path never calls that endpoint — it maps the live `actor_id` to a slug from
  `GET /orgs/{org}/installations` — so `plan` and `drift` render the actor
  correctly, and this one class of change is green on review and red on apply.
  The plan report now flags exactly that, by making the write path's
  `GET /apps/{slug}` call itself at review time
  ([#259](https://github.com/vig-os/org-config/issues/259), *The plan report
  also checks declared App slugs* above) — so the class is visible on the pull
  request, though still not repairable there.
  **Workaround:** run the engine itself once with an org-owner PAT as
  `OTTERDOG_TOKEN` — an owner *can* read the slug, so a one-off `otterdog
  apply` resolves it through otterdog's own code path and writes the complete
  payload. Prefer that over hand-building a REST `PUT` of the ruleset: a
  hand-assembled ruleset payload is precisely the operation that silently lost
  unmodelled fields in
  [#246](https://github.com/vig-os/org-config/issues/246). Once the actor is
  live, the installation token's read path maps its `actor_id` back to the
  slug, matches the declaration and plans clean, so the declaration still
  detects drift. **Residual gap:** detection survives, repair does not —
  `apply` re-sends the *whole* bypass list on any change to that ruleset, so
  every later patch hits the same `403`, otterdog's own reconciliation of a
  manual edit included. Repair stays manual until
  [upstream #772](https://github.com/eclipse-csi/otterdog/issues/772) is fixed
  ([#256](https://github.com/vig-os/org-config/issues/256)). Detection itself
  has one hole, tracked separately in the next bullet: an App bypass actor
  whose App is *not* an installation on the org is dropped on the read path
  ([#262](https://github.com/vig-os/org-config/issues/262)).

- **An App bypass actor is *read* only while its App is an installation on the
  organization; otherwise it is silently dropped.** The slug otterdog renders
  for a live `Integration` bypass actor comes from one map, built per run from
  `GET /orgs/{org}/installations` (`models/github_organization.py:555-558`) and
  applied to each ruleset at `:758-765`, behind the project's own `FIXME`
  ("*need to associate an app id to its slug — GitHub does not support that
  atm*"). That map can only ever hold **org installations**. An actor whose
  `actor_id` is missing from it gets no `app_slug`, and
  `models/ruleset.py:541-548` then logs `fail to map integration actor '<id>',
  skipping` — to otterdog's log, not to `plan.txt` — and **drops the actor from
  the model**. Both directions are wrong, and only one of them now reaches the
  pull request: if the config declares the actor, every `plan` proposes to add
  it back and `apply` never converges, because a ruleset patch re-sends the
  whole bypass list — that half is reported by the plan report's App-slug check,
  which compares each declared slug against the org's installations
  ([#259](https://github.com/vig-os/org-config/issues/259)); if the config does
  not declare it, a live bypass of a protected branch or tag is still never
  reported at all, because catching it needs a live ruleset read. Same root cause as
  [upstream #732](https://github.com/eclipse-csi/otterdog/issues/732) — the
  same installation map, for required status checks — but a strictly worse
  symptom: a status check *falls back* to the numeric
  `<integration_id>:<context>` form (`models/ruleset.py:145-151`) and stays
  visible and writable, which is why this repo's status-check prefixes are
  numeric ([#69](https://github.com/vig-os/org-config/issues/69)); a bypass
  actor has no numeric form and simply disappears. Unfixed at the 1.5.0 pin and
  unfixed on upstream `main` (both read 2026-09-25). **Nothing here is affected
  today:** all fifteen `Integration` bypass actors live across the readable
  `vig-os` and `exo-pet` rulesets — `2433383` `commit-action-bot` (×11),
  `2930017` `vig-os-release-app` (×3) and one private App owned by a sibling
  org (×1) — appear in their org's `/installations` listing, compared on
  2026-09-25. Two blind spots in that comparison, both of them limits of the
  billing plan rather than surfaces left unread by choice: `vig-os/qms` is
  private on a Free-plan org, so both of its ruleset endpoints answer
  `403 Upgrade to GitHub Pro` and its rulesets, if any, could not be read; and
  `GET /orgs/vig-os/rulesets` answers `403 Upgrade to GitHub Team`, because
  org-level rulesets are a Team/Enterprise feature — a Free-plan org can hold
  none, so the refusal is a statement about the plan rather than an unchecked
  surface, but it was not read either. (`exo-pet` is on Team and was read in
  full; its org-level ruleset list is empty.) The case that trips it is a
  bypass slot granted out of band to an App installed on *some repositories*
  without being an org installation, or an installation removed while the
  ruleset keeps the `actor_id`
  ([#262](https://github.com/vig-os/org-config/issues/262)).

- **Creating a repository costs two apply dispatches when Code Security is
  unavailable.** The post-create `PATCH /repos/{org}/{repo}/code-scanning/default-setup`
  returns `403` even when otterdog is asking to turn code scanning *off*, so the
  first `apply` of a new repo exits non-zero although the repository and every
  declared setting were applied; an immediate re-dispatch is a clean no-op. The
  read path already tolerates exactly this condition, the write path does not.
  Unfixed at the 1.5.0 pin — `_update_code_scanning_config` is byte-identical to
  1.4.0 and still raises unconditionally
  ([#209](https://github.com/vig-os/org-config/issues/209),
  [upstream #738](https://github.com/eclipse-csi/otterdog/issues/738)).

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
