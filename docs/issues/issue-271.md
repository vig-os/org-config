---
type: issue
state: open
created: 2026-09-25T20:28:24Z
updated: 2026-09-25T20:28:24Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/271
comments: 0
labels: chore, docs, priority:low, effort:small
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-26T07:11:50.488Z
---

# [Issue 271]: [The `vigos-devkit-upgrade` App is public with no recorded visibility decision — same posture as #261, no runbook anywhere](https://github.com/vig-os/org-config/issues/271)

## What's wrong

#261 establishes that a `vig-os`-owned App's **visibility** is a posture that must be decided and
recorded, and records one for the engine App. `vigos-devkit-upgrade` is in the same position and has
no such record anywhere: not in this repo, not in `vig-os/devkit`, not in an ADR.

Probed 2026-09-25, unauthenticated, no token:

```console
$ curl -s -o /dev/null -w '%{http_code}\n' https://api.github.com/apps/vigos-devkit-upgrade
200
$ curl -s https://api.github.com/apps/vigos-devkit-upgrade | jq '{id, owner: .owner.login, created_at, client_id, permissions, events}'
{
  "id": 4434545,
  "owner": "vig-os",
  "created_at": "2026-07-30T10:52:15Z",
  "client_id": "Iv23liye1EHNeAeynWsU",
  "permissions": {
    "contents": "write",
    "issues": "write",
    "metadata": "read",
    "pull_requests": "write",
    "workflows": "write"
  },
  "events": []
}
```

`200` anonymous is what a **public** App answers — the same discriminator #261 used, with the same
controls (three `vig-os`-owned Apps answer `404` anonymous: `vig-os-release-please`,
`tessera-sync-issues-bot`, `tessera-release-plz`). So the org does set some Apps private; this one
is public and nobody wrote down that it should be.

**Public is almost certainly required here, for the #261 reason.** The App is installed on a
**foreign org**: `gh api /orgs/exo-pet/installations` lists `4434545 vigos-devkit-upgrade` alongside
`vig-os`'s own (`gh api /orgs/vig-os/installations`). GitHub's private setting means *"it can only
be installed on the account that owns the app"* — so the `exo-pet` installation would be impossible
if it were private. That is a fact about the live topology, not a preference.

**Where it is documented today — nowhere as a decision.** The App exists only as: its credential
declarations in this repo (`otterdog/vig-os/vig-os.jsonnet:124-135` `DEVKIT_UPGRADE_APP_CLIENT_ID`
over seven `selected_repositories`, `:147-155` the legacy numeric form over four, and the private
key over the union), and the scaffolded workflow header that states the *grant* it needs
(`.github/workflows/devkit-upgrade.yml:18-24`, mirrored from
`vig-os/devkit:assets/workspace/.github/workflows/devkit-upgrade.yml:18-24`, pointing at
`vig-os/devkit#1302`). `grep -rn "Where can this GitHub App be installed\|Only on this account"` over
`vig-os/devkit` returns nothing — there is no creation runbook for this App at all.

## Why it matters

1. **Same exposure, no record.** A public App with `contents: write`, `workflows: write` and
   `pull_requests: write`, whose private key is an org secret reaching seven repositories, can be
   installed by any account that finds its install page. As with #261 the direction of harm is
   outbound — a stranger installing it gains nothing without the PEM, and `events: []` means there
   is no `installation` webhook, so the installation set is **unbounded, unmonitored and not
   enumerable from CI** (listing `GET /app/installations` needs a JWT signed with the key, which no
   workflow holds). That is exactly the cost #261 decided to accept *explicitly* for the engine App;
   here it is accepted implicitly.
2. **The #256 coupling does not apply, and that is worth stating.** `vigos-devkit-upgrade` is named
   as a ruleset bypass actor **nowhere** — `otterdog/vig-os/vig-os.jsonnet`'s fourteen
   `bypass_actors+` blocks name only `commit-action-bot` (×6), `vig-os-release-app` (×3),
   `#OrganizationAdmin` and `#RepositoryAdmin:pull_request`. #81 proposed exactly such a bypass and
   was closed as superseded by `vig-os/devkit#1308` ("fleet-wide Signed-commits bypasses are the
   wrong model — verified signatures are policy"; the interim bypass was reverted). So unlike
   `commit-action-bot` / `vig-os-release-app`, making this App private would not strand any ruleset
   — the only thing keeping it public is the `exo-pet` installation. Recording that distinction is
   half the value of the decision.
3. **#261 leaves an obvious gap otherwise.** Once the runbook says, for one App, "public, decided,
   here is what it costs", the next reader's question is what the other public `vig-os` App is, and
   the answer is silence.

## Suggested fix

1. **Take the same decision, in one line: public, because the `exo-pet` installation requires it.**
   With the same two accepted costs named (unbounded/unmonitored installation set; world-readable
   grant table), and the explicit note that the #256 bypass-actor coupling does **not** bind here.
2. **Pick a home and say so** — this App is `vig-os`-owned but scaffolded by `devkit`, so the
   decision has two plausible places:
   - *Here*, as a short comment beside the `DEVKIT_UPGRADE_APP_*` declarations in
     `otterdog/vig-os/vig-os.jsonnet` (which already carries a MAINTENANCE COUPLING comment) plus a
     cross-reference from `docs/runbooks/github-app.md`'s new **Visibility** section — cheapest, and
     keeps the two App postures readable side by side.
   - *In `vig-os/devkit`*, as the creation runbook that App has never had (grant, visibility,
     install targets, key rotation), mirroring `docs/runbooks/github-app.md`. More correct, larger,
     and a `devkit` issue rather than this one.
   Recommend the first now and the second as a follow-up if `devkit` ever needs to recreate the App.
3. **Add the same key-rotation inventory line** #261 adds for the engine App: at key rotation, list
   `GET /app/installations` with a JWT and confirm every installation is expected. It is the only
   moment that check is free, and it is the only compensating control for an unmonitored public
   install page.
4. Verification is a **UI checklist**, not an API call, for the reason #261 records: `GET
   /apps/{app_slug}` carries no visibility field, so the only API signal is the status code to an
   unauthenticated request. *Settings → Developer settings → GitHub Apps → vigos-devkit-upgrade →
   Advanced → "Where can this GitHub App be installed?"*, with the same trap — the Danger-zone
   button names the action, not the current state.

## Acceptance

- [ ] The live "Where can this GitHub App be installed?" value for `vigos-devkit-upgrade` is
      confirmed in the UI and recorded
- [ ] A decision is written down with its reason (the `exo-pet` installation) and its accepted costs
- [ ] The record states that this App is not a ruleset bypass actor, so its visibility is not
      load-bearing for `apply` the way `commit-action-bot` / `vig-os-release-app` are
- [ ] A key-rotation step exists that inventories `GET /app/installations` for this App

## Context

Out-of-scope finding from the #261 spike (§6.2), which probed every `vig-os`-owned App while
verifying the engine App's visibility. Filed here rather than on `vig-os/devkit` because this repo
holds the App's credential declarations and #261 sets the precedent for where App postures are
recorded; move it if the decision is to give the App its own `devkit` runbook. Related: #261 (the
engine App's visibility decision and the Visibility section it adds), #256 (the bypass-actor
readability coupling that does *not* bind here), #81 (the bypass proposal that was superseded),
#112 / #123 (the org secrets that feed this App), `vig-os/devkit#1302` (why the App exists).

