---
type: issue
state: closed
created: 2026-07-17T09:03:03Z
updated: 2026-08-07T09:16:41Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/26
comments: 1
labels: chore, priority:high, effort:small
assignees: c-vigo
milestone: M4 — Distribution & exo-pet pilot
projects: none
parent: none
children: none
synced: 2026-08-08T03:28:25.821Z
---

# [Issue 26]: [Release v1.0.0](https://github.com/vig-os/org-config/issues/26)

- [ ] CHANGELOG consolidated; devkit release pipeline (prepare-release → release → promote) with `DEVKIT_TAG_PREFIX=v` → tag `v1.0.0`
- [ ] Downstream Renovate pin-bumping verified against the tag
- [ ] Close #1 with a summary comment linking ADRs and milestones

Part of #1 (M4).

---

# [Comment #1]() by [c-vigo]()

_Posted on August 7, 2026 at 09:16 AM_

Released: **[v1.0.0](https://github.com/vig-os/org-config/releases/tag/v1.0.0)**.

## Evidence

| Item | Value |
| --- | --- |
| Release | https://github.com/vig-os/org-config/releases/tag/v1.0.0 (published, not draft, not pre-release) |
| Tag | `v1.0.0` — annotated + SSH-signed, object `099bf7fce15123ef1e32bf002450efae7194b8ee` |
| Tagged commit | `dfc3cdad9c6353b7085381a23128a8f3b0d7571a` (merge of #104 into `main`) |
| Release PR | #104 — `chore: release 1.0.0`, all checks green, merge commit |
| CHANGELOG | `## [v1.0.0](…releases/tag/v1.0.0) - 2026-08-07` on `main`, with a fresh empty `## Unreleased` |

## What shipped

- **CHANGELOG consolidated** — the whole accumulated `## Unreleased` body (M0–M4) frozen into the dated `v1.0.0` section by the house `prepare-changelog prepare` + `prepare-changelog finalize … --tag-prefix v` pair, so the heading and its release link carry `DEVKIT_TAG_PREFIX=v` exactly as the pipeline would have written them. Release notes are that section verbatim.
- **Root `README.md` rewritten** to describe the shipped engine rather than a config store: Otterdog reconciliation and the pinned-version/vendored-template layout, the three repo-owned `workflow_call`-reusable workflows (`plan` on PR, `production`-gated `apply` on merge to `main`, daily `drift`) and their shared `otterdog-mutate` serialization, the human gate on every mutation, issue-only drift with the open/update/auto-close lifecycle plus the inventory sweep and two-section allow-list, SOPS/age secrets, the least-privilege App auth model, the four testing layers incl. the weekly destructive testbed E2E, downstream distribution via `template/` pinned to a release tag/SHA with the `exo-pet` pilot and the Free-plan read-only-first posture, the trunk model, and a **Known limitations** section (the permanent one-line `vs-dolt` plan artifact — [upstream #694](https://github.com/eclipse-csi/otterdog/issues/694); the otterdog ruleset-write bug forcing manual `gh api` ruleset changes — #69 / [upstream #695](https://github.com/eclipse-csi/otterdog/issues/695); the downstream drift-layer vendoring gap).

## Deviation: the devkit release pipeline could not drive this release

The intended mechanism was `prepare-release` → `release` → `promote-release`. It is blocked here by this repo's own governance, in two independent places:

1. **The changelog-freeze push is refused.** `prepare-release.yml` commits the frozen CHANGELOG **directly to `main`** via `commit-action`. `org-config`'s `Main protection` ruleset requires a pull request and bypasses only `OrganizationAdmin`, so that bot push is rejected — the identical failure as [vig-os/devkit#1227](https://github.com/vig-os/devkit/issues/1227), which was *first seen on this repo* and whose resolution explicitly **rules out** adding the commit App as a bypass actor on `main` (a bot that can write `main` can rewrite the applied org configuration; `sync-issues` was redirected to an unprotected mirror branch instead). Additionally, under the trunk model the release branch is cut from **post-freeze `main`**, so the draft release PR would open with an empty diff.
2. **`release-core` requires an approved release PR** for a `final` release. In the pipeline the PR is authored by the Release App so the maintainer can approve it; any PR a sole maintainer authors themselves cannot be approved by them.

So the release was cut manually with the *same* house tooling and an identical end state: the freeze landed as reviewed PR #104 (strictly more auditable than the bot push it replaces) using `prepare-changelog`, and the annotated tag + GitHub Release were created from the merge commit with notes taken from the CHANGELOG `v1.0.0` section — matching `release-publish.yml`'s own `git tag -a` / `gh release create --title <tag> --notes-file` shape. Worth a follow-up on the devkit side: the trunk render of `prepare-release.yml` is unusable against a require-PR `main` (same root cause as #1227), and `release-publish.yml`'s note extraction greps `## [X.Y.Z]` while `prepare-changelog finalize --tag-prefix v` writes `## [vX.Y.Z]`, so prefixed repos would ship empty release notes.

## Checklist disposition

- [x] **CHANGELOG consolidated; tag `v1.0.0` with `DEVKIT_TAG_PREFIX=v`** — done; pipeline replaced by the equivalent manual cut documented above.
- [ ] **Downstream Renovate pin-bumping verified against the tag** — deferred to the `exo-pet/org-config` re-pin, which is the separate follow-up step now unblocked by this tag existing.
- [x] **Close #1 with a summary comment** — already closed 2026-07-20 with the design/execution summary; a release pointer has been added there.

The **`dev` → `main` promotion** item is **moot**: #63/#67 retired the `dev` branch, `main` is the single applied-state branch, and the `schedule`/`workflow_dispatch` registrations for `drift.yml` and `testbed-e2e.yml` already run from `main` — there is no release gap left to bridge, so nothing was promoted by this release.

No `Apply` run was queued by this merge: `apply.yml`'s `paths:` filter covers only `otterdog.json`, `otterdog/**`, `secrets/**`, and `.sops.yaml`, and this release touched documentation only.

Refs: #26


