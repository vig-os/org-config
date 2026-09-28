// House defaults overlay for Otterdog org configs (vig-os and downstream orgs).
//
// WHAT THIS IS
//   A thin re-export of the vendored Eclipse base template with the *house*
//   repository merge policy folded into `newRepo`, plus the house ruleset
//   shapes as constructors. An org entry point imports THIS file instead of
//   `vendor/otterdog-defaults/otterdog-defaults.libsonnet` and gets the house
//   policy on every repo it declares, by construction — nothing is copied per
//   repo and nothing silently regresses to the upstream Eclipse defaults, which
//   are the exact opposite of ours.
//
// HOW TO USE IT
//   Drop this file next to the org entry point, beside the `vendor/` tree:
//
//     otterdog/<org>/
//       <org>.jsonnet             local orgs = import 'house-defaults.libsonnet';
//       house-defaults.libsonnet  (this file)
//       vendor/otterdog-defaults/otterdog-defaults.libsonnet
//
//   The `vendor/` import below is resolved relative to THIS file, so the layout
//   above is the only requirement — it works unchanged in this engine repo and
//   in a downstream org's private `org-config` repo, which vendors its own copy
//   of the base template. This file is deliberately org-neutral: it names no
//   org and is copied verbatim, never edited, downstream.
//
// EVERYTHING ELSE IS PASSED THROUGH
//   Every other constructor (`newOrg`, `newRepoRuleset`, `newRepoSecret`, ...)
//   is re-exported untouched, so an existing config only changes its import
//   line. `newRepo(name)` keeps its signature; only the five merge fields move.
//   The ruleset constructors below are additions, not replacements: a repo may
//   still declare any ruleset by hand with `newRepoRuleset`.
//
// THE RULE BEHIND IT
//   Which repo carries which ruleset, and every deliberate exception, is stated
//   in vig-os/org-config ADR-0008 (repository protection and merge policy).

local base = import 'vendor/otterdog-defaults/otterdog-defaults.libsonnet';

// The house merge policy: merge commits ONLY, with the pull request's title and
// body as the merge commit's title and message. Rationale: every branch is a
// single reviewed unit of work whose PR title is already a Conventional Commit
// subject, so a merge commit carrying that title and the PR body preserves the
// review context verbatim, and disabling rebase/squash keeps the merged history
// shape uniform across the fleet.
//
// The repo fields are the ONLY merge-method lever: Otterdog does not model a
// ruleset's `allowed_merge_methods`, and apply re-PUTs a ruleset without it, so
// the ruleset-level value is always GitHub's all-three default
// (eclipse-csi/otterdog#768). The rulesets below therefore carry no merge policy.
local houseMergePolicy = {
  allow_merge_commit: true,
  allow_rebase_merge: false,
  allow_squash_merge: false,
  // Can be one of: PR_TITLE, MERGE_MESSAGE
  merge_commit_title: 'PR_TITLE',
  // Can be one of: PR_BODY, PR_TITLE, BLANK
  merge_commit_message: 'PR_BODY',
};

// The vendored Eclipse base template's own merge defaults, restated verbatim so
// a repo can opt back out of the house policy explicitly. Applying this mixin
// is how a repo says "upstream defaults, deliberately" rather than "nobody has
// looked at this yet" — e.g. a sacrificial testbed that exercises the vendored
// defaults themselves.
local upstreamMergePolicy = {
  allow_merge_commit: false,
  allow_rebase_merge: true,
  allow_squash_merge: true,
  merge_commit_title: 'MERGE_MESSAGE',
  merge_commit_message: 'PR_TITLE',
};

// ---------------------------------------------------------------------------
// House ruleset shapes. Each returns a complete `newRepoRuleset`, so a repo
// block lists them directly in `rulesets:` and overrides any field the usual
// way (`orgs.mainProtection([...]) { required_pull_request+: { ... } }`) when
// it deliberately deviates — say why next to the override.
//
// Status checks are passed in their canonical Otterdog form. For checks bound
// to a first-party app that is never an org installation (github-actions,
// app_id 15368) that is the numeric `15368:<context>` prefix, not a slug:
// Otterdog resolves ids to slugs only through `/orgs/{org}/installations`, so a
// committed slug is a permanent phantom plan diff (needs otterdog >= 1.4.0 to
// write). Bypass actors are passed in Otterdog's actor syntax: `#<Role>` or
// `#<Role>:<mode>` for a role, `@<org>/<team>` for a team, a bare slug for an
// App — and an App actor is writable only while the App is PUBLIC and
// installed on the org.
// ---------------------------------------------------------------------------

// Default-branch protection (`main`): a reviewed, checked pull request is the
// only way in.
//   - One approval, and a push after it dismisses it, so the approval always
//     covers the code being merged.
//   - Unresolved review threads block the merge.
//   - Code-owner review OFF: with a single owner who also authors the PRs the
//     gate can never be satisfied, and its only outcome is a routine bypass.
//   - `checks` are required and must have run against an up-to-date branch
//     (`strict`). Pass the repo's CI aggregator (one context that fails when
//     any job fails), not the individual jobs. `[]` — a repo with no
//     aggregator yet — requires no status check at all rather than one that
//     can never report, which would block every merge.
//   - Org owners may bypass, but only by merging a pull request
//     (`pull_request` mode): an audited, deliberate override that still leaves
//     a PR behind, never a direct push.
local mainProtection(checks=[]) = base.newRepoRuleset('Main protection') {
  allows_creations: true,
  bypass_actors+: [
    '#OrganizationAdmin:pull_request',
  ],
  include_refs+: [
    'refs/heads/main',
  ],
  required_pull_request+: {
    dismisses_stale_reviews: true,
    required_approving_review_count: 1,
    requires_code_owner_review: false,
    requires_review_thread_resolution: true,
  },
  required_status_checks:
    if std.length(checks) == 0 then null
    else super.required_status_checks {
      status_checks: checks,
      strict: true,
    },
};

// Integration-branch protection (`dev`, for repos on a gitflow release train):
// a pull request with passing `checks`, no approval — the review that counts
// happens once, on the release PR into `main`. `bypass` names the automation
// that pushes to `dev` directly (e.g. the App committing issue syncs).
local devProtection(checks, bypass=[]) = base.newRepoRuleset('Dev protection') {
  allows_creations: true,
  bypass_actors+: bypass,
  include_refs+: [
    'refs/heads/dev',
  ],
  required_pull_request+: {
    required_approving_review_count: 0,
    requires_code_owner_review: false,
    requires_review_thread_resolution: true,
  },
  required_status_checks+: {
    status_checks: checks,
  },
};

// Release-branch protection (`release/*`): same shape as `dev`, plus deletion,
// because a release train creates and retires these branches. `bypass` names
// the automation that pushes release commits (changelog stamps, syncs).
local releaseProtection(checks, bypass=[]) = base.newRepoRuleset('Release protection') {
  allows_creations: true,
  allows_deletions: true,
  bypass_actors+: bypass,
  include_refs+: [
    'refs/heads/release/*',
  ],
  required_pull_request+: {
    required_approving_review_count: 0,
    requires_code_owner_review: false,
    requires_review_thread_resolution: true,
  },
  required_status_checks+: {
    status_checks: checks,
  },
};

// Signed commits on every branch. Signing is its own ruleset, not a flag on
// `mainProtection`, so that one rule covers every ref; creation, deletion and
// force-push stay allowed because this ruleset governs signatures only.
local signedCommits() = base.newRepoRuleset('Signed commits') {
  allows_creations: true,
  allows_deletions: true,
  allows_force_pushes: true,
  include_refs+: [
    '~ALL',
  ],
  required_pull_request: null,
  required_status_checks: null,
  requires_commit_signatures: true,
};

// Tag protection: every tag is immutable to everyone but `bypass`, the release
// automation that writes (and prunes) release tags. Updates are refused here
// explicitly; creation and deletion are refused by the vendored ruleset
// defaults (`allows_creations` / `allows_deletions` false), which this shape
// deliberately leaves in place.
local tagProtection(bypass) = base.newRepoRuleset('Tag protection') {
  allows_force_pushes: true,
  allows_updates: false,
  bypass_actors+: bypass,
  include_refs+: [
    '~ALL',
  ],
  required_pull_request: null,
  required_status_checks: null,
  target: 'tag',
};

base {
  // The house policy is applied AFTER the base constructor, so a repo block can
  // still override any individual field the usual way.
  newRepo(name):: base.newRepo(name) + houseMergePolicy,

  // Exported so a repo block can name the policy it is on instead of restating
  // five fields. Usage: `orgs.newRepo('x') + orgs.upstreamMergePolicy { ... }`.
  houseMergePolicy:: houseMergePolicy,
  upstreamMergePolicy:: upstreamMergePolicy,

  // House ruleset shapes (see above). Usage:
  //   rulesets: [
  //     orgs.mainProtection(['15368:CI Summary']),
  //     orgs.signedCommits(),
  //     orgs.tagProtection(['my-release-app']),
  //   ],
  mainProtection:: mainProtection,
  devProtection:: devProtection,
  releaseProtection:: releaseProtection,
  signedCommits:: signedCommits,
  tagProtection:: tagProtection,
}
