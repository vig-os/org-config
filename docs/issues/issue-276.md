---
type: issue
state: open
created: 2026-09-25T21:41:29Z
updated: 2026-09-25T21:41:29Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/276
comments: 0
labels: bug, priority:medium, area:ci, effort:small
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-26T07:11:50.099Z
---

# [Issue 276]: [The reusable `plan.yml`'s auxiliary steps `Build plan report` and `Upsert plan comment` are not fail-soft — a 422/5xx on a cosmetic comment upsert reddens the consumer's required plan context](https://github.com/vig-os/org-config/issues/276)

## What's wrong

The reusable `plan.yml` has two auxiliary steps that can redden the job on their own, independently
of the plan verdict. Both run unconditionally after the plan, both use `errexit`, and one of them
makes three unguarded network writes.

`.github/workflows/plan.yml`, line numbers as of `main` @ `561f19c` (#268's docs PR adds a header
block and shifts everything below it by its length):

| Step | Line | `continue-on-error` | Failure path |
| --- | --- | --- | --- |
| `Build plan report (comment body + job summary)` | `:394` | **no** | `if: always() && steps.plan.outcome != 'skipped'` (`:395`), `set -euo pipefail` (`:402`) — any nonzero command in the body assembly fails the job |
| `Upsert plan comment on the PR` | `:493` | **no** | `if: always() && github.event_name == 'pull_request' && …` (`:494`), `set -euo pipefail` (`:500`), one `gh api … --paginate` read (`:503`) and a `PATCH` (`:507`) or `POST` (`:510`) |

Neither step contributes to the verdict. The verdict is carried entirely by `Run otterdog plan`
(`:210`, which captures `rc` rather than failing) and `Fail on plan error` (`:516`, which reflects
that `rc` and is *meant* to redden). Steps `:394` and `:493` exist to render a comment and a job
summary — cosmetics — yet a 422, a 403, a 5xx, a rate-limited `--paginate` read, or a
`comment-body.md` that step `:394` never got to write is enough to fail the check.

**Contrast with the three steps #274 shipped**, which got this exactly right: `Guard engine pin`
(`:262`), `Checkout engine repository` (`:293`) and `Check declared App slugs` (`:330`) each carry
`continue-on-error: true` (`:275`, `:300`, `:336`), each is `if:`-gated on the guard's output, and
the last one deliberately runs without `errexit` (`set -uo pipefail`, `:358`) with every branch
ending in `exit 0` (`:373`, `:392`). Its own comment states the rule as binding:

> FAIL-SOFT, BINDING (#268): downstream this job's context is a REQUIRED check on `main` … An
> advisory read must not be able to convert a transient GitHub blip into "no PR can merge"
> — `plan.yml:265-274`

So the rule is already written into the file. Two steps that predate it do not follow it.

**The repo already knows about one cause and fixed only that cause.** The `### Added` entry PR #274
shipped (`CHANGELOG.md:12`, filed under #259) says the comment body "now reserves the fragment's
bytes inside the 55000-byte budget so an over-long body can never 422 the upsert and fail that
gate", and the in-file comment at `plan.yml:440-443` is explicit:

> An over-limit body makes the upsert's `gh api` return 422 under `set -euo pipefail`, failing this
> job — which downstream is a required check on `main` (#268), i.e. the one failure this whole
> design forbids.

That is a byte-budget fix for the one 422 cause the author could foresee, on a step that stays hard
against every other cause.

## Why it matters

Downstream this job's context is a required status check on `main` — that is the whole finding of
#268, and it is why #274's steps are fail-soft. A cosmetic comment upsert that fails takes the
consumer's merge gate with it, for every PR including ones that touch no config, and it arrives
silently on a Renovate pin bump. The failure modes are the ordinary ones — secondary rate limits on
the write (this job has already spent an App token on a full org read), a GitHub 5xx, a `--paginate`
page that 403s — none of which say anything about whether the committed config is valid.

The consumer's own caller states the contract this violates: *"the check only reddens on invalid
config, auth, or harness errors."* A 5xx on a comment POST is none of the three.

It also makes the file's own header false. #268 writes the fail-soft rule where the next author will
read it; a reader who then reads down the file finds two steps that ignore it, and learns the rule
is aspirational.

## Suggested fix

1. Add `continue-on-error: true` to `Build plan report` (`:394`) and `Upsert plan comment on the PR`
   (`:493`). Both are auxiliary; neither needs to be able to fail the job.
2. Leave the verdict spine alone. Checkout, `Set up uv`, `Resolve otterdog version pin` (`:176`),
   `Mint full App installation token` (`:202`), `Run otterdog plan` (`:210`) and `Fail on plan
   error` (`:516`) redden by design — that *is* the consumer's stated contract, and
   `continue-on-error` on `:516` would silently disarm the check. `Fail on plan error` still runs
   under `if: always()`, so the verdict survives an auxiliary step degrading.
3. Keep the byte budget (`:447-448`). It stops one cause cheaply; `continue-on-error` covers the
   rest. Both, not either.
4. Note in the step comment what degradation looks like: a red X on the *step* inside a green job,
   the plan output still in the job summary (written at `:436` before the comment is built), and no
   PR comment. That is the intended visible outcome, not a silent swallow.

## Proof limits, stated

**The failure path cannot be exercised locally or in CI.** There is no way to make GitHub return a
422 or a 5xx to `gh api` on demand from this repo, and `act`-style local runs do not reproduce the
comment API at all. So what the PR's own run can prove is exactly this: the green path still works
— the comment is upserted in place on the marker, the job summary is written, the job is green, and
`Fail on plan error` still reports the plan's `rc`. It cannot prove the degraded path; that is a
read of the diff plus `actionlint` and zizmor, and the first real exercise is whenever GitHub next
fails a write. Worth saying in the PR body rather than implying a test exists.

## Acceptance

- [ ] `Build plan report` and `Upsert plan comment on the PR` carry `continue-on-error: true`
- [ ] `Fail on plan error` is unchanged and still carries the verdict; no other step's failure
      semantics change
- [ ] The `plan.yml` header's fail-soft rule no longer names these two as exceptions (#268 lands
      them as named exceptions; this issue is what retires that wording)
- [ ] The PR body states what its own run proves and what stays unexercised

## Context

Found by the round-3 adversarial review of #268 (attack A3), which enumerated every step in the job
and its failure path. #268 documents the downstream required-check gate and writes the fail-soft
rule into the ADR and the `plan.yml` header — it names these two steps as the shipped exceptions
and points here. #274 is the worked example of the rule (three steps, all fail-soft). #259 is the
byte-budget point fix for the one 422 cause already handled.

