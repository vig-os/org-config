---
type: issue
state: closed
created: 2026-09-25T12:38:30Z
updated: 2026-09-25T17:10:47Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/257
comments: 1
labels: bug, priority:high, area:docs, effort:small
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-26T07:11:54.981Z
---

# [Issue 257]: [App grant: Organization Members must be Read & write, or applying a declared team 403s](https://github.com/vig-os/org-config/issues/257)

## What's wrong

The App's grant table in `docs/runbooks/github-app.md` sets

| Organization | Members | Read | teams + team members — confirmed in #16 |

**Read is enough to plan a team and not enough to apply one.** A downstream org
that declares its first team gets a green plan and a failed apply:

```
+ add team[name="exopet"] { … }

Error: failed to apply patch: ADD - team[name="exopet"]
       failed to add team 'exopet': {"message":"Resource not accessible by integration",
       "documentation_url":"https://docs.github.com/rest/teams/teams#create-a-team",
       "status":"403"}
```

`POST /orgs/{org}/teams` requires organization **Members: Read & write**.
Observed on `exo-pet` 2026-09-25 (exo-pet/org-config#81, run 36119473230):
apply exited 1 with nothing mutated — a clean failure, not a partial one.
Granting Members write upstream and approving it on the installation made the
identical dispatch succeed.

## Why it was not caught

The permission table is the verified outcome of the **#16 spike**, which
enumerated the otterdog `import` / `plan --no-web-ui` **read** path and mapped
endpoint → permission. Teams are in that read path, so `Members: Read` is
correct *for reading*. The apply-side write was never exercised because no
downstream org had declared a team until now: `exo-pet` carried `teams: []`
from its initial import, precisely to avoid the base template's Eclipse teams.

So this is not a regression — it is a hole the spike's methodology could not
see, and the first org to declare a team falls into it.

## Why it matters more than one failed run

Otterdog models teams and team membership; the engine's reusable `apply`
workflow is built to reconcile them; the App the engine ships cannot create
one. Any downstream org that adds a team hits a 403 at apply, after a green
plan and a merge — the least helpful moment. The fix is a UI-only change to the
App plus a per-installation approval, neither of which is discoverable from the
error text.

## Suggested fix

1. `docs/runbooks/github-app.md` — change the Organization → Members row to
   **Read & write**, and say why in the same voice as the Custom-properties
   row below it (which records exactly this class of finding: a write level
   discovered by a live apply 403, granted, re-run green).
2. Note in the runbook that **existing installations must approve the widened
   permission** — an App-side change alone leaves every current install on the
   old set, so the next apply still 403s.
3. Consider whether the table should distinguish *read path* from *apply path*
   levels generally. Members is unlikely to be the only row where the #16
   methodology under-grants: it enumerated reads, and every row with a write
   level today was either obvious or found the same way this one was.

## Acceptance

- [ ] Runbook grants Organization → Members **Read & write**, with the reason
- [ ] Runbook states that existing installs must approve the widened permission
- [ ] A downstream org declaring its first team applies without a 403

---

# [Comment #1]() by [c-vigo]()

_Posted on September 25, 2026 at 05:10 PM_

Spike + review outcome, with one change of plan.

**Acceptance (c) is already green, on `exo-pet`.** `gh api /orgs/exo-pet/installations` shows
installation **147219320** at `members: write`, `repository_selection: all`, and the identical
dispatch that failed as run `36119473230` (2026-09-25T09:37:23Z, `POST /orgs/{org}/teams` ->
403) succeeded nine minutes later as run **36120273830** (09:46:03Z), with the team created.
So the criterion "a downstream org declaring its first team applies without a 403" is an
observation, not a prediction.

**`vig-os`'s own installation is deliberately left on `members: read`.** `gh api
/orgs/vig-os/installations` -> installation **147168870**, `members: read`. That gap is now a
decision rather than an omission:

- `vig-os` declares no teams (`otterdog/vig-os/vig-os.jsonnet:55` -> `teams: []`, and
  `gh api /orgs/vig-os/teams` returns an empty list), so nothing on this org can hit the
  failure.
- Organization **Members: write** is not a no-op on top of the Administration: write this App
  already holds. GitHub's permissions reference lists, under Members -> write, all accepting
  an installation access token: `PUT /orgs/{org}/memberships/{username}` (which sets `role`,
  including `admin`), `DELETE /orgs/{org}/members/{username}`, `POST /orgs/{org}/invitations`,
  and the two `outside_collaborators` calls. That is **owner promotion and member removal** —
  capabilities org Administration: write does not carry — for an App whose private key is an
  org secret consumed by a reusable `workflow_call`.
- The runbook's own rule is to widen only on proven need; the same spike invokes that rule to
  refuse three other widenings (below), so it applies here too.

The runbook wording in the PR therefore reads: *Read & write is required once an org declares
its first team; an org with `teams: []` keeps its installation on Read (least privilege)*,
with the escalation path spelled out — the App-level permission is already widened, and each
org's owner approves it on that installation when that org declares a team. `GET
/orgs/{org}/installations` is named as the cheap confirmation, since the `permissions` object
reported there, not the App's settings page, is what a token minted for that org can do.

**Three latent under-grants: documented, not fixed.** The audit behind this issue re-checked
every `providers/github/rest/*_client.py` write endpoint in otterdog 1.5.0 against GitHub's
permissions reference. The Members row was the one biting; three more rows are under-granted
for their apply path and are being written down rather than left to be rediscovered by the
next 403:

1. **Organization -> Custom properties is `Read & write`; writing a property *schema* needs
   `Admin`.** `PUT`/`DELETE /orgs/{org}/properties/schema/{name}`. Untriggered only because
   `vig-os`'s single `type` property already matches the config — the first org declaring a
   *new* org custom property fails exactly the way this issue's team did.
2. **Repository -> Contents is `Read`; renaming a branch needs `write`.** A `default_branch`
   pointed at a branch that does not exist yet makes otterdog rename the current default via
   `POST /repos/{org}/{repo}/branches/{branch}/rename`, which GitHub lists under Contents
   write. `_update_default_branch` is `rename_branch`'s only caller.
3. **There is no Repository -> Environments grant at all**, and environment *secrets* and
   *variables* need one (`…/environments/{env}/secrets`, `…/environments/{env}/variables`).
   This is masked, not safe: the pinned base template
   `otterdog-defaults@v0.13.1` (`otterdog.json:4`) exports no `newEnvSecret` / `newEnvVariable`
   constructor, so no such object can be declared today — which is why three declared
   environments (`copilot`, `github-pages`, `production`) work with no Environments grant. The
   pin is held for the unrelated `max_cache_size_gb` reason, so **a base-template bump that
   adds those constructors must add the permission in the same change.** The trip-wire goes on
   the pin comment as well as in the runbook, since that bump is the one with a scheduled
   trigger.

None of the three is granted in this PR — the same "widen only on proven need" rule, applied
consistently. Each becomes a one-line UI change plus a per-installation approval the day
something actually declares the object.

Docs-only PR to follow; no engine, workflow, config or table-semantics change.


