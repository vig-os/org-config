// House defaults overlay for Otterdog org configs (vig-os and downstream orgs).
//
// WHAT THIS IS
//   A thin re-export of the vendored Eclipse base template with the *house*
//   repository merge policy folded into `newRepo`. An org entry point imports
//   THIS file instead of `vendor/otterdog-defaults/otterdog-defaults.libsonnet`
//   and gets the house policy on every repo it declares, by construction —
//   nothing is copied per repo and nothing silently regresses to the upstream
//   Eclipse defaults, which are the exact opposite of ours.
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

local base = import 'vendor/otterdog-defaults/otterdog-defaults.libsonnet';

// The house merge policy: merge commits ONLY, with the pull request's title and
// body as the merge commit's title and message. Rationale: every branch is a
// single reviewed unit of work whose PR title is already a Conventional Commit
// subject, so a merge commit carrying that title and the PR body preserves the
// review context verbatim, and disabling rebase/squash keeps the merged history
// shape uniform across the fleet.
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
// looked at this yet".
local upstreamMergePolicy = {
  allow_merge_commit: false,
  allow_rebase_merge: true,
  allow_squash_merge: true,
  merge_commit_title: 'MERGE_MESSAGE',
  merge_commit_message: 'PR_TITLE',
};

// All three merge methods enabled, on the upstream commit title/message
// defaults. This is where repos predating the house policy sit: merge commits
// were switched on without disabling rebase and squash. Narrowing one of these
// repos to `houseMergePolicy` is a live settings change (it removes merge
// buttons contributors may be using), so it is done deliberately, per repo,
// never as a side effect of this overlay.
local legacyMergePolicy = upstreamMergePolicy {
  allow_merge_commit: true,
};

base {
  // The house policy is applied AFTER the base constructor, so a repo block can
  // still override any individual field the usual way.
  newRepo(name):: base.newRepo(name) + houseMergePolicy,

  // Exported so a repo block can name the policy it is on instead of restating
  // five fields. Usage: `orgs.newRepo('x') + orgs.legacyMergePolicy { ... }`.
  houseMergePolicy:: houseMergePolicy,
  upstreamMergePolicy:: upstreamMergePolicy,
  legacyMergePolicy:: legacyMergePolicy,
}
