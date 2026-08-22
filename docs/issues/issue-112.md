---
type: issue
state: open
created: 2026-08-07T12:52:36Z
updated: 2026-08-10T13:10:18Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/112
comments: 2
labels: chore, priority:low, area:ci, effort:large
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-11T03:47:05.711Z
---

# [Issue 112]: [Consolidate GitHub App secrets to client-ID-only across orgs](https://github.com/vig-os/org-config/issues/112)

> **Program tracker — do not work this issue directly.** Each phase gets its own
> issue, branch, and PR. This issue only holds the plan and the running status.

## Goal

Every GitHub App authentication across the `vig-os` and `exoma-ch` orgs should
use a **client ID only**. Today most App integrations carry a redundant
*numeric* `*_APP_ID` secret alongside (or instead of) the client ID, which
doubles the number of org secrets to rotate, keep in sync, and reason about.

**Nothing is numerically load-bearing.** `@octokit/auth-app` accepts a client-ID
string in its `appId` field on every version pinned anywhere in either org, and
`actions/create-github-app-token` has taken `client-id` since v2. So the numeric
IDs are pure duplication and can be retired without behavior change — the
sequencing below exists only so no consumer is ever left pointing at a secret
that no longer exists.

Findings below come from the 2026-08-07 App-secret audit across both orgs.

## Phases

### Phase 1 — retire the orphaned `APP_SYNC_ISSUES` org secrets

Tracked in #111. The `vig-os` org-level `APP_SYNC_ISSUES_ID` /
`APP_SYNC_ISSUES_PRIVATE_KEY` pair has zero consumers (`tessera`'s same-named
**repo-level** secrets are a different App and stay). Config removal, then live
deletion.

### Phase 2 — upgrade the stragglers to devkit 1.6.0

Three repos still run the old `actions/create-github-app-token@v3.0.0`
numeric-ID scaffold instead of the devkit 1.6.0 client-ID scaffold, accounting
for **33 references** between them:

- `vig-os/h5v`
- `vig-os/scitadel`
- `exoma-ch/brother-printer`

Upgrading them to devkit 1.6.0 retires those scaffolds and removes the last
consumers of several numeric IDs.

### Phase 3 — delete `RELEASE_APP_ID`

Once phase 2 lands, `RELEASE_APP_ID` has no consumers. Delete it from the
`vig-os` org **and** from `otterdog/vig-os/vig-os.jsonnet` (paired edit —
declaration first, live deletion after merge, as in phase 1).

### Phase 4 — client-ID migration for the commit and devkit-upgrade Apps

This is the only phase with a code change ahead of it:

1. Add a `client-id` input to **`vig-os/sync-issues-action`**. It forwards to the
   same `appId` the action already passes to `@octokit/auth-app`, so the
   implementation is trivial; it exists so callers can stop passing a numeric ID.
2. Ship a **devkit release** that switches the scaffolds over:
   - `sync-issues.yml:177` -> `client-id`
   - `devkit-upgrade.yml:55` and `:68` -> `client-id`
   - rename `DEVKIT_UPGRADE_APP_ID` -> `DEVKIT_UPGRADE_APP_CLIENT_ID`
3. Re-scaffold all consumers onto that release.
4. Delete `COMMIT_APP_ID` and `DEVKIT_UPGRADE_APP_ID` from **both** orgs, with
   the paired jsonnet edits in each org's config repo.

### Phase 5 — repo-local pairs (cosmetic)

Lowest value, do last. Repo-scoped App pairs that could equally move to
client-ID-only:

- `vig-os/tessera` — `APP_SYNC_ISSUES_*` (the `tessera-sync-issues-bot` App).
- `vig-os/scitadel` — `RELEASE_BOT_*`. **Careful:** there is a presence gate,
  `if: vars.RELEASE_BOT_APP_ID != ''`, plus `setup-release-bot.sh`; a rename
  silently disables the job unless both are updated together.
- `exoma-ch/hyrr` and `exoma-ch/nucl-parquet` — release-please App pairs. These
  also still use **floating action tags**, worth pinning in the same pass.

## Ordering constraint

Phases are strictly sequential: a numeric ID may only be deleted after the last
workflow that reads it has been re-scaffolded. Phase 5 is independent of 2-4 and
can slip indefinitely.

---

# [Comment #1]() by [c-vigo]()

_Posted on August 7, 2026 at 01:09 PM_

Per-repo execution issues for the migration are now filed (2026-08-07):

- **Phase-0 root prerequisite**: vig-os/sync-issues-action#168 (add `client-id` input, minor release)
- **Devkit release**: vig-os/devkit#1365 (stamped workflows → client-id; DEVKIT_UPGRADE_APP_ID → _CLIENT_ID; SemVer/dual-name fallback question open there)
- **Old-scaffold bumps** (block RELEASE_APP_ID retirement): vig-os/h5v#6 (defers bump mechanics to pre-existing h5v#1) and vig-os/scitadel#209 (defers bump to pre-existing scitadel#207, which has an in-flight branch; additionally owns the RELEASE_BOT_APP_ID → _CLIENT_ID release-please migration incl. the `if`-gate silent-failure hazard)
- **Dedicated-App repo**: vig-os/tessera#364 (keeps tessera-sync-issues-bot identity; jsonnet pairing lands here in org-config)
- **exo-pet side**: exo-pet/org-config#20 (COMMIT_APP_ID + DEVKIT_UPGRADE_APP_ID retirement with paired jsonnet edits)

The vig-os org-config retirement work (drop RELEASE_APP_ID after the bumps; COMMIT_APP_ID + DEVKIT_UPGRADE_APP_ID after devkit adoption; declare DEVKIT_UPGRADE_APP_CLIENT_ID; rename tessera repo-secret declarations alongside tessera#364) remains tracked by this issue.

**Scope note**: exoma-ch (brother-printer devkit bump, hyrr + nucl-parquet release-please pairs) is DEFERRED per owner decision 2026-08-07 — phase 5 stays parked until reopened.

Hard invariant for every step: no numeric `*_APP_ID` secret is deleted while any pinned workflow still references it, and every live secret change pairs with its jsonnet edit in the same change.

---

# [Comment #2]() by [c-vigo]()

_Posted on August 10, 2026 at 01:10 PM_

Reopening: auto-closed by the #149 merge (linked development branch), but this tracker still owns the remaining phases — commit-action + sync-issues-action devkit-1.7 adoptions, h5v/scitadel re-scaffolds, then retirement of COMMIT_APP_ID / DEVKIT_UPGRADE_APP_ID / RELEASE_APP_ID, and the tessera + exo-pet legs. #149 completed only the consumer-list alignment + pre-seeding.

