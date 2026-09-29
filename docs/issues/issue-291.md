---
type: issue
state: closed
created: 2026-09-28T09:57:52Z
updated: 2026-09-28T14:29:02Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/291
comments: 0
labels: chore, docs, priority:low, effort:small
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-29T08:00:44.307Z
---

# [Issue 291]: [The `vigos-devkit-upgrade` App is verified public in the UI, and its flip to private is blocked by two foreign installations, not one](https://github.com/vig-os/org-config/issues/291)

## Description

#271 recorded the `vigos-devkit-upgrade` visibility decision — public, *Any account* — explicitly
**"pending the UI verification below"**, because `GET /apps/{app_slug}` carries no visibility field
and the only API signal was the status code to an anonymous caller. That hedge is now wrong in both
directions: the verification has been done, and what it found is more than a confirmation.

**The reading (2026-09-28).** An owner of the `vig-os` organization opened *Settings → Developer
settings → GitHub Apps → `vigos-devkit-upgrade` → Advanced* and read, under **Danger zone**, three
controls in this order:

1. "Transfer ownership of this GitHub App"
2. "Delete this GitHub App"
3. **"Make this GitHub App private"** — **greyed out**, subtitled *"Private GitHub Apps cannot be
   installed on other accounts."*

Identical in text, order and disabled state to what #261 read on the engine App the same day. The
button names the *action*, so the live value is **public** — what the anonymous `200` predicted
(re-probed 2026-09-28: `curl -s -o /dev/null -w '%{http_code}' https://api.github.com/apps/vigos-devkit-upgrade`
→ `200`). Second agreeing reading of that mapping, on a second App; still corroboration and not the
contract GitHub declines to publish.

**The finding: this App's flip is blocked harder than the engine App's.** GitHub states the rule —
*"Public apps cannot be made private if they're installed on other accounts"* ([Modifying a GitHub
App registration](https://docs.github.com/en/apps/maintaining-github-apps/modifying-a-github-app-registration#changing-the-visibility-of-a-github-app),
*Changing the visibility of a GitHub App*) — and the disabled control is that rule enforced in the
product. Re-verified 2026-09-28 with `gh api /orgs/<org>/installations` across all four orgs:

| Org | `vigos-devkit-upgrade` installation | Created |
|-----|-------------------------------------|---------|
| `vig-os` (owner) | `150058891` | 2026-07-30T12:53:44+02:00 |
| `exo-pet` | `151387251` | 2026-08-05T09:28:31+02:00 |
| `exoma-ch` | `162764177` | 2026-09-18T15:53:42+02:00 |
| `MorePET` | none | — |

So **two** foreign installations, against the engine App's one (`exo-pet` `147219320`). Unblocking
the button would take devkit-upgrade automation offline in **two** orgs, sequentially, not one —
uninstall from `exo-pet` and `exoma-ch`, flip on `vig-os`, then re-onboard both.

**The `exoma-ch` installation is itself missing from the record.** The `APP VISIBILITY DECISION`
comment names `exo-pet` `151387251` as *the* foreign installation and argues the posture from it in
the singular. `exoma-ch` had been installed for ten days when that comment was written, so the
argument is sound but the evidence under it is short by one org — and the cost of a flip is
understated by a whole org.

## Documentation Type

Fix incorrect or outdated content

## Target Files

- `otterdog/vig-os/vig-os.jsonnet` — the `APP VISIBILITY DECISION` comment above the
  `DEVKIT_UPGRADE_APP_*` declarations (`:115-181`):
  - `:115-116` — drop "pending the UI verification below"; record the reading, its date, who took it
    and the three Danger-zone control texts in the order seen.
  - `:168` — "VERIFICATION IS UI-ONLY, **and still owed**" is no longer true. Keep the
    observation-vs-contract split and the "button names the ACTION, not the state" trap; add that
    the button is **disabled** and is to be read anyway.
  - the foreign-installation paragraph — name **both** `exo-pet` `151387251` and `exoma-ch`
    `162764177` with their dates, and state that the flip is uninstall-gated in two orgs with
    downstream automation stopping in each.
- `docs/runbooks/github-app.md:259-261` — the grant-table bullet in **Visibility** still reads
  "**also public, also pending its UI verification**". Past-tense it and point at the (then
  verified) jsonnet comment; the last clause of the #290 CHANGELOG bullet, "its 'pending its UI
  verification' hedge stands", stops being true the moment this lands.
- `CHANGELOG.md` — one **new** bullet under `## Unreleased` → `### Changed`. Do not rewrite the
  existing #271 bullet; #290 set the precedent of recording a later reading as its own entry.

Not a generated file, so no `just docs` run is implied.

## Related Code Changes

- #271 (CLOSED, shipped as #286) — the decision whose hedge this removes.
- #261 / #290 (MERGED, `17b1e33`) — **the pattern to follow.** #290 did exactly this shape of edit
  for the engine App: past-tense the decision with the reading and its date, add the uninstall
  precondition to the flip checklist, replace "GitHub's documentation does not say whether this is
  possible at all" with the documented answer, and tell the next reader to expect a disabled button.
  Reuse its reasoning by reference rather than restating it.
- #290 already added the `[app-modify]` link reference at `docs/runbooks/github-app.md:328`.
  **Reuse it — do not add a second one**; `pymarkdown` will flag a duplicate.
- #270 (CLOSED) — the Client-ID-stays-a-secret decision the jsonnet comment already cites.
- #256 — the bypass-actor coupling that still does **not** bind to this App. Unchanged here.
- `vig-os/devkit#1739` — the `devkit`-side creation runbook for this App. Still out of scope.

## Acceptance Criteria

- [ ] The `APP VISIBILITY DECISION` comment reads as a verified value, not a hedge: date, who read
      it, and the three Danger-zone control texts as seen
- [ ] "VERIFICATION IS UI-ONLY, and still owed" no longer claims the check is owed, and the next
      reader is told the button is greyed out and to read it regardless
- [ ] Both foreign installations are recorded with ids and dates (`exo-pet` `151387251`,
      `exoma-ch` `162764177`), and `MorePET` is recorded as carrying none
- [ ] The flip is recorded as uninstall-gated in **two** orgs, with the automation outage in each
      named as a precondition to the button being clickable at all
- [ ] `docs/runbooks/github-app.md:259-261` no longer calls this App's verification pending
- [ ] The observation-vs-contract split survives: the documented constraint is quoted **as
      documented**, the greyed-out button is corroboration, and the anonymous-`200` mapping stays an
      observation now carrying a second agreeing reading
- [ ] One new `### Changed` bullet in `## Unreleased`; the #271 bullet is left alone
- [ ] `just precommit` green (`pymarkdown`, `typos`) and `otterdog validate` succeeds
- [ ] No live setting is touched — no flip is proposed or performed

## Changelog Category

Changed

## Additional Context

**Sequencing.** This was deliberately held back while #290 was open, because both changes touch the
same runbook hunk (**Visibility**) and the same `## Unreleased` → `### Changed` block. #290 has
since merged (`17b1e33`), so the conflict is gone — but the implementation must branch from a `main`
that contains it, and `docs/runbooks/github-app.md:259-261` must be read in its post-#290 form, not
the form #286 left.

**No `unmanaged-controls.toml` row can assert any of this**, and the jsonnet comment already records
why: the only signal that discriminates public from private is the status code to an
*unauthenticated* call, and the controls transport reads authenticated, so it never sees the
discriminator. Verification stays a UI checklist by necessity, not by preference. The same holds for
the disabled state of the button — there is no API surface for it at all.

**Nothing about the live posture changes here** — no setting is touched, no exposure moves, no
permission changes. That is why this is `### Changed` and not `### Security`; per the section's own
rule, a `### Security` entry marks an actual posture flip. Today's precedent across #287, #289 and
#290 is the same.

