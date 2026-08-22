---
type: issue
state: open
created: 2026-08-07T16:28:18Z
updated: 2026-08-07T16:43:06Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/123
comments: 2
labels: chore, security, priority:medium, area:ci, effort:large, semver:patch
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-08T03:28:16.732Z
---

# [Issue 123]: [Narrow org secret visibility from all to selected with per-secret repo lists](https://github.com/vig-os/org-config/issues/123)

Settings-audit item 2. **Issue only — no implementation here.**

## Problem

All twelve `vig-os` organization secrets are `visibility: all`:

```console
$ gh api orgs/vig-os/actions/secrets --jq '.secrets[]|"\(.name) \(.visibility)"'
COMMIT_APP_CLIENT_ID all          DEVKIT_UPGRADE_APP_PRIVATE_KEY all    RELEASE_APP_CLIENT_ID all
COMMIT_APP_ID all                 DOCKERHUB_TOKEN all                   RELEASE_APP_ID all
COMMIT_APP_PRIVATE_KEY all        DOCKERHUB_USERNAME all                RELEASE_APP_PRIVATE_KEY all
DEVKIT_UPGRADE_APP_CLIENT_ID all  ORG_CONFIG_CANARY all
DEVKIT_UPGRADE_APP_ID all         RELEASE_APP_PRIVATE_KEY all
```

`all` means every workflow in **all 14 repos** in the org can read them:

```
commit-action  devkit  devkit-smoke-test  h5v  nvd-mirror  org-config  org-config-testbed
qms  qx  scitadel  sync-issues-action  tessera  vigos-mvp  vs-dolt
```

Three GitHub App **private keys** (`COMMIT_APP_PRIVATE_KEY`, `RELEASE_APP_PRIVATE_KEY`, `DEVKIT_UPGRADE_APP_PRIVATE_KEY`) and a Docker Hub push token are therefore reachable from repos that have no business touching them — including `vs-dolt`, which is unmaintained and carries the permanent config drift we allow-list, and `org-config-testbed`, which by design is created, mutated and destroyed by an automated harness. A workflow added to any of those repos can mint an App installation token with the App's full org-wide permissions. The blast radius of one careless `.github/workflows/*.yml` is currently the whole organization.

Related hardening already landed: #115 (devkit rulesets), #116 (unmanaged-control drift assertions), #120 (org-wide SHA pinning), #121 (workflows may no longer approve PRs; members may no longer create repos).

## Goal

Move all twelve to `visibility: selected` with an explicit per-secret repository list, declared in `otterdog/vig-os/vig-os.jsonnet`.

otterdog models this fully — `organization_secret.py:33-34` carries `visibility` and `selected_repositories`, and the vendored `newOrgSecret` defaults to `visibility: 'public'` (which maps to GitHub's `all`, hence today's silent wide-open state). So the end state is **fully declarative**: jsonnet and live change together in one PR, per the house rule, with no permanently-unmanaged residue. Note `visibility: 'private'` is rejected on the Free plan (`organization_secret.py:45-50`); `'selected'` is the only narrowing available and is what we want anyway.

## Required pre-work: map the actual consumers

This cannot be guessed. Before touching anything, build a secret -> consuming-repos matrix by grepping **every** repo's workflows for each secret name — `gh api repos/vig-os/<repo>/contents/.github/workflows` per repo, or shallow clones — and record it in the issue. Points to watch:

- **`DEVKIT_UPGRADE_APP_*`** is consumed by `devkit-upgrade.yml`, which the devkit scaffold stamps into **every** scaffolded consumer repo. Its selected-list is therefore broad by design — close to `all` minus the repos that are not devkit consumers. Do not assume "org secret with a narrow-sounding name" means "narrow list".
- **`ORG_CONFIG_CANARY`** is the SOPS/age pipeline canary and is almost certainly `org-config` + `org-config-testbed` only.
- **`COMMIT_APP_*`** is used by `sync-issues.yml` and the changelog-commit workflows across most repos; `RELEASE_APP_*` only by repos that actually publish releases.
- `tessera` carries **repo-level** secrets that shadow org ones (see #111) — check whether a repo appearing to consume an org secret is in fact resolving its own.
- Reusable workflows called cross-repo (`workflow_call`) resolve secrets in the **caller's** repo; a grep of the callee alone will miss the real consumer.

## Hard invariant — the ordering rule

**Never remove a secret's reach while any pinned workflow still references it.** This is the lesson from the `playground-carlos` incident and it is the same failure mode as the numeric-App-ID retirement in #112: a workflow pinned to an older tag keeps referencing the old name/scope long after `main` has moved on, so a change that looks safe against `main` breaks the pinned callers.

Concretely, for every secret:

1. **Expand or create first.** Put the secret in place for every repo that needs it (create/extend the selected-list) *before* anything is taken away.
2. **Narrow second**, and only after step 1 is verified live.
3. **Verify CI after each narrowing** — a repo silently loses the secret rather than erroring at config time; the failure shows up as an empty-token run at the next release or sync, potentially weeks later.
4. Prefer one PR per secret family (`COMMIT_APP_*`, `RELEASE_APP_*`, `DEVKIT_UPGRADE_*`, `DOCKERHUB_*`, `ORG_CONFIG_CANARY`) over one big-bang change, so a mistake is attributable and revertible.

Also remember `otterdog apply` never deletes secrets, and secret **values** are not readable back — narrowing visibility is the one lever available here, and it is reversible, but a repo dropped from a list has to be re-added and its workflow re-run to confirm recovery.

## Deliverable

- The consumer matrix (secret x repo), committed or recorded in this issue.
- Per-secret `visibility: 'selected'` + `selected_repositories: [...]` in `otterdog/vig-os/vig-os.jsonnet`.
- CHANGELOG entry.
- Evidence that each affected repo's next real CI run (sync-issues, release, image push) still authenticates.

---

# [Comment #1]() by [c-vigo]()

_Posted on August 7, 2026 at 04:40 PM_

## Consumer matrix — evidence

Method: shallow-cloned all 14 org repos with a sparse `.github` checkout and grepped the **whole** `.github` tree (not just `workflows/`) for every `secrets.*` reference. Both `.yml` and `.yaml` are covered — `vs-dolt` uses `.yaml` and would have been missed by a `*.yml` glob.

Cross-repo `workflow_call` was checked explicitly: `grep -rn "uses: vig-os/[a-z-]*/\.github/workflows"` across all 14 repos returns **no matches**. Every `secrets: inherit` is a *same-repo* call (release orchestrators calling `release-core.yml` / `release-publish.yml` / `prepare-release-extension.yml`), so every secret resolves in the repo that declares the caller — no hidden third-party consumer. Scheduled and `workflow_dispatch` workflows are included (the grep is trigger-agnostic).

### Secret -> repositories

| Org secret | Consuming repos | n |
|---|---|---|
| `COMMIT_APP_CLIENT_ID` | commit-action, devkit, devkit-smoke-test, org-config, sync-issues-action | 5 |
| `COMMIT_APP_ID` | commit-action, devkit, devkit-smoke-test, h5v, org-config, scitadel, sync-issues-action | 7 |
| `COMMIT_APP_PRIVATE_KEY` | commit-action, devkit, devkit-smoke-test, h5v, org-config, scitadel, sync-issues-action | 7 |
| `DEVKIT_UPGRADE_APP_CLIENT_ID` | **none yet** (declared ahead of vig-os/devkit#1365) | 0 |
| `DEVKIT_UPGRADE_APP_ID` | commit-action, devkit-smoke-test, org-config, sync-issues-action | 4 |
| `DEVKIT_UPGRADE_APP_PRIVATE_KEY` | commit-action, devkit-smoke-test, org-config, sync-issues-action | 4 |
| `DOCKERHUB_TOKEN` | **none** | 0 |
| `DOCKERHUB_USERNAME` | **none** | 0 |
| `ORG_CONFIG_CANARY` | **none** (written by `otterdog apply` from SOPS; never read by a workflow) | 0 |
| `RELEASE_APP_CLIENT_ID` | commit-action, devkit, devkit-smoke-test, org-config, sync-issues-action | 5 |
| `RELEASE_APP_ID` | h5v, scitadel | 2 |
| `RELEASE_APP_PRIVATE_KEY` | commit-action, devkit, devkit-smoke-test, h5v, org-config, scitadel, sync-issues-action | 7 |

### Repositories that consume **no** org secret

`nvd-mirror`, `org-config-testbed`, `qms`, `qx`, `tessera`, `vigos-mvp`, `vs-dolt` — 7 of 14.

- `tessera` references `APP_SYNC_ISSUES_ID` / `APP_SYNC_ISSUES_PRIVATE_KEY`, which are its **own repo-level** secrets (the org pair was retired in #111). It resolves nothing at org scope.
- `qx` uses repo-level `PARTREG_TEST_PAT`; `scitadel` also uses repo-level `CARGO_REGISTRY_TOKEN`, `RELEASE_BOT_PRIVATE_KEY`, `RELEASE_PLEASE_TOKEN`.
- `vs-dolt` (12 workflow files, all `.yaml`) uses only repo-level secrets — `DOCKER_HUB_ACCESS_TOKEN`, `DOCKER_HUB_USERNAME`, `APPLE_ID_PASSWORD`, `APPSTORE_*`, `REPO_ACCESS_TOKEN`, `WORKBENCH_CONNECTION_URL`. Note the names differ from the org pair (`DOCKER_HUB_*` vs `DOCKERHUB_*`).
- `org-config-testbed` and `vigos-mvp` have **no workflows at all**.

So `vs-dolt` and `org-config-testbed` end up in no list — which is the point of the exercise.

### Three findings worth calling out

1. **`DOCKERHUB_TOKEN` and `DOCKERHUB_USERNAME` are orphaned.** Zero references across all 14 repos. The only Docker Hub credentials in use are `vs-dolt`'s **repo-level** `DOCKER_HUB_ACCESS_TOKEN` / `DOCKER_HUB_USERNAME` — different names, different scope. This is the same pattern #111 retired for `APP_SYNC_ISSUES_*`. Narrowing them to `selected` with an **empty** list removes all reach without deleting the values; actual retirement is a separate change (follow-up filed).
2. **`DEVKIT_UPGRADE_APP_*` is narrower than expected.** Only 4 repos carry `devkit-upgrade.yml`, and they are exactly the ones on `DEVKIT_VERSION=1.6.0` (`commit-action`, `devkit-smoke-test`, `org-config`, `sync-issues-action`; `devkit` itself is the source and does not upgrade itself). `h5v` (`DEVCONTAINER_VERSION=0.3.1`) and `scitadel` (`0.3.3`) are still on the legacy scaffold — which is also why they use the numeric `COMMIT_APP_ID` / `RELEASE_APP_ID` form rather than the client-ID form. **When either is re-scaffolded to devkit 1.6+, it must be added to the `DEVKIT_UPGRADE_APP_*` lists or its upgrade workflow fails silently.** This maintenance coupling goes in a jsonnet comment.
3. **The client-ID migration (#112) is visible in the matrix.** `*_APP_CLIENT_ID` covers the five 1.6.0 repos; `*_APP_ID` covers the legacy pair (`h5v`, `scitadel`) plus the 1.6.0 repos that still reference both. The lists differ per secret for that reason and must not be collapsed into one shared list.


---

# [Comment #2]() by [c-vigo]()

_Posted on August 7, 2026 at 04:43 PM_

## Mechanism resolved — and it is not what the issue assumed

Tested against a **throwaway** org secret (`ORG_SECRET_VISIBILITY_PROBE`, dummy value, created and deleted within this investigation) rather than on real credentials.

### The REST API cannot change visibility without the value

```console
$ printf '{"visibility":"selected","selected_repository_ids":[1263724373]}' \
    | gh api -X PUT orgs/vig-os/actions/secrets/ORG_SECRET_VISIBILITY_PROBE --input -
{"message":"Invalid request.\n\n\"encrypted_value\", \"key_id\" weren't supplied.","status":"422"}
```

And the sub-endpoint cannot bootstrap it either — chicken and egg:

```console
$ printf '{"selected_repository_ids":[1263724373]}' \
    | gh api -X PUT orgs/vig-os/actions/secrets/ORG_SECRET_VISIBILITY_PROBE/repositories --input -
{"message":"Conflict","errors":"You cannot update selected repositories for a secret when the
 visibility is not set to 'selected'","status":"409"}
```

### otterdog cannot do it either, for the eleven dummy-valued secrets

`otterdog/models/secret.py:88` — `include_for_live_patch()` returns `not self.has_dummy_secret()`. Eleven of the twelve org secrets are declared `value: '********'`, which `has_dummy_secret()` matches (`secret.py:69-72`), so **`otterdog apply` skips those resources entirely** — it would show a `visibility` diff in the plan (only `value` is excluded from diff computation, `secret.py:74-77`) but never write it. A plan diff that apply silently declines to apply is precisely the failure mode this issue exists to avoid, so it must not be relied on.

### What *does* work

| Operation | Needs the value? | Mechanism |
|---|---|---|
| `all` -> `selected` (first flip) | **yes** | UI only, in practice — REST needs `encrypted_value`+`key_id` |
| maintain the repo list once `selected` | **no** | `PUT /orgs/{org}/actions/secrets/{name}/repositories` |
| full declarative management | value must be resolvable | `otterdog apply`, if the jsonnet value is a real credential-provider reference |

Verified that list maintenance works without the value:

```console
$ gh api .../ORG_SECRET_VISIBILITY_PROBE/repositories --jq '[.repositories[].name]'
["org-config"]
$ printf '{"selected_repository_ids":[1263724373,1101415912]}' \
    | gh api -X PUT .../ORG_SECRET_VISIBILITY_PROBE/repositories --input -
$ gh api .../ORG_SECRET_VISIBILITY_PROBE/repositories --jq '[.repositories[].name]'
["devkit","org-config"]
```

**This is the good news for maintenance:** once Carlos performs the one-time flip, adding `h5v`/`scitadel` to the `DEVKIT_UPGRADE_APP_*` lists on their next re-scaffold is a plain `gh api` call — no value, no UI.

### Consequence: a split plan

- **`ORG_CONFIG_CANARY` — fully declarative.** Its jsonnet value is `pass:org-config/ORG_CONFIG_CANARY`, a real credential-provider reference that `apply.yml` resolves from the committed SOPS ciphertext (the decrypt-into-`pass` bridge runs on `if: hashFiles('secrets/*.yaml') != ''`, i.e. on *every* apply, not only when `secrets/**` changed). So it is not a dummy, `include_for_live_patch` is true, and `otterdog apply` sets visibility and the repo list itself. **This is the pilot** — it proves the declarative path end to end.
- **The other eleven — jsonnet declares, Carlos flips.** The config states the target state (so `plan`/drift assert it from then on), and the one-time `all -> selected` flip happens in the UI, where changing repository access does not require re-entering the value.

### Why this is still safe

The two halves land in a deliberate order, and the unsafe direction never occurs:

1. Config merges first, declaring the **full** consumer list for every secret.
2. Carlos narrows live to exactly that list.

Between the two, live is *broader* than declared — never narrower — so no consumer can lose reach. The `playground-carlos` silent failure was the opposite ordering.

A longer-term option, deliberately **out of scope** here: move the eleven values into `secrets/vig-os.yaml` under SOPS like the canary, which would make all twelve fully declarative. That is a much larger change and collides with ADR-0003's deliberate bootstrap exclusions, so it belongs in its own issue.


