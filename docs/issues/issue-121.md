---
type: issue
state: closed
created: 2026-08-07T16:24:26Z
updated: 2026-08-07T16:34:57Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/121
comments: 0
labels: chore, security, priority:medium, area:ci, effort:small, semver:patch
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-08T03:28:17.060Z
---

# [Issue 121]: [Org settings: block workflow PR approvals and member repo creation](https://github.com/vig-os/org-config/issues/121)

Two approved org-level settings changes from the settings audit (follows #115, #118). Both live in the `settings+:` block of `otterdog/vig-os/vig-os.jsonnet`; both are plain org-settings PATCHes, so `otterdog apply` handles them normally (no #69 ruleset workaround needed).

## 1. Workflows must not be able to approve pull requests

```console
$ gh api orgs/vig-os/actions/permissions/workflow
{"default_workflow_permissions":"read","can_approve_pull_request_reviews":true}
```

Org-wide, a GitHub Actions workflow can submit an **approving review**. That is the one permission that can satisfy `Main protection`'s `required_approving_review_count: 1` without a human, so the strongest gate in the fleet is reachable by any workflow with `pull-requests: write` — including one added in the very PR it would approve. Combined with `allowed_actions: all` (no action allow-list) the blast radius is every repo in the org.

`devkit` already closes this at repo level:

```jsonnet
workflows+: {
  actions_can_approve_pull_request_reviews: false,
},
```

but it is the **only** repo that does, so `commit-action`, `sync-issues-action`, `org-config` itself, `tessera`, `scitadel` and the rest all inherit the permissive org default.

**Change:** `settings.workflows.actions_can_approve_pull_request_reviews: false`. Note the nesting — org-level workflow settings live under `settings.workflows` in the vendored schema (`otterdog-defaults.libsonnet`, `newOrg`), which is a different location from the repo-level `workflows+:` block that hangs directly off `newRepo`. `devkit`'s repo-level declaration is left in place: it is now redundant with the org default but harmless, and it keeps the intent explicit on the repo that publishes the fleet's tooling.

## 2. Members must not be able to create repositories

```console
$ gh api orgs/vig-os --jq '{members_can_create_public_repositories, members_can_create_private_repositories}'
{"members_can_create_public_repositories":true,"members_can_create_private_repositories":true}
```

Both are currently declared `true` (`vig-os.jsonnet:12-13`). The org has three members; two are owners (`c-vigo`, `gerchowl`) and one is a plain member (`irenecortinovis`), so this setting binds today rather than being theoretical.

Repository creation in this org is meant to be **config-first**: a repo is declared in `vig-os.jsonnet` and `otterdog apply` creates it. A repo created through the GitHub UI bypasses every default this repo exists to enforce — merge policy, rulesets, signed commits, secret scanning, the lot — and it is created with no ruleset at all.

The recovery path is deliberately asymmetric and slow:

- `apply` **creates** what the config declares, but never **deletes** what it does not. `--delete-resources` is deliberately omitted (`.github/workflows/apply.yml:72-73`: *"resources absent from the config are NOT deleted (apply.py:142-144 skips REMOVE patches without the flag). Destructive deletions stay a manual, explicitly-flagged operation."*).
- So an undeclared repo is never cleaned up automatically. It surfaces only through the inventory sweep (#21) as a `drift` + `critical` issue in the `repository-inventory:<name>` namespace, and is then removed by hand.

Closing member creation makes the declarative path the **only** path for members, rather than one of two. Owners can still create repositories — GitHub gives owners that right unconditionally and no org setting revokes it — so for `c-vigo` and `gerchowl` this stays a matter of discipline backed by the undeclared-repo drift sweep. That residual is accepted, not overlooked.

**Change:** `members_can_create_public_repositories: false` and `members_can_create_private_repositories: false`, kept as explicit values with an inline rationale comment (house style: state the decision, do not lean on a default).

## Apply

Three org-setting fields change. The plan on the PR should show exactly those three plus the permanent allow-listed `vs-dolt` cosmetic diff. No manual live reconciliation — `otterdog apply` writes org settings without trouble; #69 affects repo *rulesets* only.

