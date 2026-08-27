---
type: issue
state: closed
created: 2026-08-27T07:53:45Z
updated: 2026-08-27T09:23:12Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/205
comments: 0
labels: feature, priority:medium, area:workflow
assignees: c-vigo
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-27T12:26:47.704Z
---

# [Issue 205]: [unmanaged-controls: the dotted-key walk cannot address list elements, so ruleset internals are unassertable](https://github.com/vig-os/org-config/issues/205)

## What's missing

`unmanaged-controls.toml` addresses a control with a **dotted key path** walked over the decoded JSON, and `select_path()` (`src/drift_layer/controls.py`) descends dicts only:

```python
for segment in path.split("."):
    if not isinstance(current, dict) or segment not in current:
        return MISSING
```

That is the right call for jq-freedom (ADR-0005) and for never guessing. But it means **anything GitHub returns inside a list is unassertable**, and the most consequential downstream control is exactly that shape: a repository ruleset's required status checks.

```console
$ gh api repos/exo-pet/exo-fleet/rulesets/20836487 --jq '.rules[] | select(.type=="required_status_checks") | .parameters'
{"strict_required_status_checks_policy":true,
 "do_not_enforce_on_create":false,
 "required_status_checks":[{"context":"CI Summary"},{"context":"Check Summary"}]}
```

`rules` is an array, and so is the response of `/repos/{o}/{r}/rules/branches/{branch}`. There is no dict-addressable view of it — the classic `/branches/{branch}/protection` endpoint is a different system and 404s on a ruleset-protected branch. Downstream, `exo-pet/org-config` keeps its four hand-managed `Main protection` rulesets as `kind = "unassertable"` rows for that reason: a durable, versioned record that is **never evaluated**. A silent UI edit to a required-check set — or an accidental `PUT` that drops one — shows up as nothing until someone re-reads it by hand on the quarterly cadence.

That gap was the concrete finding in [exo-pet/org-config#48](https://github.com/exo-pet/org-config/issues/48): the exo-fleet ruleset required one status check that summed the wrong workflow, and the assertion row that would have caught a regression cannot be written today.

## Why it matters more than it looks

Otterdog cannot read live repo rulesets on private repos below the enterprise plan (#107, eclipse-csi/otterdog#729), so on a Team-plan private org the *rulesets are precisely the controls with no other detector*. The unmanaged-controls table is the only mechanism that could watch them, and it is the one shape it cannot address.

## Sketch (not a decision)

Options, cheapest first — all stay jq-free and stdlib-only:

1. **Numeric segments** — `rules.3.parameters.strict_required_status_checks_policy`. Cheap, but a rules array is unordered in practice; an index is a false anchor.
2. **A match segment** — one predicate form such as `rules[type=required_status_checks].parameters…`, matching exactly one element and degrading (`MISSING`) on zero or many. Addresses the real shape: rules are keyed by `type`.
3. **Set-valued assertion** — for the checks themselves, `expect` as a TOML array compared order-insensitively (`_equal` already compares whole values, so this is mostly about normalizing a list of dicts to a set of contexts).

2 + 3 together are what a ruleset row needs. Whatever the form, the existing doctrine is unchanged: `expect` is the desired value, `tolerated` records a known divergence, any third value is drift, and an unreadable row degrades only itself.

## Acceptance

- [ ] A row can assert the required-status-check **set** of a named repository ruleset, order-insensitively
- [ ] A row can assert `strict_required_status_checks_policy` on that ruleset
- [ ] A path that matches zero or several elements degrades to `MISSING`/`UNRESOLVED` rather than guessing
- [ ] Downstream `exo-pet/org-config` can convert its four `unassertable` `main-protection-*` rows into real assertions

