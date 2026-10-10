---
type: issue
state: open
created: 2026-10-09T13:05:33Z
updated: 2026-10-09T13:05:33Z
author: gerchowl
author_url: https://github.com/gerchowl
url: https://github.com/vig-os/org-config/issues/329
comments: 0
labels: none
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-10-10T08:12:36.100Z
---

# [Issue 329]: [chore(config): add @gerchowl as a production environment reviewer](https://github.com/vig-os/org-config/issues/329)

`production` (the human gate on every `apply`, ADR-0007) lists **only @c-vigo** as reviewer (`vig-os.jsonnet`), so an apply waits whenever c-vigo is unavailable. org owners can only *bypass* the gate (`can_admins_bypass`), not *approve* it. Example: the vigil declaration's apply (#328, run 37930104886) is held.

Proposal: add `@gerchowl` as a second required reviewer. GitHub needs **one** approval from any listed reviewer, so either maintainer can release an apply.

**Governance note for review:** with two reviewers and no `prevent_self_review`, one person can merge (owner bypass on `main`) and approve the apply of their own change, so there's no second pair of eyes. The alternative is to also enable *prevent self-review*, so the person who triggered a deployment (the merger) can't approve it. That keeps four eyes and still removes the single point of availability. Left as a decision for this review.

Note the chicken-and-egg: applying this change needs @c-vigo's approval once.
