---
type: issue
state: open
created: 2026-09-25T17:08:00Z
updated: 2026-09-25T20:29:29Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/261
comments: 1
labels: docs, security, priority:medium, area:docs, effort:small
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-26T07:11:52.985Z
---

# [Issue 261]: [The engine App is public — `/apps/vig-os-org-config` answers 200 unauthenticated — while the runbook says "Only on this account"](https://github.com/vig-os/org-config/issues/261)

## What's wrong

`docs/runbooks/github-app.md:43`, in **Create the App**, instructs:

> - **Where can this GitHub App be installed?**: **Only on this account** (`vig-os`-owned; installed
>   per org by an owner, not published to the Marketplace).

The live App does not match that. Probed 2026-09-25, unauthenticated, no token:

```
curl -s -o /dev/null -w '%{http_code}' https://api.github.com/apps/vig-os-org-config   -> 200
curl -s -o /dev/null -w '%{http_code}' https://api.github.com/apps/exopet-doc-issuer   -> 404
curl -s -o /dev/null -w '%{http_code}' https://api.github.com/apps/nonexistent-app-xyz -> 404
```

A `200` to an anonymous caller is what a **public** App answers; an App restricted to its
owning account is not readable that way (`exopet-doc-issuer`, `exo-pet`-owned, is the
control — `404` anonymous, `200` to an org-owner PAT). Independently: the App is installed
on `exo-pet` as well as `vig-os` (`gh api /orgs/exo-pet/installations` -> installation
`147219320`; `gh api /orgs/vig-os/installations` -> `147168870`), which "Only on this
account" would not allow.

So either the setting was changed after creation and the runbook was never updated, or it
was never set as written. Either way the runbook is not a description of the App.

## Why it matters

1. **The runbook is the App's only specification.** `docs/runbooks/github-app.md` is what a
   rebuild or a second engine App would be created from, and it is the file the permission
   audit in #257 treats as authoritative. A creation step that contradicts the live App
   silently invalidates that status.
2. **"Public" is a real posture, not a formality.** A public App is installable by any
   account that finds its install page and has a discoverable slug; the private key is an
   org secret consumed by a reusable `workflow_call` workflow, and the App holds
   Organization → Administration: Read & write on every org that installs it. Whether that
   is acceptable is a decision, and right now nobody has made it on the record.
3. **It interacts with #256.** An App's readability on `GET /apps/{slug}` is exactly what
   decides whether otterdog's write path can resolve it as a ruleset bypass actor under an
   installation token. Flipping `vig-os-org-config` to "Only on this account" would be
   inert for *this* App (it is never itself a bypass actor), but the same reasoning makes
   the public status of `commit-action-bot` and `vig-os-release-app` **load-bearing**: ten
   rulesets in `otterdog/vig-os/vig-os.jsonnet` name them as bypass actors, and making
   either App private would make those ten rulesets unrepairable by `apply` (403 on
   `GET /apps/{slug}`), with a green plan and no warning. That coupling is currently
   written down nowhere.

## Suggested fix

1. **Verify** the live setting in the UI — *Settings -> Developer settings -> GitHub Apps
   -> vig-os-org-config -> Advanced/"Where can this GitHub App be installed?"*. The API
   probe above is strong evidence but the UI is the authority.
2. **Decide**, on the record, public vs "Only on this account":
   - *Public* is the status quo and is what multi-org onboarding (`exo-pet`, and any future
     `exoma-ch` / `MorePET` install) actually uses.
   - *Only on this account* would mean every additional org install goes through a transfer
     or a second App, and it would remove the anonymous readability of the slug.
3. **Correct the runbook either way** — the creation step, and a one-line note saying which
   posture was chosen and why. If the decision is "public", the note should also record the
   #256 coupling above: an App named as a ruleset bypass actor must stay readable, so its
   visibility is a configuration-relevant setting, not cosmetic.
4. Optional, if the decision is "this must not drift again": a row in
   `unmanaged-controls.toml` asserting the App's own shape. Otterdog models no App, so this
   is squarely the controls table's territory — it is the same argument `exo-pet`'s
   `commit-app-permissions` row already makes for `commit-action-bot`.

## Acceptance

- [ ] The live "Where can this GitHub App be installed?" value is confirmed in the UI and
      recorded in the issue
- [ ] A decision is taken and written down (public, or restricted)
- [ ] `docs/runbooks/github-app.md` matches the live App, with the reason
- [ ] The #256 coupling (a bypass-actor App must remain readable on `GET /apps/{slug}`) is
      recorded wherever the decision lands

## Context

Found while reviewing the #257 permission audit, which re-derives every row of the App's
grant table against GitHub's permissions reference but takes the creation steps as given.
Related: #256 (App readability decides whether `apply` can write an App bypass actor), #16
(the original read-path permission spike), ADR-0004 (the App auth model).

---

# [Comment #1]() by [c-vigo]()

_Posted on September 25, 2026 at 08:29 PM_

## Recommendation: keep it public, and record why

Two facts decide it, and neither is a preference.

**1. "Only on this account" is not compatible with the live installation set.** GitHub documents the
private setting as: the App *"can only be installed on the account that owns the app"*
([Making a GitHub App public or private](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/making-a-github-app-public-or-private)).
The App is installed on `exo-pet` (installation `147219320`) as well as on `vig-os` (`147168870`) —
so the runbook's creation step describes a configuration under which the only downstream org that
exists could not have been onboarded. That also settles the ADR-0004 tie-in: "One App, not four" is
*structurally* dependent on the App being public, and `exoma-ch` / `MorePET` are meant to follow
`exo-pet` through the same install page the runbook already points them at
(`docs/runbooks/github-app.md:254-255`).

**2. Going private would hide nothing.** The steelman for restricting it is that the anonymous
`GET /apps/{slug}` payload exposes something. It does not, in the sense that matters: that payload
is already public and carries the Client ID **and** the entire 17-entry grant —

```console
$ curl -s https://api.github.com/apps/vig-os-org-config | jq '{client_id, permissions}'
{ "client_id": "Iv23liFmoQq21Vex9JUi",
  "permissions": { "administration": "write", "organization_administration": "write", … } }
```

— and a Client ID mints nothing without the PEM. So the flip would cost the multi-org model and buy
no confidentiality. The residual risk is the right one to name and it is not a compromise vector:
`events: []` means no `installation` webhook, and `GET /app/installations` needs a JWT the CI
credential never holds, so the set of accounts that have installed the App is **unbounded,
unmonitored and un-enumerable from CI**. The harm direction is outbound (a key leak would let an
attacker mint admin tokens *for* orgs that installed it), which is a liability argument answered by
the key-rotation sweep step, not by visibility.

One caveat worth carrying into the decision text: there are third-party reports that GitHub refuses
a public→private flip while installations on foreign accounts exist. Unverified — and it only
strengthens "keep public", since it would mean the flip is not freely reversible.

## Acceptance 1 is still open — it is a UI check, deliberately

The API cannot answer this: `GET /apps/{app_slug}` carries **no visibility field**, so the only
signal is the status code to an *unauthenticated* call, which no authenticated transport (the
controls table included) can ever observe. So no `unmanaged-controls.toml` row; verification stays a
plain UI checklist:

> Settings → Developer settings → GitHub Apps → `vig-os-org-config` → Advanced →
> "Where can this GitHub App be installed?"

with the trap that the Danger-zone button names the **action**, not the current state. Pending
@c-vigo.

## Docs PR to follow

Prepared, docs-only: the creation step changes to **Any account**, a new **Visibility** section
carries the decision, what the setting controls per GitHub's reference, and the two accepted costs;
**Key rotation** gains the `GET /app/installations` inventory step; the #256 coupling is recorded
with its scope corrected — an App named as a ruleset **bypass actor** must stay readable on
`GET /apps/{slug}` or `apply` can no longer repair that ruleset, but `vig-os-org-config` is a bypass
actor in neither org's config, so the Apps for which public is load-bearing are `commit-action-bot`
and `vig-os-release-app`.

Two out-of-scope findings from the same spike are now filed separately: #270 (the Client ID is
stored as an Actions secret although the value is world-readable — decide secret vs variable) and
#271 (`vigos-devkit-upgrade` is public with no recorded decision either, and unlike the two above it
is a bypass actor nowhere, so its public status is required only by its `exo-pet` installation).


