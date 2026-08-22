---
type: issue
state: open
created: 2026-08-07T09:37:46Z
updated: 2026-08-07T09:44:07Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/107
comments: 1
labels: bug, priority:medium, area:workflow
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-08T03:28:19.635Z
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

