// House defaults overlay: the vendored Eclipse base template re-exported with
// the house repository merge policy folded into `newRepo`, so every repo
// declared below inherits it without restating it (see house-defaults.libsonnet).
local orgs = import 'house-defaults.libsonnet';

orgs.newOrg('vig-os', 'vig-os') {
  settings+: {
    billing_email: 'carlos.vigo@exoma.ch',
    default_repository_permission: 'read',
    description: 'Versatile Instrumentation and Governance Operating Stack',
    location: 'Switzerland',
    // Repository creation is config-first: a repo is declared here and created
    // by `otterdog apply`. A UI-created repo bypasses every default this config
    // exists to enforce and is never cleaned up automatically — apply creates
    // what the config declares but deliberately does not delete what it omits
    // (apply.yml:87), so an undeclared repo surfaces only as an inventory
    // drift issue (#21) and is removed by hand. Owners can always create
    // regardless of these flags; for them this stays discipline plus the drift
    // sweep (#121).
    members_can_create_private_repositories: false,
    members_can_create_public_repositories: false,
    name: 'vigOS',
    plan: 'free',
    // Override (not `+:`) the base template's Eclipse-specific injections so
    // the config matches live vig-os exactly (drift-free): drop the inherited
    // `eclipse_project` org property and `eclipsefdn-security`/`<slug>-security`
    // security managers. vig-os declares only the `type` property and no
    // security-manager teams.
    security_managers: [],
    custom_properties: [
      orgs.newCustomProperty('type') {
        allowed_values+: [
          'internal',
          'tools',
        ],
        default_value: [
          'internal',
        ],
        description: 'The repo type',
        required: true,
        value_type: 'multi_select',
      },
    ],
    // Org-level workflow settings (distinct from the repo-level `workflows+:`
    // block that hangs off `newRepo`).
    workflows+: {
      // An approving review from a workflow satisfies `required_approving_review_count`
      // without a human, so this is the one permission that can defeat every
      // review gate in the fleet — including from a workflow added by the PR it
      // would approve. `devkit` already set this at repo level; this closes it
      // org-wide (#121).
      actions_can_approve_pull_request_reviews: false,
    },
  },
  teams: [],
  secrets+: [
    // The five devkit-scaffolded repos authenticating with the client-ID form,
    // plus h5v and scitadel PRE-SEEDED ahead of their re-scaffold off the
    // legacy numeric form (#112) so the migration lands with a working
    // credential on day one and without another list edit (#123).
    orgs.newOrgSecret('COMMIT_APP_CLIENT_ID') {
      selected_repositories+: [
        'commit-action',
        'devkit',
        'devkit-smoke-test',
        'h5v',
        'org-config',
        'scitadel',
        'sync-issues-action',
      ],
      value: '********',
      visibility: 'selected',
    },
    // Now NARROWER than the client-ID list: the devkit 1.7.0 adoptions
    // re-scaffolded `sync-issues.yml` from `app-id` to `client-id` in devkit,
    // devkit-smoke-test and org-config (2026-08-10 sweep of every live
    // workflow tree). commit-action and sync-issues-action still pass the
    // numeric form in their pre-1.7 `sync-issues.yml`; h5v
    // (DEVCONTAINER_VERSION=0.3.1) and scitadel (0.3.3) are legacy throughout.
    // Each entry retires with its repo's 1.7 adoption or re-scaffold; the
    // secret retires entirely at the end (#112).
    orgs.newOrgSecret('COMMIT_APP_ID') {
      selected_repositories+: [
        'commit-action',
        'h5v',
        'scitadel',
        'sync-issues-action',
      ],
      value: '********',
      visibility: 'selected',
    },
    // Union of the client-ID and numeric-ID consumer lists — every repo that
    // mints a commit-app token needs the key regardless of which ID form it
    // uses (#123).
    orgs.newOrgSecret('COMMIT_APP_PRIVATE_KEY') {
      selected_repositories+: [
        'commit-action',
        'devkit',
        'devkit-smoke-test',
        'h5v',
        'org-config',
        'scitadel',
        'sync-issues-action',
      ],
      value: '********',
      visibility: 'selected',
    },
    // Consumed since the devkit 1.7.0 adoptions landed vig-os/devkit#1365's
    // DEVKIT_UPGRADE_APP_ID -> _CLIENT_ID rename: devkit-smoke-test and
    // org-config reference it today. commit-action and sync-issues-action keep
    // their pre-seeded entries for their own 1.7 adoption; h5v and scitadel
    // are pre-seeded ahead of their re-scaffold (#112, #123).
    orgs.newOrgSecret('DEVKIT_UPGRADE_APP_CLIENT_ID') {
      selected_repositories+: [
        'commit-action',
        'devkit-smoke-test',
        'h5v',
        'org-config',
        'scitadel',
        'sync-issues-action',
      ],
      value: '********',
      visibility: 'selected',
    },
    // MAINTENANCE COUPLING: exactly the repos whose scaffolded
    // `.github/workflows/devkit-upgrade.yml` still passes the numeric App ID
    // (pre-1.7 scaffolds; devkit-smoke-test and org-config reference both
    // forms transitionally). devkit itself is the source and does not upgrade
    // itself; h5v and scitadel predate the workflow. Any repo (re-)scaffolded
    // to devkit >= 1.6 MUST be listed on whichever ID form its scaffold uses
    // (numeric here, client-ID above for >= 1.7) or its upgrade workflow fails
    // with an empty credential and no error. Once visibility is `selected`,
    // the list is editable without the secret value via
    // `PUT /orgs/vig-os/actions/secrets/<NAME>/repositories` (#123).
    orgs.newOrgSecret('DEVKIT_UPGRADE_APP_ID') {
      selected_repositories+: [
        'commit-action',
        'devkit-smoke-test',
        'org-config',
        'sync-issues-action',
      ],
      value: '********',
      visibility: 'selected',
    },
    // Union of the numeric-ID and client-ID consumer lists (same maintenance
    // coupling as above): h5v and scitadel carry the key alongside their
    // pre-seeded _CLIENT_ID entries (#112, #123).
    orgs.newOrgSecret('DEVKIT_UPGRADE_APP_PRIVATE_KEY') {
      selected_repositories+: [
        'commit-action',
        'devkit-smoke-test',
        'h5v',
        'org-config',
        'scitadel',
        'sync-issues-action',
      ],
      value: '********',
      visibility: 'selected',
    },
    // Pilot for the org-wide visibility migration (#123). No workflow anywhere
    // in the org reads this secret — it is written by `otterdog apply` from the
    // committed SOPS ciphertext and exists only to prove that pipeline — so
    // `org-config` is the whole audience. Unlike the other nine org secrets,
    // its value is a real credential-provider reference rather than a
    // `'********'` dummy, so `include_for_live_patch` is true and apply can set
    // visibility declaratively (secret.py:88).
    orgs.newOrgSecret('ORG_CONFIG_CANARY') {
      selected_repositories+: [
        'org-config',
      ],
      value: 'pass:org-config/ORG_CONFIG_CANARY',
      visibility: 'selected',
    },
    // The five devkit-scaffolded repos, plus h5v and scitadel pre-seeded ahead
    // of their re-scaffold off RELEASE_APP_ID (#112, #123).
    orgs.newOrgSecret('RELEASE_APP_CLIENT_ID') {
      selected_repositories+: [
        'commit-action',
        'devkit',
        'devkit-smoke-test',
        'h5v',
        'org-config',
        'scitadel',
        'sync-issues-action',
      ],
      value: '********',
      visibility: 'selected',
    },
    // Only the two legacy-scaffold repos still using the numeric App ID form.
    // This secret retires entirely once both are re-scaffolded (#112).
    orgs.newOrgSecret('RELEASE_APP_ID') {
      selected_repositories+: [
        'h5v',
        'scitadel',
      ],
      value: '********',
      visibility: 'selected',
    },
    // Union of the client-ID and numeric-ID release consumers (#123).
    orgs.newOrgSecret('RELEASE_APP_PRIVATE_KEY') {
      selected_repositories+: [
        'commit-action',
        'devkit',
        'devkit-smoke-test',
        'h5v',
        'org-config',
        'scitadel',
        'sync-issues-action',
      ],
      value: '********',
      visibility: 'selected',
    },
  ],
  // Override (not `+::`) the base template's default `_repositories` list so its
  // Eclipse `.eclipsefdn` example repo is not declared for vig-os (drift-free).
  _repositories:: [
    orgs.newRepo('commit-action') {
      allow_auto_merge: true,
      custom_properties+: {
        type: ['tools'],
      },
      description: 'GitHub Action that commits changes via GitHub API or GitHub Token, creating automatically signed commits. Modular TypeScript design - use as a standalone action or import as a library.',
      has_projects: false,
      has_wiki: false,
      private_vulnerability_reporting_enabled: true,
      workflows+: {
        actions_can_approve_pull_request_reviews: false,
      },
      rulesets: [
        orgs.newRepoRuleset('Dev protection') {
          allows_creations: true,
          bypass_actors+: [
            'commit-action-bot',
          ],
          include_refs+: [
            'refs/heads/dev',
          ],
          required_pull_request+: {
            required_approving_review_count: 0,
            requires_review_thread_resolution: true,
          },
          required_status_checks+: {
            status_checks: [
              // Canonical status-check prefix form is PER-APP, throughout this
              // file (#69): checks bound to FIRST-PARTY apps that are never org
              // installations (github-actions, app_id 15368) MUST use the
              // numeric `15368:` form — otterdog's id->slug resolution covers
              // only `/orgs/{org}/installations`, so live always reads back
              // numeric and a committed slug is a permanent phantom plan diff
              // (#130-#141). Checks from org-installed apps DO resolve to slugs
              // and use slug form (cf. tessera's `any:` note). Writing the
              // numeric form needs otterdog >= 1.4.0 (upstream #695/#700); the
              // pin lives in justfile.project.
              '15368:CI Summary',
            ],
          },
        },
        orgs.newRepoRuleset('Main protection') {
          allows_creations: true,
          bypass_actors+: [
            '#RepositoryAdmin:pull_request',
          ],
          include_refs+: [
            'refs/heads/main',
          ],
          requires_commit_signatures: true,
          required_pull_request+: {
            required_approving_review_count: 1,
            requires_review_thread_resolution: true,
          },
          required_status_checks+: {
            status_checks: [
              '15368:CI Summary',
              '15368:Dist Check',
            ],
            strict: true,
          },
        },
        orgs.newRepoRuleset('Release protection') {
          allows_creations: true,
          allows_deletions: true,
          bypass_actors+: [
            'commit-action-bot',
          ],
          include_refs+: [
            'refs/heads/release/*',
          ],
          required_pull_request+: {
            required_approving_review_count: 0,
            requires_review_thread_resolution: true,
          },
          required_status_checks+: {
            status_checks: [
              '15368:CI Summary',
              '15368:Dist Check',
            ],
          },
        },
        orgs.newRepoRuleset('Signed commits') {
          allows_creations: true,
          allows_deletions: true,
          allows_force_pushes: true,
          include_refs+: [
            '~ALL',
          ],
          required_pull_request: null,
          required_status_checks: null,
          requires_commit_signatures: true,
        },
        orgs.newRepoRuleset('Tag protection') {
          allows_force_pushes: true,
          allows_updates: false,
          bypass_actors+: [
            'vig-os-release-app',
          ],
          include_refs+: [
            '~ALL',
          ],
          required_pull_request: null,
          required_status_checks: null,
          target: 'tag',
        },
      ],
    },
    orgs.newRepo('devkit') {
      allow_auto_merge: true,
      custom_properties+: {
        type: ['internal', 'tools'],
      },
      dependabot_security_updates_enabled: true,
      description: 'Reproducible dev environment (devcontainer or Nix/direnv) with batteries-included tooling and good practices.',
      has_discussions: true,
      has_projects: false,
      has_wiki: false,
      homepage: '',
      private_vulnerability_reporting_enabled: true,
      topics+: [
        'devcontainer',
        'devkit',
        'direnv',
        'good-practices',
        'nix',
        'tools',
      ],
      workflows+: {
        actions_can_approve_pull_request_reviews: false,
      },
      secrets: [
        orgs.newRepoSecret('CACHIX_AUTH_TOKEN') {
          value: '********',
        },
      ],
      variables: [
        orgs.newRepoVariable('CACHIX_CACHE') {
          value: 'vig-os',
        },
      ],
      rulesets: [
        orgs.newRepoRuleset('Dev protection') {
          allows_creations: true,
          bypass_actors+: [
            '#OrganizationAdmin',
            'commit-action-bot',
          ],
          include_refs+: [
            'refs/heads/dev',
          ],
          required_pull_request+: {
            required_approving_review_count: 0,
            requires_review_thread_resolution: true,
          },
          required_status_checks+: {
            status_checks: [
              '15368:Test Summary',
            ],
          },
        },
        orgs.newRepoRuleset('Main protection') {
          allows_creations: true,
          bypass_actors+: [
            '#OrganizationAdmin',
          ],
          include_refs+: [
            'refs/heads/main',
          ],
          required_pull_request+: {
            // An approval must cover the code being merged: without this, a
            // review of one commit survives every later push to the branch.
            // Main only — Dev and Release require 0 approvals, so they have
            // nothing to dismiss (#118).
            dismisses_stale_reviews: true,
            required_approving_review_count: 1,
            // Deliberately off: `.github/CODEOWNERS` names a single owner who
            // also authors the PRs, so the gate can never be satisfied and its
            // only outcome is an #OrganizationAdmin bypass (#115).
            requires_code_owner_review: false,
            requires_review_thread_resolution: true,
          },
          required_status_checks+: {
            status_checks: [
              // Two contexts, not one: `codeql.yml`'s analyze job is a
              // `language: ['python', 'actions']` matrix, so each leg reports
              // under its own matrix-suffixed name (#115).
              '15368:CodeQL Analysis (actions)',
              '15368:CodeQL Analysis (python)',
              '15368:Test Summary',
            ],
            strict: true,
          },
        },
        orgs.newRepoRuleset('Release protection') {
          allows_creations: true,
          allows_deletions: true,
          bypass_actors+: [
            '#OrganizationAdmin',
            'commit-action-bot',
          ],
          include_refs+: [
            'refs/heads/release/*',
          ],
          required_pull_request+: {
            required_approving_review_count: 0,
            // Deliberately off, same rationale as Main protection (#115).
            requires_code_owner_review: false,
            requires_review_thread_resolution: true,
          },
          required_status_checks+: {
            status_checks: [
              '15368:Test Summary',
            ],
          },
        },
        orgs.newRepoRuleset('Signed commits') {
          allows_creations: true,
          allows_deletions: true,
          allows_force_pushes: true,
          include_refs+: [
            '~ALL',
          ],
          required_pull_request: null,
          required_status_checks: null,
          requires_commit_signatures: true,
        },
        // Tag protection mirrors commit-action's: devkit publishes the release
        // tags every consumer pins, and `release.yml` is the only tag writer —
        // it pushes (and `promote-release.yml` prunes RC tags) with a
        // vig-os-release-app token, so one always-bypass actor is enough.
        orgs.newRepoRuleset('Tag protection') {
          allows_force_pushes: true,
          allows_updates: false,
          bypass_actors+: [
            'vig-os-release-app',
          ],
          include_refs+: [
            '~ALL',
          ],
          required_pull_request: null,
          required_status_checks: null,
          target: 'tag',
        },
      ],
      environments: [
        orgs.newEnvironment('copilot'),
      ],
    },
    orgs.newRepo('devkit-smoke-test') {
      allow_auto_merge: true,
      description: 'Repository to test deployment workflows of vigOS devcontainer',
      private_vulnerability_reporting_enabled: true,
      rulesets: [
        orgs.newRepoRuleset('Dev protection') {
          allows_creations: true,
          bypass_actors+: [
            'commit-action-bot',
          ],
          include_refs+: [
            'refs/heads/dev',
          ],
          required_pull_request+: {
            required_approving_review_count: 0,
            requires_code_owner_review: true,
            requires_review_thread_resolution: true,
          },
          required_status_checks+: {
            status_checks: [
              '15368:CI Summary',
            ],
          },
        },
        orgs.newRepoRuleset('Main protection') {
          allows_creations: true,
          // Parity with devkit's Main protection: a sanctioned always-mode
          // admin override instead of out-of-band ruleset PUTs that the next
          // apply reverts (#147).
          bypass_actors+: [
            '#OrganizationAdmin',
          ],
          include_refs+: [
            'refs/heads/main',
          ],
          required_pull_request+: {
            // No human review: the repo is bot-authored release-validation
            // scaffolding, and the dispatch listener's approval gate that
            // needed `reviewDecision` to be computable (vig-os/devkit#1391)
            // is removed by vig-os/devkit#1506. The operative controls are
            // the required CI Summary check and devkit's published-smoke-
            // release validation at promote; count-0-with-required-checks
            // matches devkit's own Dev and Release protections (#167).
            required_approving_review_count: 0,
          },
          required_status_checks+: {
            status_checks: [
              '15368:CI Summary',
            ],
          },
        },
        orgs.newRepoRuleset('Signed commits') {
          allows_creations: true,
          allows_deletions: true,
          allows_force_pushes: true,
          include_refs+: [
            '~ALL',
          ],
          required_pull_request: null,
          required_status_checks: null,
          requires_commit_signatures: true,
        },
      ],
    },
    orgs.newRepo('h5v') {
      allow_update_branch: false,
      delete_branch_on_merge: false,
      description: 'A terminal viewer for HDF5 files with chart, image, string, matrix, and attributes support',
      secret_scanning: 'disabled',
      secret_scanning_push_protection: 'disabled',
    } + orgs.legacyMergePolicy,
    orgs.newRepo('nvd-mirror') {
      allow_update_branch: false,
      delete_branch_on_merge: false,
      description: 'Public mirror of the NVD JSON 2.0 feeds for vulnix (see vig-os/devcontainer#870)',
      gh_pages_build_type: 'legacy',
      gh_pages_source_branch: 'gh-pages',
      gh_pages_source_path: '/',
      secret_scanning: 'disabled',
      secret_scanning_push_protection: 'disabled',
      environments: [
        orgs.newEnvironment('github-pages') {
          branch_policies+: [
            'gh-pages',
            'main',
          ],
          deployment_branch_policy: 'selected',
        },
      ],
    } + orgs.legacyMergePolicy,
    orgs.newRepo('org-config') {
      allow_auto_merge: true,
      custom_properties+: {
        type: ['tools'],
      },
      description: 'GitHub Organization Management',
      has_projects: false,
      has_wiki: false,
      // Template repo: downstream orgs' private org-config repos are created
      // from this one (ADR-0006; marked live via one-time gh API action, #52).
      is_template: true,
      secret_scanning: 'disabled',
      secret_scanning_push_protection: 'disabled',
      secrets: [
        orgs.newRepoSecret('ORG_CONFIG_APP_CLIENT_ID') {
          value: '********',
        },
        orgs.newRepoSecret('ORG_CONFIG_APP_PRIVATE_KEY') {
          value: '********',
        },
        orgs.newRepoSecret('SOPS_AGE_KEY') {
          value: '********',
        },
      ],
      environments: [
        orgs.newEnvironment('production') {
          branch_policies+: [
            'main',
          ],
          deployment_branch_policy: 'selected',
          reviewers+: [
            '@c-vigo',
          ],
        },
      ],
      rulesets: [
        orgs.newRepoRuleset('Main protection') {
          allows_creations: true,
          bypass_actors+: [
            '#OrganizationAdmin',
          ],
          include_refs+: [
            'refs/heads/main',
          ],
          required_pull_request+: {
            // No human review: the repo is solo-maintained, so an approval
            // (and the single-owner CODEOWNERS gate) is unsatisfiable on
            // self-authored PRs and its only outcome was a routine
            // #OrganizationAdmin bypass on every merge — the #115 pathology.
            // The operative controls are the required CI Summary check and
            // the `production` environment approval (@c-vigo) that gates every
            // live apply with the plan preview in the same run;
            // count-0-with-required-checks matches devkit's Dev and Release
            // protections and devkit-smoke-test's Main (#167, #195).
            required_approving_review_count: 0,
            requires_code_owner_review: false,
            requires_review_thread_resolution: true,
          },
          required_status_checks+: {
            status_checks: [
              '15368:CI Summary',
            ],
          },
        },
        orgs.newRepoRuleset('Signed commits') {
          allows_creations: true,
          allows_deletions: true,
          allows_force_pushes: true,
          include_refs+: [
            '~ALL',
          ],
          required_pull_request: null,
          required_status_checks: null,
          requires_commit_signatures: true,
        },
      ],
    },
    orgs.newRepo('org-config-testbed') {
      // SACRIFICIAL L3 mutation-E2E target (issue #23, ADR-0007 Axis C). Being
      // declared here is what makes it a valid test target: apply creates it,
      // and .github/workflows/testbed-e2e.yml churns + reverts its live state on
      // a schedule. Only the description is overridden; every other field keeps
      // the vendored `newRepo` default, all of whose lists (webhooks/secrets/
      // variables/environments/rulesets/branch_protection_rules) are empty — so
      // there is nothing seeded to re-inject and the evaluated config is
      // drift-free-by-construction (the next plan shows exactly one `+ repo`).
      // `orgs.upstreamMergePolicy` below restores the vendored merge fields that
      // the house overlay would otherwise impose, keeping that property exact.
      // The description string is duplicated verbatim into testbed-e2e.yml's
      // `TESTBED_DESCRIPTION` (its consistency-guard step greps for it here), so
      // the harness reverts induced drift back to this declared value.
      description: 'SACRIFICIAL testbed for the L3 mutation E2E harness (issue #23) - its live settings are deliberately churned and reverted by .github/workflows/testbed-e2e.yml on every run; do not rely on any state here.',
    } + orgs.upstreamMergePolicy,
    orgs.newRepo('qms') {
      allow_forking: false,
      allow_update_branch: false,
      custom_properties+: {
        type: ['tools'],
      },
      default_branch: 'worktree-agent-ab0adbce',
      delete_branch_on_merge: false,
      description: 'Quality Management System',
      has_wiki: false,
      private: true,
    } + orgs.legacyMergePolicy,
    orgs.newRepo('qx') {
      allow_update_branch: false,
      delete_branch_on_merge: false,
      description: 'Per-instance physical part identification: nano-id IDs, QR labels, mint-then-bind workflow',
      gh_pages_build_type: 'workflow',
      homepage: 'https://vig-os.github.io/qx/',
      secret_scanning: 'disabled',
      secret_scanning_push_protection: 'disabled',
      secrets: [
        orgs.newRepoSecret('PARTREG_TEST_PAT') {
          value: '********',
        },
      ],
      environments: [
        orgs.newEnvironment('github-pages') {
          branch_policies+: [
            'main',
          ],
          deployment_branch_policy: 'selected',
        },
      ],
    } + orgs.legacyMergePolicy,
    orgs.newRepo('scitadel') {
      allow_auto_merge: true,
      // Deliberate deviation from the house merge policy (house-defaults.libsonnet):
      // scitadel merges by squash, keeping the house PR_TITLE/PR_BODY wording on
      // the squash commit instead of the merge commit.
      allow_merge_commit: false,
      allow_squash_merge: true,
      allow_update_branch: false,
      description: 'Scitadel: programmable, reproducible scientific literature retrieval',
      secret_scanning: 'disabled',
      secret_scanning_push_protection: 'disabled',
      squash_merge_commit_message: 'PR_BODY',
      squash_merge_commit_title: 'PR_TITLE',
      secrets: [
        orgs.newRepoSecret('CARGO_REGISTRY_TOKEN') {
          value: '********',
        },
        orgs.newRepoSecret('RELEASE_BOT_PRIVATE_KEY') {
          value: '********',
        },
        orgs.newRepoSecret('RELEASE_PLEASE_TOKEN') {
          value: '********',
        },
      ],
      variables: [
        orgs.newRepoVariable('RELEASE_BOT_APP_ID') {
          value: '3931309',
        },
      ],
      rulesets: [
        orgs.newRepoRuleset('dev protection') {
          allows_creations: true,
          include_refs+: [
            'refs/heads/dev',
          ],
          required_pull_request+: {
            required_approving_review_count: 0,
            requires_review_thread_resolution: true,
          },
          required_status_checks+: {
            status_checks: [
              'Lint',
              'Test (ubuntu-latest)',
            ],
            strict: true,
          },
        },
        orgs.newRepoRuleset('main protection') {
          allows_creations: true,
          include_refs+: [
            'refs/heads/main',
          ],
          required_pull_request+: {
            required_approving_review_count: 0,
            requires_review_thread_resolution: true,
          },
          required_status_checks+: {
            status_checks: [
              'Lint',
              'Test (macos-latest)',
              'Test (ubuntu-latest)',
            ],
            strict: true,
          },
        },
      ],
      environments: [
        orgs.newEnvironment('crates-io'),
      ],
    },
    orgs.newRepo('sync-issues-action') {
      allow_auto_merge: true,
      allow_update_branch: false,
      custom_properties+: {
        type: ['tools'],
      },
      description: 'GitHub Action that syncs issues and pull requests to markdown files with full comments, review threads, and diff snippets. Useful for documentation, backups, and offline access. Supports incremental syncing with state caching and GitHub App authentication.',
      private_vulnerability_reporting_enabled: true,
      rulesets: [
        orgs.newRepoRuleset('Dev protection') {
          allows_creations: true,
          bypass_actors+: [
            'commit-action-bot',
          ],
          include_refs+: [
            'refs/heads/dev',
          ],
          required_pull_request+: {
            required_approving_review_count: 0,
            requires_code_owner_review: true,
            requires_review_thread_resolution: true,
          },
          required_status_checks+: {
            status_checks: [
              '15368:CI Summary',
            ],
          },
        },
        orgs.newRepoRuleset('Main protection') {
          allows_creations: true,
          include_refs+: [
            'refs/heads/main',
          ],
          required_pull_request+: {
            // An approval must cover the code being merged: without this, a
            // review of one commit survives every later push to the branch.
            // Main only — Dev and Release require 0 approvals, so they have
            // nothing to dismiss (#118, converged here by #184).
            dismisses_stale_reviews: true,
            required_approving_review_count: 1,
            requires_code_owner_review: true,
            requires_review_thread_resolution: true,
          },
          required_status_checks+: {
            status_checks: [
              '15368:CI Summary',
              '15368:Dist Check',
            ],
          },
        },
        orgs.newRepoRuleset('Release protection') {
          allows_creations: true,
          allows_deletions: true,
          bypass_actors+: [
            'commit-action-bot',
          ],
          include_refs+: [
            'refs/heads/release/*',
          ],
          required_pull_request+: {
            required_approving_review_count: 0,
            requires_review_thread_resolution: true,
          },
          required_status_checks+: {
            status_checks: [
              '15368:CI Summary',
              '15368:Dist Check',
            ],
          },
        },
        orgs.newRepoRuleset('Signed commits') {
          allows_creations: true,
          allows_deletions: true,
          allows_force_pushes: true,
          include_refs+: [
            '~ALL',
          ],
          required_pull_request: null,
          required_status_checks: null,
          requires_commit_signatures: true,
        },
        orgs.newRepoRuleset('Tag protection') {
          allows_force_pushes: true,
          allows_updates: false,
          bypass_actors+: [
            'vig-os-release-app',
          ],
          include_refs+: [
            '~ALL',
          ],
          required_pull_request: null,
          required_status_checks: null,
          target: 'tag',
        },
      ],
      environments: [
        orgs.newEnvironment('copilot'),
      ],
    },
    orgs.newRepo('tessera') {
      allow_auto_merge: true,
      // Deliberate deviation from the house merge policy (house-defaults.libsonnet):
      // rebase and squash stay available alongside merge commits.
      allow_rebase_merge: true,
      allow_squash_merge: true,
      allow_update_branch: false,
      delete_branch_on_merge: false,
      description: 'FAIR Data on HDF5 — self-describing, FAIR-principled data format for scientific data products',
      private_vulnerability_reporting_enabled: true,
      // Credentials of the repo-scoped `tessera-sync-issues-bot` GitHub App
      // (app_id 4483218), NOT the org-wide sync-issues App — same secret names,
      // different App identity, so do not "deduplicate" these into org secrets.
      secrets: [
        orgs.newRepoSecret('APP_SYNC_ISSUES_ID') {
          value: '********',
        },
        orgs.newRepoSecret('APP_SYNC_ISSUES_PRIVATE_KEY') {
          value: '********',
        },
      ],
      branch_protection_rules: [
        orgs.newBranchProtectionRule('dev') {
          required_approving_review_count: null,
          // Deliberately un-prefixed: the live check is app-bound (app_id
          // 15368), which otterdog serializes without the `any:` prefix.
          required_status_checks: [
            'nix flake check',
          ],
          requires_pull_request: false,
        },
        orgs.newBranchProtectionRule('main') {
          required_approving_review_count: null,
          required_status_checks: [
            'any:nix flake check',
          ],
          requires_pull_request: false,
          requires_strict_status_checks: true,
        },
      ],
    },
    orgs.newRepo('vigos-mvp') {
      allow_update_branch: false,
      delete_branch_on_merge: false,
      description: 'MVP with basic functions',
      private_vulnerability_reporting_enabled: true,
    } + orgs.legacyMergePolicy,
    orgs.newRepo('vs-dolt') {
      allow_update_branch: false,
      delete_branch_on_merge: false,
      description: 'VS Code extension, open source SQL workbench for your MySQL and PostgreSQL compatible database with version control features when connected to Dolt.',
      has_issues: false,
      homepage: 'https://hub.docker.com/r/dolthub/dolt-workbench',
      private_vulnerability_reporting_enabled: true,
    } + orgs.legacyMergePolicy,
  ],
}
