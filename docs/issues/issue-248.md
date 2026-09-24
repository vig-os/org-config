---
type: issue
state: closed
created: 2026-09-24T06:15:47Z
updated: 2026-09-24T06:18:43Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/248
comments: 0
labels: docs, priority:low, area:docs, effort:small, semver:patch
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-24T07:21:49.562Z
---

# [Issue 248]: [The `template/` starter still claims otterdog cannot read private-repo rulesets; the 1.5.0 pin removed that gate](https://github.com/vig-os/org-config/issues/248)

## Summary

Three places still assert the private-repo repository-ruleset **read gate** that
otterdog 1.5.0 removed:

- `template/unmanaged-controls.toml:41` — the starter file every downstream org
  copies: *"Otterdog cannot read live rulesets on a private repo below
  Enterprise, so on a private Team-plan org they are precisely the controls with
  no other detector"*, followed by "the two rows worth holding".
- `README.md:73` — *"a repository ruleset's internals are assertable, which
  matters most on a private repo where Otterdog cannot read rulesets at all"*.
- `unmanaged-controls.toml:277` — the shipped table's own "Repository ruleset
  internals" comment: *"The capability is therefore held for downstream orgs on
  Team/Enterprise, whose private repos otterdog cannot read (#107,
  eclipse-csi/otterdog#729) while REST can"*.

## Why it is false

The gate is gone. #225 bumped the pin to otterdog **1.5.0** and engine **v1.4.0**
ships it; upstream [eclipse-csi/otterdog#731](https://github.com/eclipse-csi/otterdog/pull/731)
removed the plan/visibility gate from **both** ruleset read paths, which is
exactly what closed #107 / [upstream #729](https://github.com/eclipse-csi/otterdog/issues/729)
and released the downstream conversions designed in #205. Repository rulesets
are now read on every plan tier and both repo visibilities, so the fields
otterdog's schema models are plan-diffed everywhere and a row asserting one
duplicates a modelled control — the opposite of what the template currently
recommends.

The README's "Known limitations" section already records the correction
(v1.4.0), so the repo contradicts itself.

## What is still true, and should replace it

- **Org-level** rulesets remain blocked: #731 ungated the *read* path but left
  `GitHubOrganization.validate()` rejecting any declared org ruleset below
  Enterprise ([upstream #763](https://github.com/eclipse-csi/otterdog/issues/763)).
  They stay hand-managed, so an unmanaged-control row is genuinely their only
  detector — the stronger case for these path forms now.
- **Unmodelled rule parameters** are invisible to the plan whatever the
  visibility (#246, [upstream #768](https://github.com/eclipse-csi/otterdog/issues/768)),
  which is the other thing list-addressing reaches.
- Unrelated and not to be touched: the `otterdog-defaults` `v0.13.1` pin, which
  is held for the `max_cache_size_gb` / HTTP 402 reason, not for reads.

## Proposed fix

Documentation and template prose only. Correct the three passages so each
section still makes sense to a downstream consumer: keep the two example rows in
`template/unmanaged-controls.toml` as the *shape* a row takes, but state when a
row is warranted (unmodelled rule parameter, a ruleset kept out of the config,
org-level rulesets) instead of the retired read gate. No row, endpoint, engine,
workflow or config change.

Deliberately out of scope: `docs/issues/*.md` and `docs/pull-requests/*.md`,
which are archival records of what was true when written, and
`template/README.md:212`, which already says "previously unreadable".

## Acceptance

- [ ] No file under `template/`, `README.md` or `unmanaged-controls.toml` claims
      otterdog cannot read repository rulesets on a private repo
- [ ] The `template/` ruleset section still tells a downstream consumer when to
      hold a row, and the example rows still parse as shown
- [ ] `CHANGELOG.md` `## Unreleased` → `### Changed` records the correction

## Context

Found while reviewing the template starter after #225 / v1.4.0. Related: #205,
#107, #246.

