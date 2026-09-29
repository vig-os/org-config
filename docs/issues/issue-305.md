---
type: issue
state: open
created: 2026-09-29T08:50:03Z
updated: 2026-09-29T08:50:03Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/305
comments: 0
labels: chore, security, priority:low, area:workflow, effort:small
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-29T09:51:26.685Z
---

# [Issue 305]: [chore(config): lift tessera's two ADR-0008 exceptions — Signed commits once its contributor signs, Tag bypass once an App tags](https://github.com/vig-os/org-config/issues/305)

## Chore Type

Configuration change

## Description

`tessera` is tier A under [ADR-0008](https://github.com/vig-os/org-config/blob/main/docs/adr/0008-repository-protection-and-merge-policy.md#exceptions) but carries two recorded exceptions. Each has its own exit condition and its own config change, and this issue tracks both until they are lifted.

### 1. No `Signed commits` ruleset

ADR-0008 exceptions row: *`tessera` — No `Signed commits` — its main contributor pushes unsigned commits — exit: that contributor signs.*

The override comment in `otterdog/vig-os/vig-os.jsonnet` (tessera block, L833-912; the comment is at L898-902):

```jsonnet
// EXCEPTION (ADR-0008) — no `Signed commits`: tessera's main
// contributor pushes unsigned commits (every commit on the open
// PRs, and the two promotion commits on `main`). Under merge-commit
// only, a signing rule would make each of those PRs unmergeable.
// Add `orgs.signedCommits()` once they sign.
```

Still true on 2026-09-29: `dev` received unsigned commits today (`49288e3`, `b9559e1` unsigned, `ee274a8` `unverified_email`), carried in by merge commits alongside signed ones.

**Precondition:** confirm with the contributor(s) that every commit they push is signed from now on, and check that no open PR into `dev` or `main` still carries an unsigned commit. `signedCommits()` is a `~ALL` ruleset with no bypass: the moment it is applied, any unsigned push to `dev`, `main` or a PR branch is rejected, and an open PR with an unsigned commit becomes unmergeable until it is rewritten.

**Config change on exit:**
- Add `orgs.signedCommits(),` to the tessera `rulesets:` list and delete the exception comment above.
- Drop the `tessera` "No `Signed commits`" row from the ADR-0008 exceptions table.
- `CHANGELOG.md` `## Unreleased` line.

### 2. `Tag protection` bypass is `#OrganizationAdmin`

ADR-0008 exceptions row (shared with `qx`): the `Tag protection` bypass is `#OrganizationAdmin` in `always` mode, not a release App, because tags are pushed by hand by a maintainer who is an org owner. `release-plz` only opens release PRs; no App writes tags. Exit: an App takes over tagging (`release-plz release`, or the devkit train via [vig-os/tessera#441](https://github.com/vig-os/tessera/issues/441)).

**Config change on exit:**
- Replace `orgs.tagProtection(['#OrganizationAdmin'])` with `orgs.tagProtection(['<tagging-app-slug>'])` and delete the second exception comment (L904-909). As that comment notes, the App must be public.
- Narrow the ADR-0008 row to `qx` only (do not drop it; `qx` still tags by hand).
- `CHANGELOG.md` line.

### Not in scope

`tessera` keeps `dev` as its default branch. That is a separate ADR-0008 row with its own exit (`main` carries the devkit scaffold, or tessera#441) and it stays as is.

## Acceptance Criteria

- [ ] Signing: contributor(s) confirmed signing, no unsigned commit on open PRs, `orgs.signedCommits()` added and applied, ADR row and jsonnet comment removed, changelog updated
- [ ] Tagging: an App creates tessera's tags, `tagProtection` bypass switched to that App and applied, ADR row narrowed to `qx`, jsonnet comment removed, changelog updated
- [ ] `otterdog plan` clean for `tessera` after each apply

## Related Issues

Refs #294. Exit for the tag row: vig-os/tessera#441.

## Priority

Low

## Changelog Category

Security

