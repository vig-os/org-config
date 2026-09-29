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
    // credential on day one and without another list edit (#123). tessera
    // joins from its devkit 1.16.0 scaffold (#252, tessera#364) and is the
    // first repo here on the client-ID form FROM DAY ONE — its
    // `sync-issues.yml` reads `client-id:` with no numeric fallback, so it is
    // deliberately absent from COMMIT_APP_ID below and leaves nothing for
    // #112 to retire.
    orgs.newOrgSecret('COMMIT_APP_CLIENT_ID') {
      selected_repositories+: [
        'commit-action',
        'devkit',
        'devkit-smoke-test',
        'h5v',
        'org-config',
        'scitadel',
        'sync-issues-action',
        'tessera',
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
        'tessera',
      ],
      value: '********',
      visibility: 'selected',
    },
    // APP VISIBILITY DECISION (2026-09-28, #271; the UI verification it
    // was pending was taken the same day, #291): keep the
    // `vigos-devkit-upgrade` App PUBLIC — "Any account". That is now a
    // reading and not a hedge. An owner of the `vig-os` organization
    // opened Settings -> Developer settings -> GitHub Apps ->
    // vigos-devkit-upgrade -> Advanced on 2026-09-28 and read, under
    // Danger zone, three controls in this order: "Transfer ownership of
    // this GitHub App", "Delete this GitHub App", "Make this GitHub App
    // private" — the third GREYED OUT, subtitled "Private GitHub Apps
    // cannot be installed on other accounts." The button names the
    // ACTION, not the state, so the live value is public. Recorded here
    // because this file is the App's only appearance in code anywhere;
    // the engine App's twin decision, whose shape this follows — and
    // whose own reading of the same day this one confirms — is
    // docs/runbooks/github-app.md, Visibility (#261, #290), and
    // `vig-os/devkit`, which scaffolds the workflow that consumes these
    // secrets, has no runbook for this App at all (its own creation
    // runbook is vig-os/devkit#1739, the follow-up this decision
    // deliberately did not grow into).
    //
    // Public is not a preference here, and it is not currently
    // reversible either. GitHub states the constraint — "Public apps
    // cannot be made private if they're installed on other accounts"
    // (Modifying a GitHub App registration, "Changing the visibility of
    // a GitHub App") — and the greyed-out control above is that
    // documented rule enforced in the product. This App has TWO such
    // installations, one more than the engine App. Re-verified
    // 2026-09-28 with `gh api /orgs/<org>/installations` across all four
    // orgs: it is installed on its owner `vig-os` (installation
    // 150058891, created 2026-07-30) and on the FOREIGN orgs `exo-pet`
    // (151387251, 2026-08-05) and `exoma-ch` (162764177, 2026-09-18),
    // while `MorePET` carries none. Private means installable only on
    // the account that owns the App, so neither foreign installation
    // could exist if it were private — the same one-App/N-installations
    // model ADR-0004 chose under "One App, not four".
    //
    // THE FLIP IS UNINSTALL-GATED IN TWO ORGS, sequentially, and the
    // outage is a precondition to the button being clickable at all
    // rather than a consequence of clicking it: uninstall from `exo-pet`
    // and from `exoma-ch`, which takes EACH org's devkit-upgrade
    // automation offline — that workflow mints its token from this App's
    // DEVKIT_UPGRADE_APP_CLIENT_ID / DEVKIT_UPGRADE_APP_PRIVATE_KEY —
    // then flip on `vig-os`, then re-onboard both. The engine App's twin
    // operation (#290) is the same shape against one org; this one costs
    // two.
    //
    // The grant behind that posture is far narrower than the engine
    // App's, which is what makes the same decision cheaper here:
    // `contents`, `issues`, `pull_requests`, `workflows` write plus
    // `metadata` read — no organization_administration, no secrets, no
    // members, no administration. An unauthenticated
    // `GET /apps/vigos-devkit-upgrade` publishes exactly that table plus
    // the numeric id, the owner, the creation date, the Client ID and
    // `events: []` — i.e. *this org runs a write-capable upgrade bot* —
    // and publishes NONE of: the private key, the installation set, or
    // which repositories the lists below name. Treat the Client ID as
    // public whatever it is stored as (#270).
    //
    // Two costs are accepted with it, the same two as #261:
    //   - An installation set we neither control nor hear about. Any
    //     account owner can install from the public page, and with
    //     `events: []` there is no `installation` event to receive, so
    //     `GET /app/installations` — a JWT signed with
    //     DEVKIT_UPGRADE_APP_PRIVATE_KEY, which no workflow holds — is
    //     the only inventory. SWEEP IT WHENEVER THAT KEY IS ROTATED and
    //     confirm every installation is one of ours; rotation is the one
    //     moment the check is free. A stray installation is inert while
    //     the key is sound — what it widens is the blast radius of a key
    //     compromise, from our orgs to ours plus whoever installed it.
    //   - A world-readable grant table (above). Reconnaissance, not a
    //     credential.
    //
    // The #256 coupling does NOT bind here, and that is half the value
    // of writing this down: `vigos-devkit-upgrade` is named as a ruleset
    // bypass actor or a status-check app NOWHERE in this file, so
    // `apply` never resolves its slug through `GET /apps/<slug>` and its
    // visibility is not configuration-relevant the way
    // `commit-action-bot`'s and `vig-os-release-app`'s are (see the App
    // bypass-actor comment on commit-action's rulesets below). #81 proposed
    // exactly such a bypass and was closed as superseded by
    // vig-os/devkit#1308. Making this
    // App private would therefore strand no ruleset — the two foreign
    // installations above are the only thing keeping it public.
    //
    // VERIFICATION IS UI-ONLY, and it is no longer owed. There is no
    // visibility field in `GET /apps/{slug}`, so the only API signal is
    // the status code to an ANONYMOUS call — 200 public, 404 private
    // (re-probed 200 on 2026-09-28; three sibling `vig-os` Apps answer
    // 404). That mapping stays an OBSERVATION and not a documented
    // contract: it has now been held up against the authority twice and
    // agreed twice — the engine App on 2026-09-28 (#290) and this App
    // the same day — which is corroboration on a second App, not the
    // contract GitHub declines to publish. It is also why no
    // `unmanaged-controls.toml` row can assert any of this: the controls
    // transport reads authenticated and never sees the discriminator,
    // and the button's disabled state has no API surface at all. The
    // authority remains the App's own settings page — Settings ->
    // Developer settings -> GitHub Apps -> vigos-devkit-upgrade ->
    // Advanced -> "Where can this GitHub App be installed?" — where the
    // Danger-zone button names the ACTION, not the state, so "Make
    // private" means it is currently public. EXPECT THAT BUTTON TO BE
    // DISABLED AND READ IT ANYWAY: greyed out is the state to expect
    // while another account has it installed, not a fault, and it still
    // reports the visibility. Click nothing: if the live value
    // contradicts this paragraph, that is drift in the App itself and
    // belongs in an issue, not in a hand-flip back.

    // Consumed since the devkit 1.7.0 adoptions landed vig-os/devkit#1365's
    // DEVKIT_UPGRADE_APP_ID -> _CLIENT_ID rename: devkit-smoke-test and
    // org-config reference it today. commit-action and sync-issues-action keep
    // their pre-seeded entries for their own 1.7 adoption; h5v and scitadel
    // are pre-seeded ahead of their re-scaffold (#112, #123). tessera consumes
    // it directly from its devkit 1.16.0 scaffold (#252, tessera#364): that
    // workflow takes the numeric DEVKIT_UPGRADE_APP_ID only as a legacy
    // fallback, so the client-ID entry alone is sufficient and no numeric one
    // is added.
    orgs.newOrgSecret('DEVKIT_UPGRADE_APP_CLIENT_ID') {
      selected_repositories+: [
        'commit-action',
        'devkit-smoke-test',
        'h5v',
        'org-config',
        'scitadel',
        'sync-issues-action',
        'tessera',
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
        'tessera',
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
        // Applies to every App bypass actor throughout this file. An App
        // actor (no `#role` / `@team` prefix) is WRITTEN by resolving its
        // slug through `GET /apps/<slug>`, which this engine's
        // installation token is observed to read only for a PUBLIC App
        // (#256, upstream #772). Both Apps named in this file are public,
        // and keeping them public is load-bearing, not incidental: make
        // one private and every ruleset below that names it becomes
        // unrepairable. A non-public App has to be written out of band —
        // a one-off `otterdog apply` with an org-owner PAT, which CAN
        // read the slug; otterdog then reads the actor back from
        // `/orgs/{org}/installations`, not `/apps/`, and plans clean, but
        // can no longer repair that ruleset. That read-back is the second
        // requirement: the App must also be an INSTALLATION ON THIS ORG,
        // because `/orgs/{org}/installations` is the ONLY id->slug source
        // otterdog has. An App with a live bypass slot that is not an org
        // installation is dropped from the model with a log line and no
        // plan output — a permanent phantom diff, with no numeric fallback
        // as there is for the `15368:` status-check prefixes below (#262,
        // upstream #732). See README, Known limitations.
        //
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
        orgs.devProtection(
          checks=['15368:CI Summary'],
          bypass=['commit-action-bot'],
        ),
        // House standard (ADR-0008). `Dist Check` is required on top of the
        // CI aggregator: it proves the committed `dist/` bundle matches the
        // source, which no CI Summary leg covers. Signatures come from the
        // `Signed commits` ruleset alone (this block used to require them a
        // second time), and the bypass is now the house org-owner PR bypass
        // instead of `#RepositoryAdmin` (#294).
        orgs.mainProtection(['15368:CI Summary', '15368:Dist Check']),
        orgs.releaseProtection(
          checks=['15368:CI Summary', '15368:Dist Check'],
          bypass=['commit-action-bot'],
        ),
        orgs.signedCommits(),
        orgs.tagProtection(['vig-os-release-app']),
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
        orgs.devProtection(
          checks=['15368:Test Summary'],
          bypass=['#OrganizationAdmin', 'commit-action-bot'],
        ),
        // House standard (ADR-0008) on devkit's own aggregator. Two CodeQL
        // contexts, not one: `codeql.yml`'s analyze job is a
        // `language: ['python', 'actions']` matrix, so each leg reports under
        // its own matrix-suffixed name (#115). Stale-review dismissal (#118)
        // and code-owner review off (#115) come with the shape.
        orgs.mainProtection([
          '15368:CodeQL Analysis (actions)',
          '15368:CodeQL Analysis (python)',
          '15368:Test Summary',
        ]),
        // Code-owner review is off in the shape itself, same rationale as
        // Main protection (#115).
        orgs.releaseProtection(
          checks=['15368:Test Summary'],
          bypass=['#OrganizationAdmin', 'commit-action-bot'],
        ),
        orgs.signedCommits(),
        // Tag protection mirrors commit-action's: devkit publishes the release
        // tags every consumer pins, and `release.yml` is the only tag writer —
        // it pushes (and `promote-release.yml` prunes RC tags) with a
        // vig-os-release-app token, so one always-bypass actor is enough.
        orgs.tagProtection(['vig-os-release-app']),
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
        // Code-owner review is off in the shape itself: `.github/CODEOWNERS`
        // is the devkit-seeded stub with every rule line commented out, so no
        // owner ever matches and the flag gates nothing. Populating it would
        // recreate the #115 unsatisfiable single-owner gate instead (#187).
        orgs.devProtection(
          checks=['15368:CI Summary'],
          bypass=['commit-action-bot'],
        ),
        // House shape (ADR-0008), with three documented exceptions that keep
        // devkit's release train unattended here. The admin bypass is the
        // house `pull_request` mode, still the sanctioned override that
        // replaced out-of-band ruleset PUTs (#147).
        orgs.mainProtection(['15368:CI Summary']) {
          required_pull_request+: {
            // EXCEPTION — no human review: the repo is bot-authored
            // release-validation scaffolding, and the dispatch listener's
            // approval gate that needed `reviewDecision` to be computable
            // (vig-os/devkit#1391) is removed by vig-os/devkit#1506. The
            // operative controls are the required CI Summary check and
            // devkit's published-smoke-release validation at promote;
            // count-0-with-required-checks matches devkit's own Dev and
            // Release protections (#167).
            required_approving_review_count: 0,
            // EXCEPTION — no thread-resolution gate: nobody is in the loop to
            // resolve a thread, so any comment would stall the train.
            requires_review_thread_resolution: false,
          },
          required_status_checks+: {
            // EXCEPTION — not strict: a release PR that falls behind `main`
            // makes `promote-release` fail on `BEHIND`, and no human is
            // present to update the branch mid-train.
            strict: false,
          },
        },
        // The train writes `release/X.Y.Z` as the Commit App only
        // (`prepare-release.yml` / `prepare-hotfix.yml` create it and commit
        // the freeze, `release-core.yml` the finalize, `sync-issues.yml` the
        // archive sync); `abandon-release.yml` and the dispatch listener's
        // stale-branch cleanup delete it as the Release App, which the
        // shape's `allows_deletions` permits.
        orgs.releaseProtection(
          checks=['15368:CI Summary'],
          bypass=['commit-action-bot'],
        ),
        orgs.signedCommits(),
        // The only tag writer is the release train: `release-publish.yml`
        // creates the release and RC tags, and `promote-release.yml` prunes
        // RC tags and moves floating tags, all as the Release App.
        orgs.tagProtection(['vig-os-release-app']),
      ],
      // Live-proof harness for devkit's opt-in `DEVKIT_COMMIT_APP_ENVIRONMENT`
      // knob (vig-os/devkit#1710, shipped in vig-os/devkit#1724): it binds the
      // commit-App token-minting jobs to an environment, so the deployment
      // branch policy (`main` + `release/*`, plus `dev` under gitflow) becomes
      // the control that refuses an out-of-policy branch. Holds no secrets yet
      // — the knob is not in a devkit release as of 1.16.0. No reviewers,
      // deliberately: a reviewer gate here would add a second approval to
      // devkit's single-approval release train. Declared so the plan stops
      // proposing its deletion (#279).
      environments: [
        orgs.newEnvironment('commit-app') {
          branch_policies+: [
            'dev',
            'main',
            'release/*',
          ],
          deployment_branch_policy: 'selected',
        },
      ],
    },
    orgs.newRepo('h5v') {
      description: 'A terminal viewer for HDF5 files with chart, image, string, matrix, and attributes support',
      // Tier A (ADR-0008): a devkit 1.17.0 trunk scaffold (`.vig-os`
      // DEVKIT_WORKFLOW=trunk) — no `dev` branch; releases fork
      // `release/X.Y.Z` from `main` and merge back through the release PR.
      // `CI Summary` is `ci.yml`'s aggregator job, reported by github-actions
      // on every PR into `main` and `release/**` (#294).
      rulesets: [
        // House standard, no bot bypass. Until vig-os/h5v#9 lands, h5v's
        // nightly `sync-issues.yml` still commits straight to `main` as the
        // Commit App (`DEVKIT_SYNC_TARGET` unset) and this ruleset refuses
        // that push (vig-os/devkit#1227); #9 retargets it to
        // `sync/issue-mirror`, the org-config pattern (#294).
        orgs.mainProtection(['15368:CI Summary']),
        // The trunk release train writes `release/X.Y.Z` as the Commit App
        // only: `prepare-release.yml` creates the branch and commits the
        // freeze, `release-core.yml` commits the finalize and dispatches the
        // archive sync onto it, and `release.yml`'s rollback reverts it.
        // `abandon-release.yml` deletes it with the Release App, which the
        // shape's `allows_deletions` already permits.
        orgs.releaseProtection(
          checks=['15368:CI Summary'],
          bypass=['commit-action-bot'],
        ),
        // Every automated branch writer commits through the API, so GitHub
        // signs it: the Commit App (commit-action), the devkit-upgrade App
        // (`devkit-upgrade.yml` builds its commit with `git/commits`) and
        // Renovate (platform commits).
        orgs.signedCommits(),
        // The only tag writer is the release train: `release-publish.yml`
        // creates the release tag, and `promote-release.yml` prunes RC tags,
        // both as the Release App. h5v has no tags yet.
        orgs.tagProtection(['vig-os-release-app']),
      ],
    },
    orgs.newRepo('nvd-mirror') {
      description: 'Public mirror of the NVD JSON 2.0 feeds for vulnix (see vig-os/devcontainer#870)',
      gh_pages_build_type: 'legacy',
      gh_pages_source_branch: 'gh-pages',
      gh_pages_source_path: '/',
      // Tier B (ADR-0008): no PR workflow, so no check to require (#294).
      rulesets: [
        orgs.mainProtection([]),
        // EXCEPTION (ADR-0008) — `gh-pages` is outside the signing rule. It
        // is `refresh.yml`'s output, not source: every six hours the job
        // force-pushes a fresh, UNSIGNED orphan commit there with the
        // workflow's GITHUB_TOKEN, and github-actions cannot be a ruleset
        // bypass actor. `main` only ever takes signed, human commits.
        orgs.signedCommits() {
          exclude_refs+: [
            'refs/heads/gh-pages',
          ],
        },
      ],
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
      custom_properties+: {
        type: ['tools'],
      },
      description: 'GitHub Organization Management',
      has_projects: false,
      has_wiki: false,
      // Template repo: downstream orgs' private org-config repos are created
      // from this one (ADR-0006; marked live via one-time gh API action, #52).
      is_template: true,
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
        // House standard (ADR-0008).
        orgs.mainProtection(['15368:CI Summary']),
        orgs.signedCommits(),
        // The only tag writer is the release train: `release-publish.yml`
        // creates the release tag and `promote-release.yml` prunes RC tags
        // and moves floating tags, all as the Release App.
        orgs.tagProtection(['vig-os-release-app']),
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
      // OUT OF SCOPE of ADR-0008 and deliberately frozen at its live state
      // until it gets its own decision (#294): private on a Free-plan org, so
      // no ruleset can be enforced, and its default branch is a leaked agent
      // worktree branch. The five merge fields below restate the retired
      // `legacyMergePolicy` (all three methods, upstream title/message) so
      // removing that mixin changes nothing live here.
      allow_forking: false,
      allow_merge_commit: true,
      allow_rebase_merge: true,
      allow_squash_merge: true,
      allow_update_branch: false,
      custom_properties+: {
        type: ['tools'],
      },
      default_branch: 'worktree-agent-ab0adbce',
      delete_branch_on_merge: false,
      description: 'Quality Management System',
      has_wiki: false,
      merge_commit_message: 'PR_TITLE',
      merge_commit_title: 'MERGE_MESSAGE',
      private: true,
    },
    orgs.newRepo('qx') {
      description: 'Per-instance physical part identification: nano-id IDs, QR labels, mint-then-bind workflow',
      gh_pages_build_type: 'workflow',
      homepage: 'https://vig-os.github.io/qx/',
      // Tier A (ADR-0008), trunk-based with no `dev` or `release/*` branch.
      // `CI Summary` is the aggregator vig-os/qx#311 adds to `ci.yml` over
      // its `flake-check` matrix (vig-os/qx#310); it reports on every PR.
      // qx has no bot writers at all: every commit, merge and tag is a
      // maintainer's, and `release.yml` / `pages.yml` write only GitHub
      // Releases and Pages with the Actions token (#294).
      rulesets: [
        orgs.mainProtection(['15368:CI Summary']),
        // Every commit on `main`, fork PRs included, is signed.
        orgs.signedCommits(),
        // EXCEPTION (ADR-0008) — the bypass is the org owners, not a release
        // App: qx releases by a maintainer (an org owner) pushing a `v*` tag
        // by hand, which triggers `release.yml`. There is no release App to
        // name. `#OrganizationAdmin` in always mode, since a tag push is not
        // a pull request.
        orgs.tagProtection(['#OrganizationAdmin']),
      ],
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
      description: 'Scitadel: programmable, reproducible scientific literature retrieval',
      secrets: [
        orgs.newRepoSecret('CARGO_REGISTRY_TOKEN') {
          value: '********',
        },
      ],
      // Tier A (ADR-0008): a devkit gitflow scaffold (`.vig-os`
      // DEVKIT_WORKFLOW unset) that releases through the devkit train —
      // `dev` integrates, `release/X.Y.Z` is forked from it, and the
      // App-authored release PR merges into `main` with `gh pr merge
      // --merge`, which the squash-only policy this repo used to declare
      // refused. The same shapes as commit-action's (#294).
      //
      // `CI Summary` is `ci.yml`'s aggregator, reported by github-actions on
      // PRs into `dev`, `release/**` and `main` (seen on #226 into `dev` and
      // on the 0.8.0 release PR #222 into `main`). It replaces the
      // unpinned `Lint` / `Test (...)` contexts, which any app or commit
      // status could satisfy. Those jobs belong to `rust-ci.yml`, a second
      // workflow the aggregator does not cover: its `clippy -D warnings` and
      // the macOS test leg keep running but no longer gate a merge.
      rulesets: [
        // Every direct push to `dev` is the Commit App's: `sync-issues.yml`
        // commits the nightly issue mirror there, and `prepare-release.yml`
        // commits through commit-action. Merges of the sync-main-to-dev PR
        // and devkit-upgrade PRs go through a PR.
        orgs.devProtection(
          checks=['15368:CI Summary'],
          bypass=['commit-action-bot'],
        ),
        // House standard, no bot bypass: nothing pushes to `main` directly;
        // the release PR is merged by the Release App after the human
        // approval.
        orgs.mainProtection(['15368:CI Summary']),
        // The train writes `release/X.Y.Z` as the Commit App only
        // (`prepare-release.yml` / `prepare-hotfix.yml` create it and commit
        // the freeze, `release-core.yml` the finalize); `abandon-release.yml`
        // deletes it as the Release App, which the shape's `allows_deletions`
        // permits.
        orgs.releaseProtection(
          checks=['15368:CI Summary'],
          bypass=['commit-action-bot'],
        ),
        // Every writer signs: humans' commits on `main` and `dev` verify, and
        // every bot commit is an API commit GitHub signs (the Commit App via
        // commit-action, the devkit-upgrade App, Renovate's changelog
        // commits, Dependabot).
        orgs.signedCommits(),
        // The only tag writer is the release train: `release-publish.yml`
        // creates the release tag and `promote-release.yml` prunes RC tags,
        // both as the Release App. `binaries.yml` only uploads assets to the
        // existing tag's release.
        orgs.tagProtection(['vig-os-release-app']),
      ],
      environments: [
        orgs.newEnvironment('crates-io'),
      ],
    },
    orgs.newRepo('sync-issues-action') {
      allow_auto_merge: true,
      // On so the "Update branch" button (and auto-merge's auto-update) can
      // satisfy Main protection's `strict` requirement without a manual
      // rebase (#188).
      allow_update_branch: true,
      custom_properties+: {
        type: ['tools'],
      },
      description: 'GitHub Action that syncs issues and pull requests to markdown files with full comments, review threads, and diff snippets. Useful for documentation, backups, and offline access. Supports incremental syncing with state caching and GitHub App authentication.',
      private_vulnerability_reporting_enabled: true,
      rulesets: [
        // Code-owner review is off in the shape itself: `.github/CODEOWNERS`
        // is the devkit-seeded stub with every rule line commented out, so no
        // owner ever matches and the flag gates nothing. Populating it would
        // recreate the #115 unsatisfiable single-owner gate instead (#187).
        orgs.devProtection(
          checks=['15368:CI Summary'],
          bypass=['commit-action-bot'],
        ),
        // House standard (ADR-0008): stale-review dismissal (#118, #184),
        // strict up-to-date checks (#188, paired with `allow_update_branch`
        // above) and code-owner review off — the seeded CODEOWNERS stub has
        // no active rule, and populating it would recreate the #115
        // unsatisfiable single-owner gate (#187). `Dist Check` as on
        // commit-action. The org-owner PR bypass is new here (#294).
        orgs.mainProtection(['15368:CI Summary', '15368:Dist Check']),
        orgs.releaseProtection(
          checks=['15368:CI Summary', '15368:Dist Check'],
          bypass=['commit-action-bot'],
        ),
        orgs.signedCommits(),
        orgs.tagProtection(['vig-os-release-app']),
      ],
      environments: [
        orgs.newEnvironment('copilot'),
      ],
    },
    orgs.newRepo('tessera') {
      allow_auto_merge: true,
      // EXCEPTION (ADR-0008) — the only vig-os repo not defaulting to `main`
      // (tessera#383). The first alpha (0.1.0-alpha.1) was cut on
      // 2026-09-23, but `dev` is still the integration branch: every PR,
      // Dependabot's `target-branch` and release-plz (run on every push to
      // `dev` since tessera#436) target it, and `main` only moves at a
      // promotion. Flipping now would run the scheduled workflows from
      // `main`'s stale copies — it lacks the devkit scaffold and
      // `devkit-upgrade.yml`, and its `sync-issues.yml` still uses the
      // repo-scoped sync App. Revisit once `main` carries the scaffold, or
      // with tessera#441's release-train decision (#294).
      default_branch: 'dev',
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
        // Credentials of the repo-scoped `tessera-release-plz` GitHub App
        // (app_id 5050387) that drives tessera's release-plz release-PR flow
        // (tessera ADR-0052); value managed out-of-band, declared so the plan
        // stops proposing their deletion (#254, #255). Retire together with
        // release-plz when tessera migrates to the devkit release train
        // (tessera#441).
        orgs.newRepoSecret('RP_APP_ID') {
          value: '********',
        },
        orgs.newRepoSecret('RP_APP_PRIVATE_KEY') {
          value: '********',
        },
      ],
      // Tier A (ADR-0008) on a `dev` + `main` model without `release/*`
      // branches: release-plz opens the release PR into `dev`, and `main`
      // takes a promotion from `dev`. These rulesets replace the classic
      // branch protection on both branches (#294).
      //
      // The required context stays `nix flake check`, now in ruleset syntax
      // (`15368:`), not `CI Summary`: it is the only aggregator both a
      // `main`-origin PR and a `dev` promotion PR report (#234), since
      // `main` still runs the pre-scaffold `CI` shim. It also reports on
      // every PR into `dev`, where `CI Summary` would additionally gate
      // commit messages that Dependabot's PRs currently fail.
      rulesets: [
        // Not strict, as before: `dev` moves constantly, so re-running both
        // arch legs on every push would cost more there than up-to-date-ness
        // is worth (#234). New: a PR is now required. The only direct pusher
        // is the Commit App, which `sync-issues.yml` commits the nightly
        // issue mirror to `dev` with; release-plz, devkit-upgrade and
        // Dependabot all go through PRs.
        orgs.devProtection(
          checks=['15368:nix flake check'],
          bypass=['commit-action-bot'],
        ),
        // House standard. The alpha promotion was pushed to `main` directly
        // (tessera `5281db2`, `ee277ad`, both unsigned); from here on a
        // promotion is a `dev` -> `main` PR.
        orgs.mainProtection(['15368:nix flake check']),
        // EXCEPTION (ADR-0008) — no `Signed commits`: tessera's main
        // contributor pushes unsigned commits (every commit on the open
        // PRs, and the two promotion commits on `main`). Under merge-commit
        // only, a signing rule would make each of those PRs unmergeable.
        // Add `orgs.signedCommits()` once they sign.
        //
        // EXCEPTION (ADR-0008) — the bypass is the org owners, not a release
        // App: `v0.1.0-alpha.1` was tagged by hand by a maintainer (an org
        // owner), and release-plz is wired for `release-pr` only, so no App
        // creates tags. When `release-plz release` takes over tagging, its
        // App replaces this bypass (and must be public, see the note at the
        // top of this list).
        orgs.tagProtection(['#OrganizationAdmin']),
      ],
    },
    orgs.newRepo('vigos-mvp') {
      description: 'MVP with basic functions',
      private_vulnerability_reporting_enabled: true,
      // Tier B (ADR-0008): no workflows at all, so no check to require and
      // no automated writer. Every commit on every branch is already signed
      // by its human author, so `Signed commits` refuses nothing in use
      // (#294).
      rulesets: [
        orgs.mainProtection([]),
        orgs.signedCommits(),
      ],
    },
    orgs.newRepo('vs-dolt') {
      description: 'VS Code extension, open source SQL workbench for your MySQL and PostgreSQL compatible database with version control features when connected to Dolt.',
      has_issues: false,
      homepage: 'https://hub.docker.com/r/dolthub/dolt-workbench',
      private_vulnerability_reporting_enabled: true,
      // Tier B (ADR-0008): a fork of dolthub/dolt-workbench with no commits
      // of its own. Its upstream workflows are not enabled on the fork, and
      // CodeQL default setup writes nothing, so no automated writer exists.
      // Updating from upstream now goes through a PR (upstream `main` into
      // this `main`); the one-click "Sync fork" is a direct push, which
      // `Main protection` refuses (#294).
      //
      // No `Signed commits` (ADR-0008 tier B signs only where every writer
      // already does): upstream lands unsigned commits, so a signing rule
      // would make every upstream sync unmergeable.
      rulesets: [
        orgs.mainProtection([]),
      ],
    },
  ],
}
