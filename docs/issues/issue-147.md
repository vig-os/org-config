---
type: issue
state: closed
created: 2026-08-10T12:29:36Z
updated: 2026-08-10T12:38:48Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/147
comments: 1
labels: none
assignees: c-vigo
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-11T03:46:55.075Z
---

# [Issue 147]: [Grant #OrganizationAdmin a permanent bypass on devkit-smoke-test Main protection](https://github.com/vig-os/org-config/issues/147)

## Problem

`devkit-smoke-test`'s `Main protection` ruleset (live id 13444875) declares no bypass actors, so an org admin has no sanctioned escape hatch on `main` — any operational unblock (e.g. around the smoke-release approval gate from vig-os/devkit#1391) requires an out-of-band `gh api PUT` that the next `otterdog apply` reverts.

## Proposal

Declare `'#OrganizationAdmin'` (always mode) in the ruleset's `bypass_actors`, matching the parity precedent: `devkit`'s own `Main protection` already carries exactly this bypass.

The 1-approval requirement stays for the normal path — the dispatch listener's final-release gate polls `reviewDecision` and is unaffected; the bypass only gives org admins a deliberate, audited override instead of ad-hoc API surgery.

## Notes

- This is a **ruleset modification with status checks**, i.e. the first real ruleset write since the otterdog 1.4.0 pin (#69 / #145) — it doubles as the pending end-to-end confirmation of the numeric-prefix write fix. Fallback if apply 404s: the documented manual-PUT interim.
---

# [Comment #1]() by [c-vigo]()

_Posted on August 10, 2026 at 12:38 PM_

Verified post-merge (apply run [31388666533](https://github.com/vig-os/org-config/actions/runs/31388666533), otterdog 1.4.0): the apply performed the `~ repo_ruleset` modification and exited 0 — no `GET /apps/15368` 404. Live readback of ruleset 13444875 shows `bypass_actors: [OrganizationAdmin/always]`, the check still `{"context": "CI Summary", "integration_id": 15368}`, and `required_approving_review_count: 1` untouched. This closes the loop on #69: the 1.4.0 numeric-prefix write fix is confirmed end-to-end, and the manual-PUT interim is retired as a fallback.

