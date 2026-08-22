---
type: issue
state: closed
created: 2026-08-14T05:37:14Z
updated: 2026-08-14T05:49:24Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/164
comments: 0
labels: chore, priority:high, area:docs, effort:medium, semver:patch
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-14T06:03:43.888Z
---

# [Issue 164]: [[CHORE] Pre-tag cleanup for v1.1.0: complete and correct the Unreleased changelog, align the template otterdog pin, fix the release recipes](https://github.com/vig-os/org-config/issues/164)

### Chore Type

General task

### Description

Pre-tag cleanup for the next release (`v1.1.0`). A release-readiness audit of
`v1.0.1..main` found the `## Unreleased` section incomplete and inaccurate in
several places, plus two code inconsistencies that should not ship. None of
these change behaviour of the drift layer or the reusable workflows; they make
the release notes true and the shipped template internally consistent.

**Changelog (`CHANGELOG.md`, `## Unreleased`)**

1. Empty `### Deprecated` heading — released entries only carry populated
   sections; drop it.
2. The devkit **1.7.0 / 1.8.0 / 1.9.0** adoptions are unlogged, though they are
   the largest block of change in the cycle (20+ managed files, plus the new
   `.vig-os` knobs `DEVKIT_COMMIT_TYPES`, `DEVKIT_BRANCH_TYPES`,
   `DEVKIT_LANGUAGES`). The repo's convention is to log devkit adoptions.
3. The deletion of `renovate-changelog-build.yml` / `renovate-changelog-commit.yml`
   is unlogged. This is also *why* later Renovate PRs carry no entry, so the
   entry should say so rather than leaving the gap looking like an oversight.
4. The secret-scanning-extras entry claims the control was recorded as
   **unassertable**; the shipped `unmanaged-controls.toml` asserts it with a
   `tolerated` value. Contradicts the `#116` entry in the same section.
5. Stale citation `apply.yml:72-73` (the comment moved to `:87` when the #105
   supersession header landed) — repeated in `otterdog/vig-os/vig-os.jsonnet`.
6. Renovate entries name superseded versions (`setup-uv` v9, `ruff` 0.15.22)
   while v10.0.0 and 0.16.2 are what ship; #160/#161 have no entry at all.

**Code**

7. `template/.github/workflows/import.yml` still defaults `otterdog_version` to
   `1.3.4` while the other three template callers were moved to `1.4.0` — a
   downstream org onboarding from `template/` would import on one version and
   plan on another.
8. The release recipes in `justfile.project` are commented out **and** still say
   `--ref dev`, which is dead under the trunk model; `docs/DOWNSTREAM_RELEASE.md`
   advertises `just promote-release` / `just changelog-preview`, neither of which
   exists.

### Acceptance Criteria

- `## Unreleased` documents every substantive change in `v1.0.1..main`, with no
  empty sections and no superseded version numbers.
- No entry contradicts the config it describes; no stale `file:line` citations.
- `template/` is internally consistent on the otterdog pin.
- The release recipes either work as documented or the docs stop advertising them.
- `just precommit` green; no behaviour change to `drift_layer` or the reusable
  workflows.

### Additional Context

Found while evaluating release readiness for `v1.1.0` (minor bump: the `#116`
unmanaged-controls leg is additive, and the `workflow_call` input schemas of
plan/apply/drift are unchanged since `v1.0.1`).

The two hard blockers found by the same audit are already resolved upstream in
devkit 1.9.0 ([vig-os/devkit#1479](https://github.com/vig-os/devkit/issues/1479),
adopted in #163): the changelog freeze now targets the release branch, so the
release PR is non-empty and the Commit App needs no bypass on `main`.

One item is deliberately **out of scope** here, as it needs a live downstream
run rather than an edit: `apply.yml`'s `uses: ./.github/workflows/plan.yml`
inside a workflow consumed downstream via `workflow_call`. The guard is
`if: inputs.org_github_id == ''`, but an `if:` gates execution, not reference
resolution. Same class as #56. To be verified against a real `exo-pet` apply on
the candidate tag before promote.

### Changelog Category

Changed

