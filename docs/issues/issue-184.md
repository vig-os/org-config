---
type: issue
state: open
created: 2026-08-17T08:49:47Z
updated: 2026-08-17T08:49:47Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/184
comments: 0
labels: change-request
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-18T02:57:52.173Z
---

# [Issue 184]: [[CHANGE-REQUEST] sync-issues-action: dismiss stale reviews on Main protection](https://github.com/vig-os/org-config/issues/184)

### Target repo(s)

vig-os/sync-issues-action

### Setting area

Ruleset / branch protection

### Current behavior

`Main protection` for `sync-issues-action` (`otterdog/vig-os/vig-os.jsonnet:772-788`) sets `required_approving_review_count: 1` and `requires_code_owner_review: true` but does **not** set `dismisses_stale_reviews`, so it defaults to off. Verified against the live repo ruleset `Main protection` (id `13401788`): `dismiss_stale_reviews_on_push: false`. Config and live state agree; there is no drift.

Consequence: an approval of one commit survives every later push to the branch, so the review gate can be satisfied by a commit nobody reviewed.

### Desired change

Add `dismisses_stale_reviews: true` to the `required_pull_request` block at `otterdog/vig-os/vig-os.jsonnet:777-781`, carrying the same inline rationale devkit already records.

Everything else in the ruleset stays as-is — approval count 1, code-owner review, thread resolution, the `CI Summary` + `Dist Check` status checks, the `Signed commits` ruleset.

Explicitly **not** requested here:

- `requires_last_push_approval` — with a single maintainer this makes self-merge impossible without an admin bypass, trading a real gate for a routine override. devkit declined it for the same reason.
- `strict` (up-to-date branches) — `commit-action` carries it (`:276`) but it costs a CI re-run per merge whenever `main` moves; worth deciding separately rather than folding into this request.

### Justification

Straight convergence on an existing org decision. devkit's `Main protection` already sets `dismisses_stale_reviews: true` (`otterdog/vig-os/vig-os.jsonnet:386-396`) with the rationale written out under #118 — *"an approval must cover the code being merged: without this, a review of one commit survives every later push to the branch. Main only — Dev and Release require 0 approvals, so they have nothing to dismiss."* That reasoning applies unchanged to `sync-issues-action`, which likewise requires 1 approval on Main and 0 on Dev/Release. The two action repos should not differ here by accident.

Prompted by OpenSSF Scorecard alert [#15](https://github.com/vig-os/sync-issues-action/security/code-scanning/15) (`BranchProtectionID`) on `sync-issues-action`, which flags stale-review dismissal among four Main-branch warnings. Note this change alone will **not** close that alert — Scorecard also counts `required approving review count is 1`, `last push approval is disabled` and `up-to-date branches is disabled`, and the first two are deliberate given a solo maintainer. Expect an improved score with the alert still open; that is the intended outcome, not a partial failure.

Low risk: it can only ever require a re-approval that should have been required anyway, and `sync-issues-action` PRs are small and already gated on `CI Summary` + `Dist Check`.

### Urgency

Low — whenever capacity allows

### Additional context

- Precedent and rationale: #118 (devkit's `dismisses_stale_reviews`).
- Related shape: #167 (the inverse request on `devkit-smoke-test`) — same ruleset area, same plan/apply path.
- Incidental, **not** part of this request: `requires_code_owner_review: true` is currently inert on `sync-issues-action` because `.github/CODEOWNERS` in that repo has no uncommented rule, so no owner is ever matched. Not a security gap, but the flag does not do what it reads like it does. Worth a separate issue to either populate CODEOWNERS or drop the flag.
- The other open Scorecard finding on that repo (unpinned `curl | bash` of `install.sh` from `devkit@main` in the managed `devkit-upgrade.yml`) is filed upstream in vig-os/devkit and is not an org-config concern.

