---
type: issue
state: closed
created: 2026-08-22T08:54:06Z
updated: 2026-08-22T09:00:39Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/195
comments: 0
labels: change-request
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-22T09:25:34.188Z
---

# [Issue 195]: [[CHANGE-REQUEST] org-config: drop the unsatisfiable Main-protection approval gate (count 0, code-owner off)](https://github.com/vig-os/org-config/issues/195)

## Problem

`org-config`'s own `Main protection` ruleset requires 1 approving review plus code-owner review. The repo is solo-maintained: every self-authored PR is structurally unable to satisfy the gate (an author cannot approve their own PR, and the CODEOWNERS owner is the author), so its only outcome is a routine `#OrganizationAdmin` bypass on every merge. A control that is always bypassed is worse than its absence — it muddies the audit trail and normalizes bypassing, the exact pathology #115 diagnosed on devkit and #167 resolved on devkit-smoke-test with count-0-plus-required-checks.

## Why count 0 is safe here

The PR approval is not this repo's operative control:

- Every live mutation still stops at the `production` environment gate (reviewer `@c-vigo`, `main`-only branch policy) with the exact-tree plan preview one click from the approve button — a human approval per apply, regardless of how the PR merged.
- `CI Summary` remains a required status check on Main; the bypass-free `Signed commits` ruleset is untouched.
- Precedent: devkit's own Dev and Release protections and devkit-smoke-test's Main (#167) are count 0 with required checks for the same reason.

Accepted trade-off, explicitly: bot-authored PRs (Renovate, release-train) currently *can* be approved and so the count-1 gate does bind there; at count 0 they may merge on green CI without review. The blast radius is a merged commit, not an applied one — nothing reaches the live org without the environment approval.

## Change

In `otterdog/vig-os/vig-os.jsonnet`, `org-config` › `Main protection` (`required_pull_request+` block, ~:601-605):

- `required_approving_review_count: 1` → `0`
- `requires_code_owner_review: true` → `false` — the CODEOWNERS gate is functional (7 active rules) but equally unsatisfiable solo, and meaningless once reviews are not required; explicit `false` with rationale, matching devkit's style (#115)

Keep: `requires_review_thread_resolution: true` (still binds when threads exist), the required `CI Summary` check, `bypass_actors` (now rarely needed, harmless), and the `Signed commits` ruleset.

Out of scope: every other repo's rulesets (devkit deliberately keeps count 1 — its bot-authored release PRs make the gate satisfiable and worth keeping).

## Acceptance criteria

- Plan preview on the PR shows exactly the two ruleset field changes.
- Post-merge apply: live `Main protection` ruleset on `vig-os/org-config` reads `required_approving_review_count: 0`, `require_code_owner_review: false`.
- Next self-authored PR merges without an admin bypass once CI is green and threads are resolved.

Urgency: low — friction removal, not a functional break.

Provenance: raised during the 2026-08-22 backlog sweep (#187/#188/#191/#176), same single-maintainer-gate lineage as #115/#167/#187.

