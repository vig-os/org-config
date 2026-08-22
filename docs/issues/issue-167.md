---
type: issue
state: closed
created: 2026-08-14T07:35:24Z
updated: 2026-08-14T07:42:26Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/167
comments: 0
labels: change-request
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-14T08:59:21.427Z
---

# [Issue 167]: [[CHANGE-REQUEST] devkit-smoke-test: drop the human-review requirement on Main protection](https://github.com/vig-os/org-config/issues/167)

### Target repo(s)

vig-os/devkit-smoke-test

### Setting area

Ruleset / branch protection

### Current behavior

`Main protection` sets `required_approving_review_count: 1` (`otterdog/vig-os/vig-os.jsonnet:506`), with the inline comment at :502-505 recording the vig-os/devkit#1391 rationale: a human must approve the smoke release PR because workflow-token approvals are blocked org-wide and the dispatch listener's final-release gate polls `reviewDecision`, which GitHub only computes when reviews are required.

### Desired change

`required_approving_review_count: 0`, with the comment rewritten to record the new rationale: the repo is entirely bot-authored release-validation scaffolding; the listener's approval gate is removed in devkit (vig-os/devkit#1506), so `reviewDecision` no longer needs to be computable; the operative controls are the required `15368:CI Summary` status check and devkit's published-smoke-release validation at promote. Everything else in the ruleset is unchanged — PR required, status checks, thread resolution, Signed commits ruleset, `#OrganizationAdmin` bypass. Count-0-with-required-checks is the established pattern on devkit's own Dev and Release protections.

### Justification

Part of the single-approval release train (vig-os/devkit#1504): removes the only remaining human interaction in the smoke leg, which vig-os/devkit#1391 introduced as a workaround rather than a control. Exposure is negligible — only the maintainer and org Apps have write access, and the repo ships nothing.

**Sequencing constraint:** must be applied together with the devkit-side listener change (vig-os/devkit#1506), both before the next release train — see that issue's invariants. Apply note: this ruleset carries a numeric `15368:` status-check prefix, the write-path class fixed by the otterdog 1.4.0 pin (#69), so a normal plan/apply cycle is expected to work; the mutation pauses in the reviewer-gated `production` environment as usual.

### Urgency

Medium — this milestone

### Additional context

Related: vig-os/devkit#1391, vig-os/devkit#438, vig-os/devkit#1504, vig-os/devkit#1506; #118 (unaffected — devkit's `dismisses_stale_reviews` stays), #147 (out-of-band PUT caveat).

