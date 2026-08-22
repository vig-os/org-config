---
type: issue
state: closed
created: 2026-07-17T09:02:11Z
updated: 2026-08-07T08:16:55Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/6
comments: 1
labels: chore, security, priority:blocking, effort:small
assignees: c-vigo
milestone: M0 — Prerequisites & self-protection
projects: none
parent: none
children: none
synced: 2026-08-08T03:28:26.150Z
---

# [Issue 6]: [Upgrade exo-pet organization to GitHub Team](https://github.com/vig-os/org-config/issues/6)

**Human step (@c-vigo) — billing.** exo-pet (medtech, 8/9 repos private) has no enforceable branch protection anywhere: rulesets/branch protection on Free private repos return HTTP 403 (verified 2026-07-06, re-verified 2026-07-17). Free orgs cannot create org-level rulesets at all.

- [ ] Upgrade exo-pet to GitHub Team (3 seats, ~$4/user/mo)
- [ ] Verify: ruleset creation on a private exo-pet repo no longer 403s

Gates M4 (the private `exo-pet/org-config` repo must be protectable before it holds apply credentials). Does not block M1–M3. The decision ADR belongs in exo-pet's own records and is cross-referenced from here.

Part of #1 (M0).

---

# [Comment #1]() by [c-vigo]()

_Posted on August 7, 2026 at 08:16 AM_

Verified completed on 2026-08-07.

Evidence — \`gh api orgs/exo-pet --jq '{plan: .plan.name, seats: .plan.filled_seats}'\`:

```json
{"plan":"team","seats":4}
```

The exo-pet organization is on the GitHub Team plan (4 filled seats), so branch protection / rulesets on private repos are no longer blocked by the Free-plan 403. M4 is unblocked.

