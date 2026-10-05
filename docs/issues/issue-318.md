---
type: issue
state: closed
created: 2026-10-04T13:47:08Z
updated: 2026-10-04T21:52:35Z
author: gerchowl
author_url: https://github.com/gerchowl
url: https://github.com/vig-os/org-config/issues/318
comments: 1
labels: none
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-10-05T08:44:33.397Z
---

# [Issue 318]: [apply does not reconcile org-secret selected_repositories — revkit declared since #312 is still not granted](https://github.com/vig-os/org-config/issues/318)

## Summary

`otterdog apply` does not reconcile `selected_repositories` for the nine org secrets whose
declared value is a `'********'` dummy. The declaration in `otterdog/vig-os/vig-os.jsonnet` is
documentation; the live grant has to be made out-of-band. Nothing surfaces the divergence — not
the plan, not drift, not the tests.

## Evidence

`revkit` was added to six secret lists in `63420ca` ("grant revkit the App org secrets scitadel
has"), merged as #312 on 2026-09-29. `apply-engine.yml` ran **successfully for that exact commit**
at 2026-09-29T20:59, and twice more since (2026-09-30T16:42, 2026-10-01T14:09).

Live state as of 2026-10-04 — `revkit` is absent from all six:

| secret | declared but not live | live but not declared |
| --- | --- | --- |
| `COMMIT_APP_CLIENT_ID` | `revkit` | — |
| `COMMIT_APP_PRIVATE_KEY` | `revkit` | — |
| `DEVKIT_UPGRADE_APP_CLIENT_ID` | `revkit` | — |
| `DEVKIT_UPGRADE_APP_PRIVATE_KEY` | `revkit` | — |
| `RELEASE_APP_CLIENT_ID` | `revkit` | — |
| `RELEASE_APP_PRIVATE_KEY` | `revkit` | — |

Reproduce:

```sh
gh api /orgs/vig-os/actions/secrets/COMMIT_APP_CLIENT_ID/repositories \
  --jq '[.repositories[].name]|sort'
```

Three successful applies over five days did not add it. This is not "apply has not run yet".

## Probable cause

Already written down in the config, at `ORG_CONFIG_CANARY`: its value is a real
credential-provider reference "rather than a `'********'` dummy, so `include_for_live_patch` is
true and apply can set visibility declaratively (secret.py:88)". The other nine carry dummies, so
their live patch is skipped. The `DEVKIT_UPGRADE_APP_ID` comment's remark that the list "is
editable without the secret value via `PUT /orgs/vig-os/actions/secrets/<NAME>/repositories`
(#123)" then reads as an out-of-band instruction, not something apply does.

## Impact

A repo added to these lists believes it has credentials and does not. Its scaffolded
`sync-issues.yml`, `devkit-upgrade.yml` and release-train workflows fail with an **empty
credential and no error message** — the failure mode the `DEVKIT_UPGRADE_APP_ID` comment already
warns about for the wrong-ID-form case.

Currently affected: `revkit` (since 2026-09-29) and `stepv` (on merge of #317).

## Options

1. **Close the loop in CI.** A read-only check in `plan.yml` that diffs each declared
   `selected_repositories` against `GET /orgs/{org}/actions/secrets/{name}/repositories` and
   reports it in the plan comment — the same shape as the existing "Declared App slugs" section,
   which exists for exactly this class of problem (config green on review, wrong on apply, #259).
   This is the cheapest fix and it makes the gap impossible to miss again.
2. **Teach apply to patch the list.** The endpoint takes no secret value, so a dummy-valued secret
   could still have its repository list reconciled. Upstream otterdog change.
3. **Document and accept.** Add the manual PUT to the repo-onboarding runbook. Weakest option —
   it is the status quo that produced this issue.

## Immediate remediation

**Done 2026-10-04 (by hand).** Live check: `revkit` and `stepv` are both on all six
`*_APP_CLIENT_ID` / `*_APP_PRIVATE_KEY` reader lists.

```sh
for s in COMMIT_APP_CLIENT_ID COMMIT_APP_PRIVATE_KEY DEVKIT_UPGRADE_APP_CLIENT_ID \
         DEVKIT_UPGRADE_APP_PRIVATE_KEY RELEASE_APP_CLIENT_ID RELEASE_APP_PRIVATE_KEY; do
  gh api /orgs/vig-os/actions/secrets/$s/repositories --jq '[.repositories[].name]|sort'
done
```

What #313 still flagged afterwards was the opposite direction: config declared `revkit` on the
numeric `COMMIT_APP_ID` / `RELEASE_APP_ID`, but live did not grant them. Those two declarations get
**removed** rather than granted. revkit's devkit 1.17.0 scaffold reads only the client ID, and #315
retires the numeric secrets, so a new reader would just add another blocker there.

## Still open

The structural gap, choosing between options 1–3 above. The manual PUT has now been needed for every
new repo (revkit, stepv); option 1 would make the next miss show up in the plan comment instead
of in a drift issue days later.

---

# [Comment #1]() by [gerchowl]()

_Posted on October 4, 2026 at 01:57 PM_

Broader AX context in #319 §5 — this is the same shape as the App-slug problem #259 already solved (config green on review, wrong on apply), which is the argument for option 1 here: extend the plan comment rather than only documenting the manual PUT.

