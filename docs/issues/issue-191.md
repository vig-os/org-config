---
type: issue
state: open
created: 2026-08-21T20:52:21Z
updated: 2026-08-21T20:52:21Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/191
comments: 0
labels: none
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-22T02:56:11.636Z
---

# [Issue 191]: [README: retire stale 'rulesets are not machine-writable' known-limitation](https://github.com/vig-os/org-config/issues/191)

## What's stale

`README.md` › Known limitations still says:

> **Rulesets are not machine-writable at the pinned otterdog version.** Any ruleset whose required status checks carry a numeric app prefix (`15368:…`) fails to apply (#69, upstream eclipse-csi/otterdog#695). Ruleset changes are applied by hand via `gh api` until that is fixed upstream; the committed jsonnet stays the source of truth.

That has been false since 2026-08-10: #69 was closed by pinning otterdog **1.4.0** (PR #145), and the ruleset write path was confirmed end-to-end the same day (PR #148). Re-confirmed in production on 2026-08-21: #186's normal apply job wrote `dismiss_stale_reviews_on_push: true` to live ruleset `13401788` on sync-issues-action — no hand-applied `gh api` involved.

## Task

Remove the bullet (or the whole now-empty **Known limitations** section — the other former bullet, the vs-dolt benign-plan artifact, was already retired by #189/PR #190).

Worth deciding in the same PR: whether the section should instead carry what is *actually* still open at the pinned version — the private-repo ruleset **read** gate (#107, upstream eclipse-csi/otterdog#729) — rather than being deleted outright. Implementer's call; the point of this issue is only that the current text tells operators to hand-apply rulesets that apply fine.

Refs: #69

Related: #145, #148, #107, #189
