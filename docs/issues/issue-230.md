---
type: issue
state: closed
created: 2026-09-23T09:39:00Z
updated: 2026-09-23T11:58:24Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/230
comments: 1
labels: bug, priority:medium, area:workflow
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-23T21:09:33.128Z
---

# [Issue 230]: [plan.yml's paths filter omits justfile.project, so an otterdog pin bump gets no plan check](https://github.com/vig-os/org-config/issues/230)

## Summary

`plan.yml`'s `pull_request` paths filter omits `justfile.project`, so a PR that
changes **which otterdog version the plan runs** does not trigger a plan check.

`.github/workflows/plan.yml:60-63`:

```yaml
    paths:
      - otterdog.json
      - otterdog/**
      - .github/workflows/plan.yml
```

`justfile.project` holds `otterdog_version` — the ADR-0005 single source of truth,
and the value `plan.yml`'s own "Resolve otterdog version pin" step greps at run
time (`plan.yml:146`). It is arguably the single highest-leverage file in the repo
for plan behaviour: it selects the binary that produces the diff. It is not in the
filter.

## Why it was invisible until now

The previous pin bump (PR #145, otterdog 1.3.4 → 1.4.0) also edited
`otterdog/vig-os/vig-os.jsonnet`, which matches `otterdog/**`, so the plan check
was pulled in incidentally and the gap never showed.

#225's bump (PR #229) is a pure pin + documentation change touching no config
path, so **no plan check ran** — even though #225's acceptance criteria require an
empty plan as the evidence that the new engine version introduces no diff. The
evidence had to be produced by a manual `workflow_dispatch`
([run 35844030809](https://github.com/vig-os/org-config/actions/runs/35844030809),
`Plan: 0 to add, 0 to change, 0 to delete`).

## Impact

Every future otterdog pin bump silently loses its merge gate unless it happens to
touch a config path too. That is exactly the class of change where the plan check
matters most: ADR-0005 makes this pin do double duty as the plan-output format
anchor, and ADR-0007's whole argument for pinning is that a version change can
move plan behaviour. Relying on the bump also editing `otterdog/**` is luck, not
a gate.

## Proposed fix

Add `justfile.project` to `plan.yml`'s `pull_request` paths filter.

Worth deciding at the same time, since the same reasoning applies:

- **`apply.yml` / `drift.yml`** resolve the pin identically. `apply.yml` is
  dispatch-only here so it has no paths filter to fix, but it is worth confirming
  the reasoning is recorded rather than incidental.
- **Scope discipline** — the filter should stay tight. `justfile.project` also
  carries unrelated recipes, so adding it means some plan runs that change no
  config. That is the right trade: a spurious read-only plan is cheap, a missing
  gate on a pin bump is not.

## Acceptance

- [ ] `justfile.project` in `plan.yml`'s `pull_request` paths filter
- [ ] A PR that edits only `otterdog_version` triggers the plan check
- [ ] Rationale recorded inline, so the next reader sees why a `justfile` is in a
      config-paths filter

## Context

Split out of #225 / PR #229 rather than fixed there: changing a workflow trigger
is an engine behaviour change and belongs to its own issue under the single-issue
scope rule.

---

# [Comment #1]() by [c-vigo]()

_Posted on September 23, 2026 at 11:58 AM_

Done in two PRs. All three acceptance criteria are met, the third by observation
rather than by reading the YAML.

| PR | Commit | What |
|----|--------|------|
| #232 | `872aef3` | `justfile.project` added to `plan.yml`'s `pull_request` `paths:` filter, with the inline rationale; comment-only notes in `apply-engine.yml` and `template/`; changelog entry |
| #233 | `ee3b7b4` | Cross-reference at the pin itself, and the isolated acceptance test |

## Acceptance

- [x] `justfile.project` in `plan.yml`'s `pull_request` paths filter
- [x] A PR that edits only `otterdog_version` triggers the plan check
- [x] Rationale recorded inline

## The evidence trail

#232 could not prove the second criterion — it edited `plan.yml`, which the
filter already matched, so a plan run there said nothing about the new entry.
#233 changed **`justfile.project` and nothing else** (`+6/-0`), which only the
newly added entry can match. Before and after, same organisation, same empty
plan, different trigger:

| | Run | Trigger |
|---|-----|---------|
| Before (#229, the 1.5.0 bump) | [35844030809](https://github.com/vig-os/org-config/actions/runs/35844030809) | `workflow_dispatch` — by hand |
| After (#233) | [35857223100](https://github.com/vig-os/org-config/actions/runs/35857223100) | `pull_request` — unprompted |

## Two corrections to this issue, recorded rather than fixed silently

1. **"Merge gate" overstated it.** `Plan` is not a required status check — the
   `Main protection` ruleset requires exactly one context, `CI Summary` — and a
   path-filtered workflow *cannot* be required, since a required check that
   never runs leaves the PR pending forever. What a pin bump was losing is the
   **automatic plan evidence on the PR**, not enforcement. The changelog says so
   explicitly, because the distinction governs what a future reader may assume
   this check blocks. Whether `Plan` should ever be enforcing is a real decision
   rather than an oversight, so it is spun off.
2. **`apply.yml` is `workflow_call`-only**, not "dispatch-only" — the
   push-triggered caller is `apply-engine.yml`, which *does* carry a paths
   filter, and which deliberately continues to omit `justfile.project`. That
   asymmetry is now written where someone will trip over it: plan must **prove**
   before merge that a newly pinned engine produces no diff; apply must not
   **mutate** the live org off an engine-version edit carrying no config delta.

`drift.yml` and `testbed-e2e.yml` also resolve the pin but are
`schedule`/`workflow_dispatch` only — no filter existed to fix.
`template/` needed no equivalent entry and now says why: downstream the pin is
the `otterdog_version:` input inside the caller workflow the filter already
matches, and the skeleton ships no `justfile.project` (#56).

Spun off, not folded in: ADR-0007's L2 "on every same-repo PR" wording, which
the paths filter has never been true to.

