---
type: issue
state: open
created: 2026-08-21T14:20:53Z
updated: 2026-08-21T14:20:53Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/187
comments: 0
labels: change-request
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-22T02:56:12.495Z
---

# [Issue 187]: [[CHANGE-REQUEST] drop inert requires_code_owner_review on sync-issues-action and devkit-smoke-test](https://github.com/vig-os/org-config/issues/187)

### Target repo(s)

vig-os/sync-issues-action, vig-os/devkit-smoke-test

### Setting area

Ruleset / branch protection

### Current behavior

`requires_code_owner_review: true` is set at three sites in `otterdog/vig-os/vig-os.jsonnet` (line refs as of `7249220`):

- `sync-issues-action` › `Dev protection` (`:763`)
- `sync-issues-action` › `Main protection` (`:779`; shifts +5 once #186 merges)
- `devkit-smoke-test` › `Dev protection` (`:481`)

In **both** repos, `.github/CODEOWNERS` is the devkit-seeded stub: every line blank or `#`-commented, the only rule line being `#*                               @username`. With no uncommented rule, no owner ever matches, so the flag silently no-ops on every PR. Verified live on `sync-issues-action` Main ruleset `13401788`: `require_code_owner_review: true`, yet no review has ever been demanded by it.

Not a security gap — the 1-approval gate on Main is independent — but the flag reads like a control and does nothing, which is worse than its absence.

**Out of scope:** `org-config`'s own `Main protection` flag (`:602`) stays — its `CODEOWNERS` has 7 uncommented rules, so the gate is functional there.

### Desired change

Set `requires_code_owner_review: false` at the three sites (matching devkit's explicit-false style at `:396`), with a short rationale comment at each repo citing #115.

### Justification

Org precedent #115: devkit dropped the same flag because with a single maintainer who authors the PRs, a *populated* CODEOWNERS makes the gate unsatisfiable — you cannot code-owner-approve your own PR — so its only outcome is a routine `#OrganizationAdmin` bypass. The alternative resolution here (populating the CODEOWNERS stubs) would recreate exactly that problem, and on `sync-issues-action` would activate it on Dev and Main simultaneously. Explicit `false` records the decision instead of leaving a flag that lies about what it does.

### Urgency

Low — whenever capacity allows

### Additional context

Found during the #184 evaluation (implemented in PR #186); flagged there as an incidental, split out per single-issue scope. Related: #115 (devkit precedent), #184.
