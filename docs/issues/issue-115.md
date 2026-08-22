---
type: issue
state: closed
created: 2026-08-07T14:46:49Z
updated: 2026-08-07T15:01:29Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/115
comments: 1
labels: chore, security, priority:medium, area:ci, effort:medium, semver:patch
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-08T03:28:18.167Z
---

# [Issue 115]: [Harden devkit rulesets: tag protection, CodeQL gate on main, drop unsatisfiable code-owner review](https://github.com/vig-os/org-config/issues/115)

Three approved settings changes to the `devkit` block of `otterdog/vig-os/vig-os.jsonnet`, plus one live-only security toggle the otterdog schema cannot model. All were approved in the devkit settings review (findings D2, D5, D8, D10).

## D2 — `devkit` has no tag-protection ruleset

`commit-action` declares a `Tag protection` ruleset (`target: 'tag'`, `include_refs: ['~ALL']`, creations/updates/deletions blocked, force pushes allowed, bypass actor `vig-os-release-app`), but `devkit` — which publishes the release tags every consumer pins — declares none. Any actor with write access can create, move, or delete a `devkit` release tag out of band.

`devkit` pushes its release tags from `release.yml`'s publish job with a token minted from `RELEASE_APP_CLIENT_ID` / `RELEASE_APP_PRIVATE_KEY`, i.e. the `vig-os-release-app` App (`app_id` 2930017, installation bypass id already used by `commit-action`), and deletes leftover RC tags from `promote-release.yml` with the same App. It is the only tag writer in the repo (`release.yml:982` is the sole `git tag`), it uses bare `X.Y.Z` tags (no `DEVKIT_TAG_PREFIX`) and declares no floating tags, so a single always-bypass actor is sufficient.

**Change:** declare a `Tag protection` ruleset on `devkit` matching `commit-action`'s verbatim.

## D5 — CodeQL is not a required status check on `main`

`devkit`'s `codeql.yml` runs on every PR to `main` but nothing gates on it, so a PR with a failing CodeQL leg merges. `Main protection` currently requires only `15368:Test Summary`.

The analysis job is a matrix (`language: ['python', 'actions']`), so it reports **two** contexts, not one — verified against a recent `main` commit:

```
CodeQL Analysis (actions)   app=github-actions
CodeQL Analysis (python)    app=github-actions
CodeQL                      app=github-advanced-security   # code-scanning result check, not a workflow job
```

**Change:** add `15368:CodeQL Analysis (actions)` and `15368:CodeQL Analysis (python)` to `Main protection`'s `required_status_checks.status_checks`. `main` only — `Dev protection` and `Release protection` stay as they are (decided).

`devkit` is public, so the workflow's `if: ${{ !github.event.repository.private }}` guard never skips the job and the checks always report — no permanently-pending gate.

## D8 — `require_code_owner_review` can never be satisfied

`Main protection` and `Release protection` both set `requires_code_owner_review: true`, and `.github/CODEOWNERS` names exactly one owner (`@c-vigo`) for every entry. Since `@c-vigo` authors the PRs, GitHub will not accept their own review, so the code-owner gate on a CODEOWNERS-touching PR is structurally unsatisfiable and its only possible outcome is an `#OrganizationAdmin` bypass. A control that only ever produces bypasses is worse than no control: it trains the bypass habit and pollutes the audit trail. `devkit#1219` already reduced CODEOWNERS to the single-maintainer reality; this is the ruleset half.

**Change:** `requires_code_owner_review: false` on `devkit`'s `Main protection` and `Release protection`. The real gates — 1 approving review on `main`, thread resolution, required status checks, signed commits — are unchanged.

## D10 — secret-scanning extras (live-only)

`devkit` is public with `secret_scanning` and `secret_scanning_push_protection` enabled, but `secret_scanning_non_provider_patterns` and `secret_scanning_validity_checks` are both `disabled` live.

otterdog 1.3.4 models **only** `secret_scanning` and `secret_scanning_push_protection` (`otterdog/models/repository.py`; the vendored `otterdog-defaults.libsonnet` exposes the same two), so neither extra can be declared. They are enabled live via `gh api -X PATCH repos/vig-os/devkit` and become unmanaged controls — tracked for drift assertion in the follow-up issue.

## Engine constraint — manual live reconciliation

otterdog 1.3.4 cannot PATCH an existing repo ruleset whose `required_status_checks` use the numeric `15368:<context>` form (#69, upstream eclipse-csi/otterdog#695). D5 and D8 are both ruleset **modifications**, so they are reconciled live with `gh api -X PUT` before the apply runs; the plan then sees only the D2 ruleset **add**, which otterdog creates normally.

---

# [Comment #1]() by [c-vigo]()

_Posted on August 7, 2026 at 02:51 PM_

## D10 outcome: not changed — the setting is unsettable, not merely unmodelled

Attempted the live enable and it is a dead end. `gh api -X PATCH repos/vig-os/devkit` with `security_and_analysis.secret_scanning_non_provider_patterns` / `secret_scanning_validity_checks` returns **200 OK and changes nothing** (verified twice, form-encoded and JSON body, re-`GET` after each).

Cause:

```console
$ gh api repos/vig-os/devkit/code-security-configuration --jq '{status, id: .configuration.id, np: .configuration.secret_scanning_non_provider_patterns, vc: .configuration.secret_scanning_validity_checks}'
{"status":"enforced","id":237480,"np":"enabled","vc":"enabled"}

$ gh api repos/vig-os/devkit --jq '.security_and_analysis'
{... "secret_scanning_non_provider_patterns":{"status":"disabled"}, "secret_scanning_validity_checks":{"status":"disabled"} ...}
```

`devkit` is attached to the **enforced** org code-security configuration `237480` ("Github + Advanced QL allowed"), which already declares both `enabled` at org level. An enforced configuration overrides repo-level writes, so the repo-level PATCH is a silent no-op — and the org side already asks for what we want. The org says enabled, the repo reads disabled, and nothing reconciles them: the features require a GHAS **Secret Protection** entitlement the org's plan does not carry.

**Decision: change nothing.** Editing configuration `237480` is out of scope and out of proportion — it governs every repo in the org and its `code_scanning_default_setup: enabled` / `code_scanning_options.allow_advanced: true` pairing is what currently lets `devkit`'s advanced `codeql.yml` upload SARIF at all. Recorded instead as an *unassertable* control in #116.

