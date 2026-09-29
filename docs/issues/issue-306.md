---
type: issue
state: open
created: 2026-09-29T08:50:05Z
updated: 2026-09-29T09:08:33Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/306
comments: 1
labels: chore, priority:low, area:workflow, effort:small
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-29T09:51:26.307Z
---

# [Issue 306]: [chore(config): decide qms — integrate and make public, keep private and unprotected, or archive](https://github.com/vig-os/org-config/issues/306)

## Chore Type

General task

## Description

`qms` is the one repo [ADR-0008](https://github.com/vig-os/org-config/blob/main/docs/adr/0008-repository-protection-and-merge-policy.md) leaves undecided: its tier is **Deferred**, and its exceptions row reads *"All three merge methods, `delete_branch_on_merge: false`, `allow_update_branch: false`, restated inline — Deferred and out of scope, so its live state must not move — exit: its own decision."* This issue is that decision. It needs an owner call; no option is preferred here.

### Facts (verified 2026-09-29)

- Private repo on the Free plan, so no ruleset can be enforced: `GET /repos/vig-os/qms/rulesets` answers 403 *"Upgrade to GitHub Pro or make this repository public"*.
- Default branch is `worktree-agent-ab0adbce`. There is no `main`. Three branches exist, `worktree-agent-a4e78417`, `worktree-agent-a2612d43` and `worktree-agent-ab0adbce`, each with one unique commit.
- Last push 2026-03-25.
- `otterdog/vig-os/vig-os.jsonnet` L675-697 freezes the live state: the five merge fields of the retired `legacyMergePolicy` restated inline, `delete_branch_on_merge: false`, `allow_update_branch: false`, `allow_forking: false`, `default_branch: 'worktree-agent-ab0adbce'`, `private: true`.

### Options

**(a) Integrate into `main` and make it public → tier B.**
- Consequences: gets `Main protection` and the house merge policy like every other active public repo. The whole history and content become public, so it needs a confidentiality review first.
- Repo work first: merge the three branches into a new `main` (by hand, outside otterdog; otterdog cannot set a default branch that does not exist).
- Config change: `default_branch: 'main'`, `private: false`; delete the inline merge fields, `delete_branch_on_merge`, `allow_update_branch` and `allow_forking` (a public repo cannot disable forking) so the house defaults apply; add `rulesets: [orgs.mainProtection([])]` (plus `orgs.signedCommits()` if applicable); replace the "OUT OF SCOPE" comment with a tier-B one. ADR-0008: move `qms` from **Deferred** to tier B, drop its exceptions row. Changelog line.

**(b) Keep private, explicitly unprotected.**
- Consequences: protection stays discipline-only for as long as `vig-os` is on Free. Nothing changes live.
- Config change: reword the jsonnet comment from "until it gets its own decision" to a permanent reason (private on Free, no enforceable ruleset). ADR-0008: rename the **Deferred** tier row to a permanent unprotected tier, set the exceptions row's exit to "a plan change (already an open question in the ADR)" and remove "needs its own decision". Optionally also fix the default branch to a real `main`, which is independent of protection. Changelog line.

**(c) Archive.**
- Consequences: read-only; no protection needed. Reverses ADR-0008's "no archiving" decision for this one repo, so the ADR records it as an amendment.
- Config change: `archived: true` in the `qms` block (any other field change must be applied before, since an archived repo cannot be edited). ADR-0008: drop `qms` from the tier table and the exceptions table, note the amendment. Changelog line.

## Acceptance Criteria

- [ ] Option chosen and recorded (comment here)
- [ ] Repo-side work done where the option needs it (branch integration, confidentiality review)
- [ ] `vig-os.jsonnet`, ADR-0008 and `CHANGELOG.md` updated per the option; applied, `otterdog plan` clean for `qms`

## Related Issues

Refs #294 (its "`qms`" decision checkbox is deferred to this issue).

## Priority

Low

## Changelog Category

Changed

---

# [Comment #1]() by [c-vigo]()

_Posted on September 29, 2026 at 09:08 AM_

Decided 2026-09-29: the content moves into the PET-scanner project's controlled-document store in the `exo-pet` org (Team plan, so it gets enforceable rulesets there); `vig-os/qms` is retired once ingested and verified, then this block and the ADR-0008 row go. Tracked in the destination org; this issue closes when the block is removed.

