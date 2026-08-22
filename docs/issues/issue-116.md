---
type: issue
state: open
created: 2026-08-07T14:46:57Z
updated: 2026-08-07T16:51:42Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/116
comments: 2
labels: feature, priority:low, area:ci, effort:medium
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-08T03:28:17.873Z
---

# [Issue 116]: [Drift layer: assert unmanaged live controls the otterdog schema cannot model](https://github.com/vig-os/org-config/issues/116)

## Problem

`otterdog plan` is the only thing that watches live org state, so a control otterdog's model has no field for is invisible: it can be turned off live and nothing in this repo notices. The drift layer inherits the blind spot, because it parses `otterdog plan` output rather than querying GitHub directly.

Three such controls are known today:

### 1. `sha_pinning_required` (Actions policy)

```console
$ gh api repos/vig-os/devkit/actions/permissions
{"enabled":true,"allowed_actions":"all","sha_pinning_required":true}
$ gh api orgs/vig-os/actions/permissions
{"enabled_repositories":"all","allowed_actions":"all","sha_pinning_required":false}
```

`vig-os/devkit` sets `sha_pinning_required: true` live; the **org** setting is `false`, so the repo-level value is the only thing holding it. otterdog 1.3.4 models neither — the string `sha_pinning` does not occur anywhere in the package; its `workflows` block covers `actions_can_approve_pull_request_reviews`, allowed-actions, and friends, but not SHA pinning. So devkit's strongest supply-chain control is entirely unasserted: a UI click silently disables it.

Assertable via `GET /repos/{owner}/{repo}/actions/permissions` (and the `GET /orgs/{org}/actions/permissions` equivalent).

### 2. Fork-PR workflow-approval policy

The "require approval for fork pull requests" setting is UI-only on the Free plan — the REST endpoint 404s — so it can be neither declared nor read back through the API. Needs either a documented manual re-check cadence or a UI-scrape alternative; at minimum the repo should record that it is unmanaged rather than silently assume it.

### 3. Secret scanning: non-provider patterns and validity checks

`security_and_analysis.secret_scanning_non_provider_patterns` and `secret_scanning_validity_checks` are returned by `GET /repos/{owner}/{repo}`, but otterdog 1.3.4 models only `secret_scanning` and `secret_scanning_push_protection`.

Worse than unmanaged: on `devkit` they are **unsettable from either side**. The repo reads `disabled`; a repo-level `PATCH` returns `200 OK` and changes nothing, because `devkit` is attached to the **enforced** org code-security configuration `237480` ("Github + Advanced QL allowed"), which already declares both `enabled`:

```console
$ gh api repos/vig-os/devkit/code-security-configuration --jq '{status, id: .configuration.id, np: .configuration.secret_scanning_non_provider_patterns, vc: .configuration.secret_scanning_validity_checks}'
{"status":"enforced","id":237480,"np":"enabled","vc":"enabled"}
$ gh api repos/vig-os/devkit --jq '.security_and_analysis.secret_scanning_non_provider_patterns'
{"status":"disabled"}
```

So the org config and the repo state disagree permanently and no API write reconciles them — the features need a GHAS Secret Protection entitlement the plan does not carry. This is exactly the class of divergence an assertion leg should surface: not "someone turned it off" but "we believe this is on and it is not". See #115.

## Proposal

Extend `drift.yml` (or the `drift-layer` CLI) with an **unmanaged-controls assertion leg**: a small declarative table of `(endpoint, jq path, expected value)` triples checked with direct `gh api` calls, emitting the same deduplicated `drift` + `critical` issues as the plan-parsing leg (ADR-0002 fingerprint lifecycle), so an unmanaged control that flips is reported exactly like a modelled one.

Sketch:

- a config file (e.g. `unmanaged-controls.toml`) beside `drift-allowlist.toml`, listing per-scope assertions;
- a `drift_layer` module that evaluates them against the injected GitHub client and yields `DriftRecord`s with their own fingerprint namespace (e.g. `unmanaged-control:<repo>:<key>`);
- graceful degradation on a 404 (Free-plan endpoints): report "unassertable" once, do not open a recurring issue;
- seed the table with the three controls above.

This keeps otterdog as the source of truth for everything it can model and adds a thin, explicitly-scoped escape hatch for everything it cannot — rather than hand-maintaining a checklist.

## Scope

Enhancement only; no behavior change until implemented. Filed out of the devkit settings review (finding D9).

---

# [Comment #1]() by [c-vigo]()

_Posted on August 7, 2026 at 04:27 PM_

## Fourth unmanaged control: org-level security defaults for **new** repositories

Set live on `vig-os` today (settings audit item 4). These are org-wide defaults applied at repository *creation* time, so they decide the security posture of every repo added from now on — and none of them is expressible in this repo's config.

### Not in the otterdog schema

```console
$ grep -rn "for_new_repositories" ~/.cache/uv/.../otterdog/ otterdog/vig-os/vendor/
# (no matches)
```

otterdog 1.3.4 models neither the org `GET /orgs/{org}` `*_enabled_for_new_repositories` family nor any equivalent. There is no jsonnet counterpart to write, so this was applied out of band and is unmanaged from now on.

### Exactly what was changed

`PATCH /orgs/vig-os`, one field per request, each verified by re-`GET`. Complete before -> after diff of `GET /orgs/vig-os` (nothing else on the org moved):

```diff
-  "dependency_graph_enabled_for_new_repositories": false,
+  "dependency_graph_enabled_for_new_repositories": true,
-  "dependabot_alerts_enabled_for_new_repositories": false,
+  "dependabot_alerts_enabled_for_new_repositories": true,
-  "dependabot_security_updates_enabled_for_new_repositories": false,
+  "dependabot_security_updates_enabled_for_new_repositories": true,
-  "secret_scanning_enabled_for_new_repositories": false,
+  "secret_scanning_enabled_for_new_repositories": true,
-  "secret_scanning_push_protection_enabled_for_new_repositories": false,
+  "secret_scanning_push_protection_enabled_for_new_repositories": true,
```

`advanced_security_enabled_for_new_repositories` was **deliberately left `false`** — GitHub Advanced Security is a paid entitlement the org does not carry.

No field was rejected; all five took on the first attempt. (Worth contrasting with the repo-level secret-scanning extras below, where the write silently no-ops.)

### Why this belongs in the assertion table

Every new repo's baseline security depends on five booleans that live only in GitHub's UI/API, with nothing in this repo to compare them against. A single UI toggle silently downgrades every repo created afterwards, and the damage is invisible until someone audits a repo that was created in the meantime — by which point the affected repos each need fixing individually.

Assertable via `GET /orgs/vig-os`, jq path `.<field>`, expected `true` for the five above and `false` for `advanced_security_enabled_for_new_repositories`.

### Running list for the assertion table

| # | control | scope | endpoint | expected |
|---|---|---|---|---|
| 1 | `sha_pinning_required` | repo `devkit` | `GET /repos/vig-os/devkit/actions/permissions` | `true` |
| 1b | `sha_pinning_required` | org | `GET /orgs/vig-os/actions/permissions` | `false` today, see #120 |
| 2 | fork-PR workflow approval policy | repo | UI-only, REST 404 on Free | report unassertable |
| 3 | `secret_scanning_non_provider_patterns` / `..._validity_checks` | repo `devkit` | `GET /repos/vig-os/devkit` | wanted `enabled`, stuck `disabled` (see #115) |
| 4 | `dependency_graph` / `dependabot_alerts` / `dependabot_security_updates` / `secret_scanning` / `secret_scanning_push_protection` `_enabled_for_new_repositories` | org | `GET /orgs/vig-os` | `true` |
| 4b | `advanced_security_enabled_for_new_repositories` | org | `GET /orgs/vig-os` | `false` (paid) |

Related: #115, #120, #121.


---

# [Comment #2]() by [c-vigo]()

_Posted on August 7, 2026 at 04:51 PM_

## Fifth unmanaged control: org secret **visibility** and selected-repository lists

From the #123 migration (PR #126). Same class as the rest of this issue's table, and arrived at the hard way.

`otterdog/models/secret.py:88` makes `include_for_live_patch()` return `not has_dummy_secret()`, and live-patch generation is what `plan` renders (`models/__init__.py:788`). Eleven of the twelve `vig-os` org secrets are declared `value: '********'`, so they are dropped from the plan **entirely** — not merely skipped at apply.

Empirically confirmed on PR #126, which declares `visibility: 'selected'` plus explicit `selected_repositories` for all eleven:

```
  ~ org_secret[name="ORG_CONFIG_CANARY"] {          # the one non-dummy secret
    ~ selected_repositories = [ + "org-config" ]
    ~ visibility            = "public" -> "selected"
  ~ }
  ~ repository[name="vs-dolt"] { ... }              # allow-listed
  Plan: 0 to add, 3 to change, 0 to delete.
```

Eleven declared changes, zero of them in the plan.

**Consequence:** once the one-time UI flip narrows them, the config records the intended lists but nothing verifies them. Someone widening `COMMIT_APP_PRIVATE_KEY` back to `all` in the UI produces no plan diff, no drift issue, and no other signal. The lists are also a live maintenance coupling — `DEVKIT_UPGRADE_APP_*` must gain any repo re-scaffolded to devkit >= 1.6 — so silent divergence is likely rather than hypothetical.

**Assertable, and cheaply:**

```console
$ gh api orgs/vig-os/actions/secrets --jq '.secrets[]|"\(.name) \(.visibility)"'
$ gh api orgs/vig-os/actions/secrets/COMMIT_APP_PRIVATE_KEY/repositories --jq '[.repositories[].name]|sort'
```

Both are plain reads. The expected lists are already in `otterdog/vig-os/vig-os.jsonnet`, so the assertion can be generated from the committed config rather than hand-maintained in a second place — the best case in this whole table.

### Updated table

| # | control | scope | endpoint | expected |
|---|---|---|---|---|
| 1 | `sha_pinning_required` | repo `devkit` | `GET /repos/vig-os/devkit/actions/permissions` | `true` |
| 1b | `sha_pinning_required` | org | `GET /orgs/vig-os/actions/permissions` | `false` today, see #120 |
| 2 | fork-PR workflow approval policy | repo | UI-only, REST 404 on Free | report unassertable |
| 3 | `secret_scanning_non_provider_patterns` / `..._validity_checks` | repo `devkit` | `GET /repos/vig-os/devkit` | wanted `enabled`, stuck `disabled` (#115) |
| 4 | five `*_enabled_for_new_repositories` | org | `GET /orgs/vig-os` | `true` |
| 4b | `advanced_security_enabled_for_new_repositories` | org | `GET /orgs/vig-os` | `false` (paid) |
| 5 | org secret `visibility` | org | `GET /orgs/vig-os/actions/secrets` | `selected` for all 12 |
| 5b | org secret `selected_repositories` | org | `GET /orgs/vig-os/actions/secrets/{name}/repositories` | per-secret list from the committed jsonnet |

Related: #115, #120, #121, #123, #126.


