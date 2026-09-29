---
type: issue
state: closed
created: 2026-09-25T17:07:46Z
updated: 2026-09-25T20:56:04Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/259
comments: 1
labels: feature, priority:medium, area:ci, effort:medium, semver:minor
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-26T07:11:54.001Z
---

# [Issue 259]: [plan: warn when the engine's installation token cannot resolve a declared App slug (all four otterdog write-path call sites)](https://github.com/vig-os/org-config/issues/259)

## What's missing

`plan` is this repository's L2 review gate, and for one class of change it is green on
config that `apply` cannot write. #256 is the live case: a ruleset bypass actor naming a
GitHub App whose slug the engine's installation token cannot read. Otterdog's read path
never calls `/apps/{slug}` — it maps the live `actor_id` back to a slug from
`GET /orgs/{org}/installations` (`models/github_organization.py:761-765`) — so the plan
renders the actor correctly and the failure surfaces only on the live, mutating `apply`.

A check with no false positives is available, and it needs no new credential and no live
ruleset read: at review time, ask the engine's *own* credential the question `apply` will
ask.

## Where it goes

`.github/workflows/plan.yml`, one step between **Run otterdog plan (read-only, committed
config)** (`plan.yml:197`, `id: plan`) and **Build plan report (comment body + job
summary)** (`plan.yml:230`). `steps.app-token.outputs.token` — minted at `plan.yml:189-195`
by `create-github-app-token` — is still in scope there, and *Build plan report* is the one
place that assembles both the PR comment and `$GITHUB_STEP_SUMMARY`, so the finding lands
in the artefact reviewers actually read. It must be folded into the marker-upserted body
(`MARKER='<!-- otterdog-plan-report -->'`, `plan.yml:239`/`:305`), not posted as a second
comment.

`plan.yml` is `workflow_call`-able and downstream callers are ~5-line wrappers
(`template/.github/workflows/plan.yml`), so the step reaches every consumer on its next pin
bump with no downstream edit.

## Predicate

For every App-shaped actor in the evaluated config (no `#` / `@` prefix, `:bypass_mode`
suffix stripped):

```
GET /apps/{slug}   Authorization: Bearer ${{ steps.app-token.outputs.token }}
  200   -> apply can write this actor
  else  -> apply WILL fail on any ADD or CHANGE of that ruleset
```

The cheaper predicate — "the actor is an App **and** is not already live" — is falsified by
this org's own config. `otterdog/vig-os/vig-os.jsonnet` declares **ten** App bypass actors
across ten rulesets (`commit-action-bot` x7, `vig-os-release-app` x3) and they apply fine,
because both Apps are public. That predicate would fire ten times on green config, and it
would still miss the #256 case: a ruleset patch re-sends the **whole** bypass list
(`models/repo_ruleset.py:63-71` passes `expected_object.to_provider_data(...)` on
`LivePatchType.CHANGE`; `models/ruleset.py:635-652` re-resolves every actor in it), so an
already-live unreadable App 403s on the next change to that ruleset too.

Stated as an observation, not as a documented mechanism — GitHub's `GET /apps/{app_slug}`
reference states no authentication requirement at all: probed 2026-09-25, a private App
answers `404` unauthenticated, `200` to an org-owner PAT and `403` to an installation token
(the traceback in #256), while `commit-action-bot`, `vig-os-release-app` and
`vig-os-org-config` each answer `200` unauthenticated. The check does not rest on the
mechanism: it makes the real call with the real token and believes the answer.

## Scope: all four write-path call sites, not only bypass actors

`grep -rn get_app_ids` over otterdog 1.5.0 (the ADR-0005 pin) returns four write-path
consumers of `GET /apps/{app_slug}`:

| Site | Field | On an unreadable App |
| --- | --- | --- |
| `models/ruleset.py:649` | ruleset `bypass_actors` | `RuntimeError` -> patch fails (the #256 case) |
| `models/ruleset.py:177-189` | ruleset `required_status_checks`, **non-numeric** app prefix only (`:208` short-circuits on `app_slug.isdigit()`) | `RuntimeError` -> patch fails |
| `models/branch_protection_rule.py:348` (`get_app_node_ids`) | branch-protection-rule status checks | `RuntimeError` -> patch fails |
| `models/environment.py:244` (`get_actor_ids_with_type`) | environment reviewers | **caught and skipped** — `providers/github/__init__.py:502-506`: `except RuntimeError: _logger.warning(f"app '{actor}' does not exist, skipping")` |

The fourth is worse than the reported bug: `apply` **succeeds** with the App reviewer
silently dropped, leaving a protection that was never written and a permanent phantom plan
diff.

`vig-os` and `exo-pet` escape the second row today only by notation — every declared
status-check prefix is numeric (`'15368:…'`), which takes the `isdigit()` escape. vig-os
commit `3487ed9` ("reference status-check apps by slug, not numeric") is precisely the kind
of change that removes that accident.

## Getting the declared actors without a token

Verified locally; no extra pin, and it works on the runner:

```sh
uvx --from "otterdog@${OTTERDOG_VERSION}" python -c \
  "import rjsonnet;print(rjsonnet.evaluate_file('otterdog/<org>/<org>.jsonnet'))"
```

Bypass actors live at `repositories[].rulesets[].bypass_actors[]` and
`rulesets[].bypass_actors[]`; status-check prefixes under the rulesets' `required_status_checks`;
environment reviewers at `repositories[].environments[].reviewers[]`.

## Warn, never fail

Per the ADR-0007 Axis D decision recorded on #236, `Plan` is **advisory** and is not a
required check (only `CI Summary` is, and a path-filtered workflow cannot become one —
#230). The finding therefore belongs in the plan report body and the job summary, not in
the job's exit code; it must not turn `steps.plan.outputs.rc` into a failure, or the *Fail
on plan error* step's contract ("nonzero means config/auth/harness, never drift") breaks.

## Where the code should live

`drift.yml` already solved this shape for downstream callers (#169): it guards
`job.workflow_sha` (`drift.yml:288-292`), checks the engine out a second time into
`.drift-engine` (`:302-303`), and runs
`uv run --project "${DRIFT_PROJECT_DIR}" drift-layer …` where `DRIFT_PROJECT_DIR` is
`.drift-engine` downstream and `.` on the engine's own runs (`:357`, `:364`). A
`drift-layer` sub-mode reusing that pattern gets unit tests (ADR-0007 L1) and a single pin,
rather than an inline heredoc in a credential-bearing workflow. Rough cost: ~120 lines of
Python plus tests in `src/drift_layer/`, ~45 lines of workflow, one new CLI mode. The
irreducible risk is that the workflow half cannot be proven locally — first real evidence
is the PR's own plan run.

## Acceptance

- [ ] `plan` reports, folded into the existing plan report and job summary, every declared
      App slug the engine's installation token cannot resolve via `GET /apps/{slug}`
- [ ] Coverage spans all four write-path sites above, and the report distinguishes the
      three that fail the apply from the one that drops the actor silently
- [ ] The finding never changes the job's exit code, and `steps.plan.outputs.rc` keeps its
      current meaning
- [ ] Declared actors are extracted token-free; only the check itself uses the App token
- [ ] Logic unit-tested in `src/drift_layer/`, not an inline workflow heredoc

## Context

Spun off from #256, which is narrowed to documenting the limitation and the residual gap
(docs-only). Upstream eclipse-csi/otterdog#772 is open (filed 2026-09-24, no PR);
eclipse-csi/otterdog#695 fixed the same defect for required status checks by accepting a
numeric app id and was never extended to bypass actors.


---

# [Comment #1]() by [c-vigo]()

_Posted on September 25, 2026 at 08:30 PM_

## Adjustments being made before the PR

The draft implementation was attacked in a round-2 adversarial pass (patch applied, 195 tests green,
`actionlint` clean, exo-pet's committed config evaluated with the pinned otterdog and the extractor
run against it). It holds — zero findings on `vig-os`'s real config, zero false positives on
`exo-pet`'s, one correct true positive — but seven things change before this opens as a PR.

**1. Every new step becomes fail-soft, because downstream the plan context is a hard merge gate.**
The premise this design was built on — "`Plan` is not a required check (ADR-0007 Axis D)" — is true
of `vig-os` and **false of the only consumer**: `exo-pet/org-config`'s `Main protection` requires
exactly one context, `plan / Plan committed config against live exo-pet`, and its caller deliberately
ships **no** `paths:` filter for that reason. ADR-0007:148-150 says the opposite and is being
corrected — filed as **#268**. Consequence here: the draft's new *Checkout engine repository
(downstream callers)* step is a bare `actions/checkout` with no `continue-on-error`, i.e. the first
step on exo-pet's merge gate that can fail for a transient reason and block every PR, arriving
silently on a Renovate pin bump. All new steps get guard + `continue-on-error: true` + an `if:` on
the guard output; the check step already `exit 0`s on all three failure branches and its
"could not be checked" path already handles a missing `.drift-engine`.

**2. A rate-limit 403 is classified as transient, not as "`apply` will fail".** `app_actors.py:129`
has `_UNRESOLVABLE_STATUSES = frozenset({403, 404})`, and `github_client.py:132-133` discards the
`HTTPError`'s headers, so `ApiError` carries a bare status. GitHub answers 403 both for *"Resource
not accessible by integration"* (the #256 true positive) and for primary/secondary rate limits — and
the step immediately before this one is a full org read on the same token, the likeliest way to
arrive at the limit. `_send`/`ApiError` are extended to carry `x-ratelimit-remaining` / `retry-after`,
a 403 carrying either is reported as undetermined (the module's own doctrine: *"a false 'apply will
fail' costs more than a missing one"*), and there is a test for it.

**3. An allowlist for known-unresolvable slugs.** Run against `exo-pet`'s evaluated config, the
extractor finds 5 sites / 2 slugs and produces exactly one finding: a bypass actor that is a
**private App owned by a sibling org**, on a ruleset that is already live and correct and cannot be
repaired until upstream `eclipse-csi/otterdog#772` lands. Without suppression, every `exo-pet` PR
comment carries a red-toned finding nobody can act on, from its next pin bump onward — which is
precisely the "standing noise trains a reviewer to wave plans through" failure #262 names.
`drift-allowlist.toml` exists for this class (*"known, benign, and by design … adding an entry goes
through the normal PR flow"*); its shape is checked first and reused if it fits, otherwise a small
table in the same file. Documented in the README, tested.

**4. `plan.yml`'s `paths:` gains `src/drift_layer/**`.** The mode lives in
`src/drift_layer/app_actors.py` + `cli.py`, neither of which is in the filter, so after this PR every
later change to the CLI flags or report shape ships with **zero** end-to-end signal. Same lesson as
#230, and the file's own comment already makes the argument for `justfile.project`
(*"Relying on that coincidence is luck, not coverage"*); `pyproject.toml` goes in with it.

**5. Three documentation fixes this PR owns.**
- `README.md`'s known-limitations sentence still ends *"with nothing here to flag it yet"* — stale
  the moment this merges.
- #262's README bullet and CHANGELOG entry say, of the read-path drop, *"neither reaches the pull
  request"*. True at #262's commit, false after this one: the **declared** half is now reported, the
  undeclared-live half still is not. This PR amends that sentence — a PR must leave the file true.
- The "advisory" wording is qualified to "not a required check **in this repository**" rather than
  republishing the ADR claim #268 corrects. `README.md` is public and is read downstream.

**6. The App installation token is exported as `DRIFT_REPOS_TOKEN`, not `GITHUB_TOKEN`.** The CLI
already prefers that name (it is `drift.yml`'s); exporting an org-admin token under the name every
`gh` invocation picks up by default is a footgun for whoever next adds a `gh` call to that step.

**7. Comment-budget and exit-code hardening.** `_report_app_actors` must catch everything and exit 0
itself rather than relying on the workflow's `if !`, and the fragment must be counted against
`MAX_PLAN_BYTES=55000` (measured: 719 bytes clean, 1262 with one unresolvable slug — but a 403 on a
widely-used slug renders seven rows, and on overflow the comment upsert returns 422 under
`set -euo pipefail`, failing the job, which per item 1 is exo-pet's merge gate).

**Kept as drafted** (reviewer-endorsed): the warn-and-skip engine-pin guard, the `github-actions`
implicit-slug gating, and the committed-config fixture-drift test.

The PR body will state the proof limits honestly — green path only, downstream unexercised until
`exo-pet`'s next pin bump — along with the sibling-org true positive and how the allowlist handles it.


