# Otterdog config layout

This directory holds this org's declarative Otterdog configuration. The reusable
`plan`/`apply`/`drift` workflows (upstream in `vig-os/org-config`) read it from
the paths below, resolved from `org_github_id` in each caller workflow.

## Expected layout

The skeleton ships `YOUR_ORG/` — rename it to this org's GitHub login (the
`github_id` / `org_github_id`). It ends up holding a single `<org>.jsonnet` entry
point, the house defaults overlay, and the vendored base template:

```text
otterdog/
  <org>/                      # e.g. otterdog/exo-pet/
    <org>.jsonnet             # e.g. otterdog/exo-pet/exo-pet.jsonnet — org entry point
    house-defaults.libsonnet  # house defaults overlay (shipped; copy verbatim)
    vendor/                   # vendored base-template libsonnet (offline validate)
      otterdog-defaults/
        otterdog-defaults.libsonnet
```

- `<org>.jsonnet` is what `otterdog plan`/`apply` and the drift reconciler
  (`--config-jsonnet otterdog/<org>/<org>.jsonnet`) evaluate. Start it from the
  **house defaults overlay**, not the vendored defaults, e.g.:

  ```jsonnet
  local orgs = import 'house-defaults.libsonnet';

  orgs.newOrg('<org>', '<org>') {
    settings+: {
      // org settings the App can manage (see the github-app runbook for the
      // web-UI-only exclusions no App token can reach)
    },
  }
  ```

- `house-defaults.libsonnet` re-exports the vendored Eclipse base template with
  the **house repository merge policy** (merge commits only, `PR_TITLE` /
  `PR_BODY`) folded into `newRepo`, so every repo declared in `<org>.jsonnet`
  inherits it without restating five fields per repo. It is org-neutral: copy it
  verbatim, never edit it. It also exports `upstreamMergePolicy` and
  `legacyMergePolicy` mixins for repos that deliberately stay on another policy —
  see the file header, and `vig-os/org-config`'s own
  `otterdog/vig-os/vig-os.jsonnet` for worked usage. The overlay resolves
  `vendor/…` relative to itself, so it only ever needs to sit beside the
  `vendor/` tree shown above.

- `vendor/` pins the base template locally so `otterdog validate --local` and the
  reusable workflows' `--local` runs never re-fetch the upstream defaults. Keep it
  in lockstep with `base_template` in `otterdog.json`.

## Import an existing org

Bootstrap the initial `<org>.jsonnet` from the live org with
`otterdog import <org>`, then:

1. Change the generated import line from
   `import 'vendor/otterdog-defaults/otterdog-defaults.libsonnet'` to
   `import 'house-defaults.libsonnet'`.
2. Normalize away any base-template-seeded defaults so the first `plan` shows an
   empty diff. Repos already on the house merge policy no longer need their
   `allow_merge_commit` / `allow_rebase_merge` / `allow_squash_merge` /
   `merge_commit_title` / `merge_commit_message` lines; repos that are **not** on
   it need an explicit `+ orgs.legacyMergePolicy` (or `+ orgs.upstreamMergePolicy`)
   so the plan stays empty.

See the upstream `vig-os/org-config` `otterdog/vig-os/` tree for a worked example.
