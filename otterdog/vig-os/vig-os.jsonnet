local orgs = import 'vendor/otterdog-defaults/otterdog-defaults.libsonnet';

orgs.newOrg('vig-os', 'vig-os') {
  settings+: {
    billing_email: 'carlos.vigo@exoma.ch',
    default_repository_permission: 'read',
    description: 'Versatile Instrumentation and Governance Operating Stack',
    location: 'Switzerland',
    members_can_create_private_repositories: true,
    members_can_create_public_repositories: true,
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
  },
  teams: [],
  secrets+: [
    orgs.newOrgSecret('APP_SYNC_ISSUES_ID') {
      value: '********',
    },
    orgs.newOrgSecret('APP_SYNC_ISSUES_PRIVATE_KEY') {
      value: '********',
    },
    orgs.newOrgSecret('COMMIT_APP_CLIENT_ID') {
      value: '********',
    },
    orgs.newOrgSecret('COMMIT_APP_ID') {
      value: '********',
    },
    orgs.newOrgSecret('COMMIT_APP_PRIVATE_KEY') {
      value: '********',
    },
    orgs.newOrgSecret('DOCKERHUB_TOKEN') {
      value: '********',
    },
    orgs.newOrgSecret('DOCKERHUB_USERNAME') {
      value: '********',
    },
    orgs.newOrgSecret('RELEASE_APP_CLIENT_ID') {
      value: '********',
    },
    orgs.newOrgSecret('RELEASE_APP_ID') {
      value: '********',
    },
    orgs.newOrgSecret('RELEASE_APP_PRIVATE_KEY') {
      value: '********',
    },
  ],
  // Override (not `+::`) the base template's default `_repositories` list so its
  // Eclipse `.eclipsefdn` example repo is not declared for vig-os (drift-free).
  _repositories:: [
    orgs.newRepo('commit-action') {
      allow_auto_merge: true,
      allow_merge_commit: true,
      allow_rebase_merge: false,
      allow_squash_merge: false,
      custom_properties+: {
        type: ['tools'],
      },
      description: 'GitHub Action that commits changes via GitHub API or GitHub Token, creating automatically signed commits. Modular TypeScript design - use as a standalone action or import as a library.',
      has_projects: false,
      has_wiki: false,
      merge_commit_message: 'PR_BODY',
      merge_commit_title: 'PR_TITLE',
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
      allow_merge_commit: true,
      allow_rebase_merge: false,
      allow_squash_merge: false,
      custom_properties+: {
        type: ['internal', 'tools'],
      },
      dependabot_security_updates_enabled: true,
      description: 'Reproducible dev environment (devcontainer or Nix/direnv) with batteries-included tooling and good practices.',
      has_discussions: true,
      has_projects: false,
      has_wiki: false,
      homepage: '',
      merge_commit_message: 'PR_BODY',
      merge_commit_title: 'PR_TITLE',
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
          include_refs+: [
            'refs/heads/main',
          ],
          required_pull_request+: {
            required_approving_review_count: 1,
            requires_code_owner_review: true,
            requires_review_thread_resolution: true,
          },
          required_status_checks+: {
            status_checks: [
              '15368:Test Summary',
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
            requires_code_owner_review: true,
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
      ],
      environments: [
        orgs.newEnvironment('copilot'),
      ],
    },
    orgs.newRepo('devkit-smoke-test') {
      allow_auto_merge: true,
      allow_merge_commit: true,
      allow_rebase_merge: false,
      allow_squash_merge: false,
      description: 'Repository to test deployment workflows of vigOS devcontainer',
      merge_commit_message: 'PR_BODY',
      merge_commit_title: 'PR_TITLE',
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
      allow_merge_commit: true,
      allow_update_branch: false,
      delete_branch_on_merge: false,
      description: 'A terminal viewer for HDF5 files with chart, image, string, matrix, and attributes support',
      secret_scanning: 'disabled',
      secret_scanning_push_protection: 'disabled',
    },
    orgs.newRepo('meta') {
      allow_merge_commit: true,
      allow_update_branch: false,
      code_scanning_default_setup_enabled: true,
      default_branch: 'dev',
      delete_branch_on_merge: false,
      description: 'vigOS coordination: discussions, guidelines, architecture, roadmap, and general tasks.',
      private_vulnerability_reporting_enabled: true,
      rulesets: [
        orgs.newRepoRuleset('Main protection') {
          allows_creations: true,
          include_refs+: [
            'refs/heads/main',
          ],
          required_status_checks: null,
          requires_commit_signatures: true,
          required_pull_request+: {
            required_approving_review_count: 0,
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
    orgs.newRepo('nvd-mirror') {
      allow_merge_commit: true,
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
    },
    orgs.newRepo('org-config') {
      allow_auto_merge: true,
      allow_merge_commit: true,
      allow_rebase_merge: false,
      allow_squash_merge: false,
      custom_properties+: {
        type: ['tools'],
      },
      description: 'GitHub Organization Management',
      has_projects: false,
      has_wiki: false,
      merge_commit_message: 'PR_BODY',
      merge_commit_title: 'PR_TITLE',
      secret_scanning: 'disabled',
      secret_scanning_push_protection: 'disabled',
      secrets: [
        orgs.newRepoSecret('ORG_CONFIG_APP_CLIENT_ID') {
          value: '********',
        },
        orgs.newRepoSecret('ORG_CONFIG_APP_PRIVATE_KEY') {
          value: '********',
        },
      ],
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
            required_approving_review_count: 1,
            requires_code_owner_review: true,
            requires_review_thread_resolution: true,
          },
          required_status_checks+: {
            status_checks: [
              '15368:CI Summary',
            ],
          },
        },
      ],
    },
    orgs.newRepo('os-config') {
      allow_merge_commit: true,
      allow_update_branch: false,
      code_scanning_default_languages+: [
        'python',
      ],
      code_scanning_default_setup_enabled: true,
      custom_properties+: {
        type: ['tools'],
      },
      delete_branch_on_merge: false,
      description: 'Reproducible OS configuration with for medtech-compliant deployments. Security hardening, audit logging, and ISO generation for air-gapped environments.',
      private_vulnerability_reporting_enabled: true,
    },
    orgs.newRepo('part-registry') {
      allow_auto_merge: true,
      allow_merge_commit: true,
      allow_rebase_merge: false,
      allow_squash_merge: false,
      allow_update_branch: false,
      custom_properties+: {
        type: ['tools'],
      },
      description: 'Registry of components, parts, assemblies',
      is_template: true,
      merge_commit_message: 'PR_BODY',
      merge_commit_title: 'PR_TITLE',
      secret_scanning: 'disabled',
      secret_scanning_push_protection: 'disabled',
      rulesets: [
        orgs.newRepoRuleset('Dev protection') {
          allows_creations: true,
          bypass_actors+: [
            'commit-action-bot',
          ],
          include_refs+: [
            'refs/heads/dev',
          ],
          required_status_checks: null,
          required_pull_request+: {
            required_approving_review_count: 0,
            requires_code_owner_review: true,
            requires_review_thread_resolution: true,
          },
        },
        orgs.newRepoRuleset('Main protection') {
          allows_creations: true,
          include_refs+: [
            'refs/heads/main',
          ],
          required_status_checks: null,
          required_pull_request+: {
            required_approving_review_count: 1,
            requires_code_owner_review: true,
            requires_review_thread_resolution: true,
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
    orgs.newRepo('qms') {
      allow_forking: false,
      allow_merge_commit: true,
      allow_update_branch: false,
      custom_properties+: {
        type: ['tools'],
      },
      default_branch: 'worktree-agent-ab0adbce',
      delete_branch_on_merge: false,
      description: 'Quality Management System',
      has_wiki: false,
      private: true,
    },
    orgs.newRepo('qx') {
      allow_merge_commit: true,
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
    },
    orgs.newRepo('scitadel') {
      allow_auto_merge: true,
      allow_rebase_merge: false,
      allow_update_branch: false,
      description: 'Scitadel: programmable, reproducible scientific literature retrieval',
      merge_commit_message: 'PR_BODY',
      merge_commit_title: 'PR_TITLE',
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
      allow_merge_commit: true,
      allow_rebase_merge: false,
      allow_squash_merge: false,
      allow_update_branch: false,
      custom_properties+: {
        type: ['tools'],
      },
      description: 'GitHub Action that syncs issues and pull requests to markdown files with full comments, review threads, and diff snippets. Useful for documentation, backups, and offline access. Supports incremental syncing with state caching and GitHub App authentication.',
      merge_commit_message: 'PR_BODY',
      merge_commit_title: 'PR_TITLE',
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
      allow_merge_commit: true,
      allow_update_branch: false,
      code_scanning_default_setup_enabled: true,
      delete_branch_on_merge: false,
      description: 'FAIR Data on HDF5 — self-describing, FAIR-principled data format for scientific data products',
      merge_commit_message: 'PR_BODY',
      merge_commit_title: 'PR_TITLE',
      private_vulnerability_reporting_enabled: true,
      branch_protection_rules: [
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
      allow_merge_commit: true,
      allow_update_branch: false,
      code_scanning_default_languages+: [
        'python',
      ],
      code_scanning_default_setup_enabled: true,
      delete_branch_on_merge: false,
      description: 'MVP with basic functions',
      private_vulnerability_reporting_enabled: true,
    },
    orgs.newRepo('vs-dolt') {
      allow_merge_commit: true,
      allow_update_branch: false,
      code_scanning_default_languages+: [
        'javascript-typescript',
      ],
      code_scanning_default_setup_enabled: true,
      delete_branch_on_merge: false,
      description: 'VS Code extension, open source SQL workbench for your MySQL and PostgreSQL compatible database with version control features when connected to Dolt.',
      has_issues: false,
      homepage: 'https://hub.docker.com/r/dolthub/dolt-workbench',
      private_vulnerability_reporting_enabled: true,
    },
  ],
}
