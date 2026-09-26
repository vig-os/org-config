---
type: issue
state: closed
created: 2026-09-25T20:25:59Z
updated: 2026-09-25T21:47:04Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/268
comments: 1
labels: docs, priority:high, area:docs, effort:small
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-26T07:11:51.874Z
---

# [Issue 268]: [ADR-0007:148-150 says a consumer org wires no plan context into its ruleset — the only consumer requires exactly that context, so every `plan.yml` step is on a downstream merge gate](https://github.com/vig-os/org-config/issues/268)

## What's wrong

`docs/adr/0007-ci-and-testing-strategy.md:148-150`, the last Consequences bullet, asserts:

> - The Axis D decision propagates downstream unchanged: `template/`'s plan caller keeps its
>   `paths:` filter, and **a consumer org wires no plan context into its ruleset**. On a private
>   consumer below Enterprise, where environment required reviewers return HTTP 422, the human gate
>   is the `workflow_dispatch` that runs apply (template Mode B) […]

The only consumer that exists does exactly the opposite. `exo-pet/org-config`'s `Main protection`
ruleset requires **exactly one** status context, and it is the plan context. Evaluated from the live
committed jsonnet (`gh api repos/exo-pet/org-config/contents/otterdog/exo-pet/...`, evaluated with
the ADR-0005 pin `otterdog@1.5.0`'s own `jsonnet_evaluate_file`):

```
org-config | Main protection | {'status_checks': ['plan / Plan committed config against live exo-pet'], 'strict': False}
```

The consumer's own caller says the same in prose, and the first half of the ADR sentence is false
there too — it has deliberately **deleted** the `paths:` filter the template ships. Read live from
`repos/exo-pet/org-config/contents/.github/workflows/plan.yml`:

```yaml
# PREVIEW PATH: `plan` is non-mutating (GETs only) and runs on EVERY pull
# request — deliberately unfiltered (#35): the check `plan / Plan committed
# config against live exo-pet` is required by org-config's `Main protection`
# ruleset (declared in otterdog/exo-pet/exo-pet.jsonnet since #62), and a path
# filter would deadlock any PR that skips it.
…
on:
  pull_request:
    # No `paths` filter: this check is ruleset-required on main (#35), so it
    # must produce a run on every PR or non-config PRs could never merge.
```

So both halves of the propagation claim are wrong about the one adopter: the caller drops the
filter, and the ruleset wires the context. The claim has been wrong since the consumer's #62, not
merely gone stale.

**Not in scope and still true:** the preceding bullet (`:145-147`), *"`Main protection`
deliberately gains **no** second required context"*, is a statement about **this** repository and is
correct — `vig-os`'s own gate requires only `CI Summary` (#230). The #236 "`Plan` stays advisory"
verdict is likewise a `vig-os` decision and survives. What is wrong is only the assertion that the
decision *propagates downstream unchanged*.

## Why it matters

1. **`plan.yml` is a reusable `workflow_call` workflow, and downstream its context is a hard merge
   gate.** Every step in it is a step on exo-pet's merge gate, for every PR, including PRs that touch
   no config. The consumer's caller header spells out the property that buys: *"A non-config PR just
   produces an empty diff; `otterdog plan` exits 0 on drift, so the check only reddens on invalid
   config, auth, or harness errors."* Any new step with an unguarded failure path converts a
   transient GitHub blip into "no exo-pet PR can merge" — and it arrives silently, on a Renovate pin
   bump.
2. **This has already produced a near-miss.** #259's design was engineered against the ADR's model
   of the gate and cited it: the draft added an unguarded `actions/checkout` of the engine repo to
   `plan.yml`, and its README text read *"the finding is **advisory** … since `Plan` is not a
   required check (ADR-0007 Axis D)"*. Both are true of `vig-os` and false of `exo-pet`, and
   `README.md` is **public**. #259 is being adjusted before its PR — every new step fail-soft
   (guard + `continue-on-error` + `if:` on the guard output), and the README sentence qualified to
   "in this repository" — but the ADR is the source the next author will read.
3. **Corrections precedent.** ADR-0007 already carries two entries (2026-09-23 #235, the L2
   `paths:`-filter claim; 2026-09-23 #237, the pre-#63 `dev` trunk). Both were *stale* statements.
   This one was never true of the only consumer, which makes it the more load-bearing kind: a reader
   auditing "can a CI change here block a downstream merge?" is told no.

## Suggested fix

1. **Correct `:148-150` in place**, per the ADR's own convention (*"Entries are added here only if
   an assumption above is later found wrong, preserved verbatim for audit"*, `:153-155`): the Axis D
   decision is `vig-os`-local. A consumer may — and the only one does — make the plan context
   required and drop the caller's `paths:` filter, which are the same decision (a filtered skip
   deadlocks a required context).
2. **Add a Corrections entry** dated 2026-09-25 quoting the original sentence verbatim, the
   evaluated `Main protection` line above, and the consumer's caller comment, in the voice of the
   two existing entries. State what survives unchanged (`:145-147`, #236, the credential rule) so
   the correction is not read wider than it is.
3. **Record the engineering consequence where an author will hit it**, not only in the ADR: every
   step added to the reusable `plan.yml` must be fail-soft, because its context is a downstream
   required check. The natural home is the `plan.yml` header comment beside the existing `paths:`
   rationale, which is where the #230 lesson already lives.
4. **Revisit `template/`'s shipped `paths:` filter** (`template/.github/workflows/plan.yml:19-30`),
   or at least annotate it: a template whose only adopter had to delete that line is a template that
   hands the next org a deadlock. Cheapest form is a comment saying "delete this filter if you make
   the plan context required" — a separate issue if it grows past that.
5. Re-check at the next onboarding (`exoma-ch`, `MorePET`) whether they wire the context too; if
   both do, the ADR's default is backwards rather than merely over-general.

## Acceptance

- [ ] `docs/adr/0007-ci-and-testing-strategy.md:148-150` no longer claims a consumer wires no plan
      context, and no longer claims the adopter keeps the `paths:` filter
- [ ] A Corrections entry records the original text verbatim with the evaluated evidence, and names
      what is unaffected
- [ ] The fail-soft requirement for steps added to the reusable `plan.yml` is written where a
      workflow author will see it
- [ ] No file in this repo — `README.md` included — states that `Plan` is not a required check
      without scoping the claim to this repository

## Context

Found by the round-2 adversarial review of #259 (attack A1), which evaluated `exo-pet`'s committed
config with the pinned otterdog rather than reading its prose. Related: #259 (the plan-time App-slug
check, now being made fail-soft), #236 (Axis D "stay advisory", a `vig-os` decision), #230 (the
`paths:`-filter coverage lesson and the `CI Summary`-only gate here), #235 / #237 (the two existing
ADR-0007 corrections).

---

# [Comment #1]() by [c-vigo]()

_Posted on September 25, 2026 at 09:42 PM_

## Correction to this issue's own dating: the right attribution is exo-pet **#35**, not #62

The body says *"The claim has been wrong since the consumer's #62, not merely gone stale."* That
sentence takes its date from the consumer's caller comment, which says the ruleset is *"**declared**
in `otterdog/exo-pet/exo-pet.jsonnet` since #62"* — and declaring is not requiring. Re-fetched:

| Fact | Source | Date |
| --- | --- | --- |
| the ADR bullet at `:148-150` was written | `868d4f5`, *"docs(adr): decide the Plan check stays advisory (ADR-0007 Axis D)"* (#236) | **2026-09-23** |
| the consumer deletes its caller's `paths:` filter | `04d8645`, *"ci(plan): run plan on every PR as the required main status check"* | **2026-08-24** 07:52Z |
| exo-pet #35 *"Make plan an always-running required status check on org-config main"* closed | `gh issue view 35 --repo exo-pet/org-config` | **2026-08-24** 07:56Z |
| the required context lands on ruleset `20545163` | `/rulesets/20545163/history` → version `47427597` | **2026-08-24** 10:02Z |
| exo-pet #62 closed | `gh issue view 62 --repo exo-pet/org-config` | **2026-09-24** |

So both halves — filter deleted, context required — went live on **2026-08-24 under #35**, a month
*before* the ADR sentence was written. #62 is a month later and, decisively, **one day after** the
bullet: it moved the already-live, hand-managed ruleset's declaration into the committed jsonnet.

This matters because it inverts the finding. Attributed to #62, the dates read `2026-09-24 >
2026-09-23` and a future auditor concludes the ADR sentence was true when written and merely went
stale — exactly the reading this issue exists to rule out. Attributed to #35, the dates prove
"never true of the only consumer", which is the stronger and correct claim. The Corrections entry is
preserved verbatim for audit (ADR-0007 `:153-155`), so the wrong date would be permanent.

The PR attributes to **#35 / 2026-08-24** with the two timestamps and the ruleset history version,
and cites #62 as the later jsonnet import. **Do not** copy this issue body's "since #62" wording.

## "No consumer PR can merge" overstates the live gate

The same phrase appears in the *Why it matters* item 1. Checked against
`repos/exo-pet/org-config/rulesets/20545163`: `enforcement: "active"`, but
`bypass_actors: [{actor_type: "OrganizationAdmin", bypass_mode: "pull_request"}]`,
`current_user_can_bypass: "pull_requests_only"`, and the `pull_request` rule carries
`required_approving_review_count: 0`.

So a red or `Pending` plan context does not stop the org owner merging; it costs a bypass click, and
it stops everyone else. The accurate phrasing is *"reddens another org's merge gate, which its only
maintainer then has to bypass by hand"*. Worth being precise here in particular, because that gate
shape — zero required approvals plus an admin bypass — is the #115/#167/#195/#226 pathology the
paragraph above (`:145-147`, declared unaffected) says this repo keeps removing. The correction
should not assert it is a hard blocker one paragraph after calling that shape a pathology.

## Acceptance item 3: the fail-soft rule needs two classes, not one exception

Writing "every step added to `plan.yml` must be fail-soft" with a single carve-out for the plan leg
is contradicted by the file itself. Enumerated, the job splits cleanly in two:

- **Verdict spine** — checkout, `Set up uv`, `Resolve otterdog version pin`, `Mint full App
  installation token`, `Run otterdog plan`, `Fail on plan error`. These redden by design, and that
  *is* the contract the consumer's caller states ("the check only reddens on invalid config, auth,
  or harness errors"). A single "the plan leg" exception does not cover the token mint or the pin
  resolve.
- **Everything auxiliary** — anything not needed to produce the verdict. Must be fail-soft.

And there are **two shipped auxiliary steps that are not**: `Build plan report` and `Upsert plan
comment on the PR`, both `if: always()`, both `set -euo pipefail`, the second making three
unguarded `gh api` calls. Filed as **#276**; the header names them as the known exceptions and
points there, so the rule is honest on the day it lands rather than aspirational. Fixing them is a
behaviour change and out of scope for a docs PR — naming them is not, and leaving them unnamed is
what would make the header false.


