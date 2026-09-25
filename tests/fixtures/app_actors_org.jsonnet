// Self-contained fixture org for the App-slug check (issue #259).
//
// Deliberately NOT built on the vendored Eclipse base template: it is the
// EVALUATED org document the extractor consumes, so it only has to carry the
// four write-path sites otterdog 1.5.0 resolves through `GET /apps/{slug}` —
// and, just as importantly, every neighbouring form that is NOT an App lookup,
// so a widening of the predicate fails a test instead of paging a reviewer.
//
// `app_actors_org.json` beside it is this file evaluated; `test_app_actors`
// re-evaluates it with the `jsonnet` binary when one is available and asserts
// the two agree, so the committed JSON can never drift from this source.
{
  github_id: 'fixture-org',
  project_name: 'fixture',
  // Org-level rulesets: the same two sites as a repo ruleset, with no repo.
  rulesets: [
    {
      name: 'Org protection',
      bypass_actors: [
        'org-bypass-app',
        '#OrganizationAdmin',
      ],
      required_status_checks: {
        status_checks: [
          'org-check-app:Build',
        ],
      },
    },
  ],
  repositories: [
    {
      name: 'alpha',
      rulesets: [
        {
          name: 'Main protection',
          bypass_actors: [
            // `:bypass_mode` suffix is stripped before the lookup.
            'gated-app:pull_request',
            // Roles and teams are resolved elsewhere, never on `/apps/`.
            '#RepositoryAdmin:pull_request',
            '@fixture-org/reviewers',
            // No `isdigit()` escape on THIS site: a numeric bypass actor is
            // still a slug lookup, and 404s (models/ruleset.py:646-649).
            '15368',
          ],
          required_status_checks: {
            status_checks: [
              // Escapes, all three (models/ruleset.py:181-185).
              '15368:CI Summary',
              'any:Lint',
              'spaced prefix:Check',
              // No colon at all -> a plain context, no app.
              'plain check',
              // The one real App lookup on this site.
              'checks-app:Coverage',
            ],
          },
        },
        {
          name: 'Signed commits',
          bypass_actors: [],
          required_status_checks: null,
        },
      ],
      environments: [
        {
          name: 'production',
          // Only the un-prefixed form is an App; `@user` and `@org/team` are not.
          reviewers: [
            '@c-vigo',
            '@fixture-org/reviewers',
            'reviewer-app',
          ],
        },
      ],
      branch_protection_rules: [
        {
          pattern: 'main',
          required_status_checks: [
            // No colon -> IMPLICIT `github-actions` slug, unlike a ruleset
            // (models/branch_protection_rule.py:345-346).
            'CI Summary',
            'any:Lint',
            'bpr-app:Build',
            // A numeric prefix is NOT escaped here — it is looked up as a slug
            // and 404s while plan stays green.
            '15368:Nope',
          ],
        },
      ],
    },
    {
      name: 'beta',
      rulesets: [],
      environments: [],
      branch_protection_rules: [],
    },
  ],
}
