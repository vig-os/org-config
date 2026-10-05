---
type: issue
state: open
created: 2026-10-04T13:57:45Z
updated: 2026-10-04T13:57:45Z
author: gerchowl
author_url: https://github.com/gerchowl
url: https://github.com/vig-os/org-config/issues/319
comments: 0
labels: discussion, priority:medium, area:docs
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-10-05T08:44:32.851Z
---

# [Issue 319]: [AX: onboarding a new repo is a three-file change discoverable only by failing CI — findings from declaring stepv](https://github.com/vig-os/org-config/issues/319)

cc @c-vigo — discussion, not a change request. Opinions wanted before anything is implemented.

## Where this comes from

I declared a brand-new repo (`vig-os/stepv`, #317) end to end as an agent, including the devkit
scaffold on the other side. Six things cost real time, and all six are fixable in this repo. None
of them are bugs — the config is unusually well documented and I want to be specific that the
problems are **discoverability and edit-site locality**, not quality.

Worth saying first, because it shapes every suggestion below: the comment density in
`vig-os.jsonnet` is the best I have worked with. Every non-obvious decision carries a why, a date
and an issue number. The `plan.yml` report — especially its **"Declared App slugs"** section, which
makes the two checks `plan` structurally cannot — is exactly the right pattern. Most of what
follows is "do more of that".

---

## 1. Cross-repo work loses every agent affordance in this repo

This is the big one and it generalises past org-config.

I was an agent rooted in a *different* repo, editing this one. This repo ships **33
`.claude/skills/`** — including `branch-naming`, the precise skill that would have stopped me
naming a branch `feat/declare-stepv` — plus flake-generated pre-commit hooks. I got none of them,
because skills load from the session root, not from the repo being edited.

So the affordances are real and they were invisible. Two consequences:

- I used `feat/`, which the gate rejects (§4).
- I bypassed the pre-commit hooks, because `hooks = { }` means `.pre-commit-config.yaml` is a
  flake-generated store symlink that does not exist until the dev shell is first entered.

**There is no `CLAUDE.md` in this repo.** That is the one file an agent asked to edit a repo will
read regardless of where its session is rooted. For the repository that governs the organisation, a
short one — config-first creation, the three files a repo declaration touches, the branch-name rule,
a pointer to the skills — would have prevented items 1, 2 and 4 outright. This may be worth raising
with devkit as a general scaffold question too.

## 2. Declaring a repo is a three-file change with no signpost at the edit site

Adding `orgs.newRepo('stepv')` to `vig-os.jsonnet` also requires:

- `tests/conftest.py` → `DECLARED_REPOS`
- `tests/conftest.py` → `DECLARED_ORG_SECRETS` (per-secret sorted tuples)
- `tests/test_app_actors.py` → the declared App-actor site count (23 → 25)

Nothing at the jsonnet edit site says so. You find out from a red CI about two minutes after
pushing, as three separate assertion failures.

Cheapest fix: a comment at the head of `_repositories::` listing the companion edits — the same
style the file already uses for the `DEVKIT_UPGRADE_APP_ID` "MAINTENANCE COUPLING" note, which is a
model of this exact thing done well.

Worth discussing further: `test_extract_declared_repos_matches_committed_set` asserts
`extract_declared_repos(declared_jsonnet) == DECLARED_REPOS` — **both sides derive from this
repo**. It is a change-detector. "Make a human confirm the declared set changed deliberately" is a
legitimate goal, but the cost is a second edit site and a confusing failure mode, and the tests
that catch *config vs live* drift (the valuable ones) are separate. Is the deliberateness gate
worth keeping, and if so could it read better as a snapshot/approval test?

The App-actor count has a rule that is now in its docstring but was not before: **+2 per trunk
repo** (`Release protection` bypass, `Tag protection` bypass), **+3 per gitflow repo** (plus `Dev
protection`). Deriving the expected count from the declared rulesets rather than hardcoding it
would remove the edit site entirely.

## 3. A ground-truth test skips silently without `jsonnet` on PATH

Both jsonnet-gated tests in `test_app_actors.py` are `skipif(shutil.which("jsonnet") is None)`.
Locally, `uv run pytest tests/` → **224 passed, 2 skipped**, green. In CI → red on the site count.
I only caught my own wrong number by re-running under `nix shell nixpkgs#go-jsonnet`.

A silent skip on a test whose whole job is to be ground truth is the failure mode devkit's
guardrails exist to prevent elsewhere. Options: fail rather than skip when `CI` is set; or put
`go-jsonnet` in the dev shell so the skip is unreachable in practice. `just validate` already
pulls `jsonnetfmt`, so the tooling is a line away.

## 4. The branch-name gate is correct; the recovery path destroyed the review

`feat/` is not an accepted type (`feature,bugfix,hotfix,release,docs,test,refactor`, or
`chore/<summary>`). Fair — and the error message helpfully points at
`docs/COMMIT_MESSAGE_STANDARD.md` and the skill.

But renaming the branch to fix it (`gh api -X POST .../branches/.../rename`) **closed PR #316**
instead of retargeting it, so the review, the plan comment and the thread were lost and #317 had to
be opened fresh. GitHub documents rename as retargeting open PRs; it did not here, and I have not
worked out why.

Suggestion: one clause in that error message — "open a new PR rather than renaming the branch" —
is probably the whole fix, and it lands where someone is already reading.

## 5. The plan report says nothing about org secrets, and that hides a live gap

Filed separately as #318, summarised here because it is the same AX shape as the App-slug problem
#259 already solved: **config that is green on review and wrong on apply.**

`apply` does not reconcile `selected_repositories` for the nine dummy-valued org secrets. `revkit`
has been declared in all six App-secret lists since #312 (2026-09-29), `apply-engine.yml` ran
successfully for that exact commit and twice more since, and `revkit` is still absent from every
live list today. The plan reports `0 to delete`, no secret actions, and reads as complete.

The fix I would argue for is **option 1 in #318**: extend the plan comment with a declared-vs-live
secret-repository diff, in the same shape and for the same stated reason as "Declared App slugs".
That section is already the best AX surface in this repo — it is where both a human reviewer and an
agent look, and it is the natural home for every check `plan` cannot make.

## 6. "Config-first creation" is stated once, in a code comment

The rule lives in a comment inside `settings+:`, roughly 1000 lines into `vig-os.jsonnet`. It is
not in `README.md`, not in `CONTRIBUTING.md`, and there is no repo-onboarding runbook — while
`docs/runbooks/github-app.md` and `docs/runbooks/secrets.md` exist for narrower tasks. (`secrets.md`
also does not mention the `selected_repositories` PUT from §5.)

I created `stepv` with `gh repo create` and learned the rule afterwards, which is precisely the
bypass the comment warns about. `members_can_create_*_repositories: false` enforces it for members,
but owners are exempt, so for an owner — or an agent holding an owner token — it is discipline plus
the daily drift sweep, nothing more.

A `docs/runbooks/new-repo.md` covering declare → merge → apply → scaffold → the secret PUTs would
be the single highest-value doc in the repo, and it answers the open question below.

---

## Open question I could not answer from the repo

**Is config-first creation actually the intended workflow — declare, merge, wait for the
human-gated apply to create the repo, and only then clone and scaffold?**

The comment says so. But that puts a human approval gate *before* `git clone`, so no work can start
until someone approves a deployment. For an agent-driven flow that is a hard stop in the middle of
setup.

Three readings, and I do not know which you intend:

1. **Yes, deliberately.** Governance precedes code; the wait is the point.
2. **Create-then-declare is fine** as long as the declaration lands promptly, and the drift sweep is
   the real control. That is effectively what I did, and what the config calls a bypass.
3. **Same-PR flow** — create the empty repo and open the declaration PR together, so the repo exists
   for cloning while governance catches up within the hour.

Whichever it is, it belongs in the runbook from §6, because the config comment currently reads as
(1) while owner permissions make (2) the path of least resistance.

---

## If only one thing happens

§5 (secret diff in the plan comment) and a short `CLAUDE.md` from §1. Those two cover the one
finding with live consequences and the one that caused three of the other five.

Happy to open PRs for any of these, but wanted the discussion first — several touch conventions
that are yours to set, not mine.
