---
type: issue
state: open
created: 2026-08-31T09:58:00Z
updated: 2026-08-31T09:58:00Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/209
comments: 0
labels: bug, priority:medium, area:workflow
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-01T07:25:55.195Z
---

# [Issue 209]: [otterdog 1.4.0: creating a repository always fails the first apply when Code Security is unavailable](https://github.com/vig-os/org-config/issues/209)

## Summary

otterdog 1.4.0 cannot create a repository in an organization without Code
Security available: the first `apply` always exits `1`. The repository *is*
created and every declared setting *is* applied — the failure is a post-create
`PATCH /repos/{org}/{repo}/code-scanning/default-setup` that returns `403`
**even though otterdog is asking to turn code scanning off**. A second `apply`
is a clean no-op and goes green.

So for every downstream org on GitHub Team with private repos, **provisioning a
new repo costs two apply dispatches**, the first of which is a red run that
looks like a partial mutation but is not one.

Upstream: eclipse-csi/otterdog#738.

## The defect

`add_repo` defers a set of settings to a post-create `update_repo`
(`providers/github/rest/repo_client.py:250-300`), among them
`code_scanning_default_config`. `update_repo` calls
`_update_code_scanning_config` (`:550`), which raises on any error. The endpoint
`403`s for *any* payload when Code Security is unavailable, including
`{"state": "not-configured"}`.

The read path already tolerates exactly this: `_fill_code_scanning_config`
(`:537`) records the config only `if status == 200`, so the live read yields no
key, `code_scanning_default_setup_enabled` maps to `False`
(`models/repository.py:883-887`), and it matches a config declaring `false`.
The write path is missing that same tolerance — which is why this is invisible
on existing repos and fires only on `ADD`.

The trigger is just the base-template default: `otterdog-defaults` v0.13.1 sets
`code_scanning_default_setup_enabled: false`. Nothing in a downstream config
opts into it.

## Observed

- Org `exo-pet` — Team plan, all repositories private.
- Provisioning `exo-pet/data-analysis` (exo-pet/org-config#51), apply run
  [33379441586](https://github.com/exo-pet/org-config/actions/runs/33379441586):

  ```
  │ Error:   failed to apply patch: ADD - repository[name="data-analysis"]
  │          failed to update code scanning config for repo 'exo-pet/data-analysis':
  │          (status=403, body={"message":"Code Security must be enabled for this
  │          repository to use code scanning.", … })
  ```

- Live state after the failed run matched the plan **field for field** —
  merge settings, topics, description, `has_wiki`, `private`,
  `delete_branch_on_merge`, `dependabot_alerts_enabled`, `default_branch`. The
  only call skipped after the raise is `_update_default_branch`, a no-op here
  because `auto_init` already produced `main`.
- Immediate re-dispatch, run
  [33379694833](https://github.com/exo-pet/org-config/actions/runs/33379694833):
  **success**, as predicted.

## Impact

1. **Every new repo needs two apply dispatches.** In this engine `apply` is a
   deliberately gated, manually-dispatched, audited mutation (ADR-0006 — the
   human running it *is* the approval gate, since required reviewers need
   Enterprise on a private repo). Costing two attributable approvals per repo,
   one of them a scary red run, is a real workflow tax.
2. **A red run that is not a real failure.** The engine's own error text says
   "the mutation was partial or aborted — check the config, auth, or harness and
   re-run", which is exactly wrong here: nothing is partial. Anyone hitting this
   the first time will (correctly) stop and investigate before re-running.
3. **The apply tracker is left open.** The "Close the loop on the apply tracker"
   step is skipped on failure, so the tracker issue gets no closing comment for
   the run that actually did the work.
4. Hits **every** downstream org this engine serves that is below the Code
   Security bar — not specific to `exo-pet`.

## Why we do not fix this downstream

Three levers, all rejected:

- **Unset the setting.** Omitting `code_scanning_default_setup_enabled` from the
  vendored base template leaves it `UNSET`, which drops it from the provider
  data (`models/__init__.py:593`, `models/repository.py:1005-1009`; the schema
  requires only `name` and `private`), so the PATCH is never sent. But
  `otterdog/*/vendor/otterdog-defaults/` is a pinned mirror of
  `EclipseFdn/otterdog-defaults@v0.13.1` — editing it forks an upstream artefact
  that Renovate bumps, and it leaves code scanning unmanaged for every repo in
  every downstream org. Bad trade for a one-line upstream tolerance.
- **Retry inside the engine.** Detecting this error and re-running `apply`
  automatically would defeat the human gate and mask genuinely partial
  mutations. Not acceptable on a write path with medtech traceability
  requirements.
- **Patch otterdog post-install.** A monkeypatch or `sed` over the installed
  wheel in the workflow makes the tool that writes to live orgs no longer the
  audited pinned release. Worse than the bug.

## Interim

Document the two-dispatch reality: when an apply's *only* failure is
`failed to update code scanning config … 403 Code Security must be enabled`,
the repository was created correctly — verify live state against the plan, then
re-dispatch `apply` to converge and close the tracker.

Close this once eclipse-csi/otterdog#738 ships and the engine's otterdog pin
moves past it.

## Relationship to #107

Same family, different subsystem: #107 is the read-side plan gate that makes
repo rulesets undeclarable below Enterprise. Both are otterdog assuming a
capability tier that downstream orgs do not have; both are worked around rather
than fixed here.

