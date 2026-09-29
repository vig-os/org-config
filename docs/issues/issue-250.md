---
type: issue
state: closed
created: 2026-09-24T06:29:31Z
updated: 2026-09-24T07:01:24Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/250
comments: 1
labels: chore, priority:low, area:ci, effort:small
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-24T07:21:49.081Z
---

# [Issue 250]: [[CHORE] Renovate custom manager for the ADR-0005 otterdog pin, with a review request before merge](https://github.com/vig-os/org-config/issues/250)

### Chore Type

Configuration change

### Description

The ADR-0005 otterdog pin is bumped entirely by hand across **five** literals, and
nothing in Renovate matches any of them. `renovate.json` sets
`enabledManagers: ["github-actions", "pep621", "npm"]` and defines no
`customManagers`, so:

- `justfile.project:32` — `otterdog_version := "1.5.0"` — a bare Just variable no
  manager extracts;
- `.github/workflows/{plan,apply,drift}.yml` — the `workflow_call` input
  `default: '1.5.0'` — the `github-actions` manager extracts `uses:` refs and
  container images only, never an input default;
- `template/.github/workflows/import.yml` — `default: "1.5.0"` — same.

This is already recorded as a dated correction in ADR-0005 (`## Corrections`,
2026-09-23, #225), which retired the ADR's original "Renovate owns the pin"
claim after the 1.5.0 bump had to be authored by hand — and after the 1.4.0 bump
(`818e1f8`) missed `import.yml` entirely (#164 item 7).

Add a `custom.regex` manager that covers all five literals. Renovate raises a
normal PR — visible, with its own `otterdog plan` run — and that PR **waits for
an explicit review before merging**: it requests review from the maintainer and
never automerges. The mechanism does the error-prone part (editing five files in
lockstep); the human keeps the decision.

Concrete trigger: the pin is at **1.5.0** and otterdog **1.6.0** shipped
2026-09-23, so the first thing this manager surfaces is that bump.

### Acceptance Criteria

- [ ] `renovate.json` adds `"custom.regex"` to `enabledManagers` and a
      `customManagers` entry matching all five pin literals, with
      `datasourceTemplate: "pypi"`, `depNameTemplate: "otterdog"`,
      `versioningTemplate: "pep440"`.
- [ ] A `packageRules` entry matching that manager sets `reviewers: ["c-vigo"]`
      and an explicit `automerge: false`, so the PR opens normally, lands in the
      maintainer's review queue, and merges only on a deliberate click. Consider
      `addLabels: ["area:ci"]` for visibility and whether this rule should opt
      out of the repo-wide `before 9am on monday` schedule (a pin bump otherwise
      waits up to a week).
- [ ] The regex is **validated, not assumed**: `renovate-config-validator` passes
      and a dry run (or the dashboard's "Detected Dependencies" section after the
      next run) shows exactly five `otterdog` occurrences — no more, no fewer.
- [ ] `tests/test_otterdog_pin.py` still passes unchanged; a deliberately partial
      edit still fails it (the guard is what makes a regex miss safe).
- [ ] ADR-0005 gets a **new** dated `## Corrections` entry: the 2026-09-23 (#225)
      entry states the bump is "a deliberate authored change", which this issue
      partially reverses — the *edit* becomes mechanical, the *decision* stays
      manual. Do not rewrite the existing entry.
- [ ] Prose that asserts the pin is hand-bumped is reconciled: the
      `justfile.project` comment block above the pin (lines ~18-27, "Bumped BY
      HAND (#225)") and the `otterdog_version` input descriptions in
      `.github/workflows/{plan,apply,drift}.yml` that reference the same history.
- [ ] `CHANGELOG.md` `## Unreleased` entry under **Changed**.

### Implementation Notes

Starting point for `renovate.json` (shapes verified against the live files):

```json
"enabledManagers": ["github-actions", "pep621", "npm", "custom.regex"],
"customManagers": [
  {
    "customType": "regex",
    "description": "ADR-0005 otterdog pin: justfile.project SSoT plus its four in-repo mirrors (#228). Guarded by tests/test_otterdog_pin.py.",
    "managerFilePatterns": [
      "/^justfile\\.project$/",
      "/^\\.github/workflows/(plan|apply|drift)\\.yml$/",
      "/^template/\\.github/workflows/import\\.yml$/"
    ],
    "matchStrings": [
      "otterdog_version\\s*:=\\s*\"(?<currentValue>[^\"]+)\"",
      "(?m)^\\s+otterdog_version:\\s*$[\\s\\S]*?^\\s+default:\\s*['\"](?<currentValue>[^'\"]+)['\"]"
    ],
    "depNameTemplate": "otterdog",
    "datasourceTemplate": "pypi",
    "versioningTemplate": "pep440"
  }
]
```

**The second `matchString` is the risky half and must be validated.** Those
workflow files mention `otterdog_version` in prose comments as well as as an
input key, so the pattern is anchored on a line that is exactly the input key
(`^\s+otterdog_version:$`) before scanning forward to the first `default:`.
Confirm it lands on the input default and not on some later key. If it proves
brittle, an alternative is a Renovate comment marker
(`# renovate: datasource=pypi depName=otterdog`) above each `default:` line —
more verbose, far more legible, and self-documenting for the next reader.

All five share one `depName`+`datasource`+version, so Renovate raises **one** PR
touching all of them. A miss would produce a red PR rather than a silent partial
bump, because `tests/test_otterdog_pin.py` asserts each mirror equals the
justfile literal.

**Review before merge — what is actually achievable, stated honestly.** The
requirement is a *requested and honoured* review, not a mechanically enforced
one, because enforcement is not available in this repo. Verified live on ruleset
`19092020` (`Main protection`):

- `required_approving_review_count: 0`, set deliberately by #167 — a single
  maintainer cannot approve their own PR, so raising it to 1 would block every
  human PR in the repo, not just this bot's.
- `bypass_actors: [{actor_type: OrganizationAdmin, bypass_mode: always}]` — the
  maintainer bypasses the entire ruleset regardless, so an approval requirement
  would not bind the very person it is meant to gate. This is the decisive
  point: no ruleset configuration produces teeth here.
- `require_extra_approval_for_unattributed_changes: true` does **not** cover bot
  PRs — all 8 most recently merged `app/renovate` PRs (#207, #208, #212,
  #216–#218, #221, #222) report an empty `reviewDecision`, so `renovate[bot]`
  commits count as attributed and no extra approval was ever demanded.

So the configuration to write is `reviewers` + `automerge: false`: Renovate
requests the review on PR creation, and nothing merges until the maintainer
merges it by hand. Renovate does not automerge by default under
`config:recommended`, but setting it explicitly documents the intent against a
future config change.

If hard enforcement is ever wanted, the only path is a status check that fails
until an approving review exists, folded into `CI Summary` (the sole required
context, integration 15368) — and even that is bypassed by the
`OrganizationAdmin` `always` rule above. Out of scope here; noted so the option
is not rediscovered from scratch.

**Plan evidence is unaffected and arrives automatically.** #230 added
`justfile.project` to `plan.yml`'s `pull_request` `paths:` filter, so the
Renovate PR carries its own `otterdog plan` comment — the acceptance evidence
the 1.5.0 bump had to dispatch by hand (run 35844030809). `Plan` remains
**advisory** (ADR-0007 Axis D, #236); `CI Summary` (integration 15368) is the
only required context, so a human still reads the plan before merging.

**Out of scope, and must stay out.** `otterdog.json`'s `base_template` pin
(`otterdog-defaults` v0.13.1) is held **by decision**, not by omission —
v0.14.x introduces `max_cache_size_gb`, whose
`/orgs/{org}/actions/cache/storage-limit` endpoint answers `402` on this org's
Free plan and would write a permanent `WARNING` into every `plan.txt` the drift
layer parses (ADR-0005 `## Corrections`, second 2026-09-23 entry). The two pins
are not in lockstep. The `managerFilePatterns` above exclude `otterdog.json`;
keep it that way.

**Open question for the implementing PR:** whether `template/renovate.json`
should carry the same manager scoped to `import.yml` alone. Downstream callers
no longer mirror the pin at all since #228 (they inherit it from the engine ref),
but an instantiated `import.yml` still carries its own literal that nothing
downstream bumps. It is a one-time onboarding bootstrap, so a stale pin there
decays in importance after the first run — recommend **no**, and record the
reasoning rather than leaving it unstated.

### Related Issues

Refs #225 (ADR-0005 correction: the pin was never Renovate-managed), #228 (the
four mirrors and `tests/test_otterdog_pin.py`), #230 (plan evidence on a pure pin
bump), #164 item 7 (the 1.4.0 bump that missed `import.yml`), #167 (why required
approvals are 0), #152 (the Dependency Dashboard this gate lives on).

### Priority

Low

### Changelog Category

Changed

### Additional Context

Renovate runs here as the hosted Mend app (no `renovate.yml` workflow in
`.github/workflows/`), confirmed by the live dashboard at #152 — so the config
is evaluated by current Renovate and the `managerFilePatterns` / `custom.regex`
spellings are the correct modern ones rather than the legacy `fileMatch` /
`regex` forms.

For context on what the first approved PR would contain: otterdog 1.6.0's
non-webapp diff is three files — null-safe `conditions` on **disabled** rulesets
(`models/ruleset.py`, `models/organization_ruleset.py`, upstream #751), an
optional `head_ref` on the PR REST client, and an app-auth tidy. No new modelled
settings, so no new plan diffs, and this config declares no disabled rulesets.
Upstream #768, #763 and #738 all remain open at 1.6.0.

---

# [Comment #1]() by [c-vigo]()

_Posted on September 24, 2026 at 06:35 AM_

Scope corrected before any work started: the gate moves from **PR creation** to **merge**.

The original body proposed `dependencyDashboardApproval: true`, which suppresses the PR entirely until a checkbox is ticked on #152. That is not what is wanted — the PR should be created normally, so it carries its own `otterdog plan` comment (#230) and is visible as a real change, and then wait for an explicit review before merging.

Body updated accordingly: `reviewers` plus an explicit `automerge: false` in place of the dashboard gate, and the "Review before merge" section now records what enforcement is and is not available here. The load-bearing finding, verified live rather than assumed:

- `Main protection` (`19092020`) lists `bypass_actors: [{actor_type: OrganizationAdmin, bypass_mode: always}]`, so the maintainer bypasses the whole ruleset — **no ruleset setting can bind the person doing the merge**;
- `required_approving_review_count: 0` is deliberate (#167) and raising it would block every human PR, since a solo maintainer cannot self-approve;
- `require_extra_approval_for_unattributed_changes: true` does not reach bot PRs — the 8 most recently merged `app/renovate` PRs (#207, #208, #212, #216-#218, #221, #222) all report an empty `reviewDecision`.

So this is a requested-and-honoured review, not an enforced one. Recorded plainly in the issue rather than left to look like a hard gate.


