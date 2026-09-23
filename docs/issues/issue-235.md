---
type: issue
state: closed
created: 2026-09-23T11:58:52Z
updated: 2026-09-23T12:48:07Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/235
comments: 0
labels: docs, priority:low, area:docs, effort:small, semver:patch
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-23T21:09:31.773Z
---

# [Issue 235]: [ADR-0007 says L2 plan runs "on every same-repo PR"; the paths filter has never made that true](https://github.com/vig-os/org-config/issues/235)

## Summary

[ADR-0007](docs/adr/0007-ci-and-testing-strategy.md) line 92 describes the L2
layer of the test pyramid as:

> **L2 — live read-only `otterdog plan`** against `vig-os` on **every same-repo
> PR**: plan is non-mutating, so this is free E2E read-path coverage.

`plan.yml` has carried a `pull_request` `paths:` filter since it was written, so
L2 has never run on every same-repo PR — only on PRs touching `otterdog.json`,
`otterdog/**`, `.github/workflows/plan.yml` and, since #230, `justfile.project`.
Most PRs to this repo (engine code, docs, workflows, the release train) get no
plan at all, by design.

## Why it matters

The claim is load-bearing in its own document, not incidental phrasing. ADR-0007
justifies L2 as the layer that gives "free E2E read-path coverage", and the
pyramid's shape is the ADR's actual decision. A reader sizing the coverage gap
between L2 and L3 — or deciding whether some new check needs L3 because L2
"already covers every PR" — is reading something that is not true of the
implementation.

#230 is the proof this matters in practice rather than pedantically: the filter's
contents silently decided that a pin bump got no plan, and nobody noticed for two
release cycles because the ADR describes a workflow that runs on everything.

## Proposed fix

Documentation only. Reconcile line 92 with the implementation: L2 runs on
same-repo PRs **that touch the config, the plan workflow, or the otterdog pin**,
and say briefly why the filter is narrow (a plan is a live-API round trip against
the org; running one on a README typo buys nothing).

Record it as a dated entry in ADR-0007's `## Corrections` block rather than
rewriting the line in place, matching how #225 handled ADR-0005's incorrect
"Renovate owns the pin" claim.

## Acceptance

- [ ] ADR-0007's L2 bullet matches what `plan.yml` actually triggers on
- [ ] The narrowness of the filter is explained, not just stated
- [ ] Recorded as a dated `## Corrections` entry, not a silent rewrite

## Context

Found while evaluating #230 and deliberately split out: that issue changed a
workflow trigger, this one corrects an ADR, and the single-issue scope rule keeps
them apart.
