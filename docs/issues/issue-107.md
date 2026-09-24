---
type: issue
state: closed
created: 2026-08-07T09:37:46Z
updated: 2026-09-23T21:21:27Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/107
comments: 2
labels: bug, priority:medium, area:workflow
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-24T07:21:56.744Z
---

# [Issue 107]: [otterdog 1.3.4 cannot read live repo rulesets on private repos below enterprise plan](https://github.com/vig-os/org-config/issues/107)

## Summary

otterdog 1.3.4 reads live **repository rulesets** only when the repository is
public **or** the organization is on the `enterprise` plan. Any downstream org
that is private-only and below Enterprise therefore cannot declare a repo
ruleset in its config: the declaration always diffs against an empty live set,
producing a permanent phantom `add` on every `plan` and a duplicate `POST` on
`apply`.

## The gate

`otterdog/models/github_organization.py:701-703`:

```python
if repo.private is False or org_settings.plan == "enterprise":
    # ... load live repo rulesets
```

The read is skipped for a private repo on any non-Enterprise plan. This does not
match platform capability: **GitHub Team supports repository rulesets on private
repositories** (they are configurable in the UI and readable/writable through
`GET|POST /repos/{owner}/{repo}/rulesets`). The gate is stricter than the API it
guards.

## Observed

- Org: `exo-pet` — **Team** plan, all repositories private.
- Repo: `exo-pet/org-config`, with a `Main protection` ruleset declared in
  `otterdog/exo-pet/exo-pet.jsonnet`.
- The ruleset **already exists live** (id `20545163`) and matches the
  declaration field for field.
- Plan run
  [exo-pet/org-config#11 / run 31165784311](https://github.com/exo-pet/org-config/actions/runs/31165784311)
  reported `1 to add, 3 to change, 10 to delete`, where the single `add` was
  `repo_ruleset[name="Main protection", repository=org-config]` — an add of
  something that is already there.
- Removing the declaration dropped the plan to `0 to add, 3 to change,
  10 to delete` (all remaining items are genuine, unrelated drift), confirming
  the add was purely an artefact of the unread live state.

## Impact

For every private-repo downstream below Enterprise:

1. **Permanent phantom diff.** Repo rulesets can never converge — each `plan`
   re-proposes the same `add`, so a clean plan is unreachable and real drift is
   harder to spot in the noise.
2. **Duplicate write on apply.** A real `apply` would `POST` a ruleset that
   already exists (expected `422` / partially-applied run), so the write path is
   unsafe with any repo ruleset declared.
3. **Rulesets are effectively undeclarable** for these orgs — the single most
   important protection primitive on the Team plan is pushed out of
   configuration-as-code.

## Relationship to #69

Distinct bug, same subsystem. #69 is the **write-side** defect (`apply` fails on
any ruleset patch carrying numeric `"15368:"` status checks). This one is the
**read-side** gate, and it bites even when nothing is written. Both share the
same interim workaround, which is why they are easy to conflate.

## Interim (already in place for exo-pet)

Manage the live ruleset manually via `gh api`, and leave the declaration out of
the config with an inline comment recording the reason and the re-declare
condition. Applied in exo-pet/org-config#11 (merged) — the config comment points
at this gate by file and line.

## Durable fix

Change the read gate to match platform capability rather than plan tier: repo
rulesets should be read for private repositories on plans that support them
(Team and above), falling back gracefully when the API returns `403`/`404`
instead of pre-emptively skipping. This is an **upstream** change in
`eclipse-csi/otterdog`.

**Action for the maintainer:** file the upstream report against
`eclipse-csi/otterdog` (not done here — deliberately out of scope for this org's
automation), then re-declare the exo-pet ruleset once a fixed version is pinned.

---

# [Comment #1]() by [c-vigo]()

_Posted on August 7, 2026 at 09:44 AM_

Reported upstream as eclipse-csi/otterdog#729 (includes the stale org-ruleset sibling gates — read gate at main L633 and the hard validation error at main L200 — offered there as an optional split). Durable fix now tracks the upstream issue; the manual-management interim in exo-pet/org-config stands until it lands in a released otterdog we can pin.

---

# [Comment #2]() by [c-vigo]()

_Posted on September 23, 2026 at 09:21 PM_

## Resolved by the otterdog 1.5.0 pin, released in v1.4.0

Upstream [eclipse-csi/otterdog#731](https://github.com/eclipse-csi/otterdog/pull/731)
(`ab66569`) removed the `repo.private is False or org_settings.plan ==
"enterprise"` condition from the repository-ruleset read path — the exact gate
this issue reports at `models/github_organization.py:701-703` — and shipped it in
otterdog **v1.5.0**. Confirmed at the release tag: both read paths
(`github_organization.py` L659 and L754) are ungated.

Pinned here by [PR #229](https://github.com/vig-os/org-config/pull/229) (#225,
merge `d00fddd`) and released in
[v1.4.0](https://github.com/vig-os/org-config/releases/tag/v1.4.0) (tag
`022462b`), which is the version a downstream org can actually consume — hence
closing against the release rather than the merge.

The same commit also gave both ruleset clients `if ex.status in (403, 404):
return []` at `debug` level, which is what makes the bump safe on a Free-plan org
like `vig-os`: the newly-attempted `/repos/{org}/{repo}/rulesets` and
`/orgs/{org}/rulesets` calls answer `403 Upgrade to GitHub Pro` and are absorbed
silently instead of aborting the plan or adding lines to the `plan.txt` the drift
layer parses. Effect on this org is nil — every repo but `qms` is public and
already ruleset-complete, `qms` declares none, and `otterdog 1.5.0 validate
--local` output is identical to 1.4.0.

**For the downstream org this issue was filed from** (Team plan, private repos,
rulesets hand-managed with the declaration held out of the jsonnet), the
re-declare condition stated in the interim workaround is now met. The order
matters, and it is the migration note of v1.4.0:

1. Declare the live rulesets in the jsonnet.
2. Bump the engine pin to `v1.4.0` in the same change — the engine ref selects
   the otterdog release, so this is what makes the live rulesets visible.
3. Empty plan as the acceptance evidence.

Bumping first and declaring later produces a red plan proposing one deletion per
ruleset, plus one `drift` + `critical` issue per ruleset on the next scheduled
run. It does **not** delete live protection: `apply.yml` omits
`--delete-resources`, and `operations/apply.py` is byte-identical across 1.4.0
and 1.5.0.

Scope note: this closes the **repository** ruleset read gate only.
**Organization**-level rulesets remain unusable below `enterprise` — #731 left
the matching condition in `GitHubOrganization.validate()` (L219), which raises an
`ERROR` on any declared org ruleset. Filed as
[upstream #763](https://github.com/eclipse-csi/otterdog/issues/763) and carried
in the README's "Known limitations"; anything org-wide stays hand-managed.

Upstream [#729](https://github.com/eclipse-csi/otterdog/issues/729), the report
this issue was escalated to, is still open upstream despite being fixed by #731 —
so this is closed against the released version, not against that issue's state.

Closing as completed.


