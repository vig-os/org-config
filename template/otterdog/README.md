# Otterdog config layout

This directory holds this org's declarative Otterdog configuration. The reusable
`plan`/`apply`/`drift` workflows (upstream in `vig-os/org-config`) read it from
the paths below, resolved from `org_github_id` in each caller workflow.

## Expected layout

Create one directory named for this org's GitHub login (the `github_id` /
`org_github_id`), containing a single `<org>.jsonnet` entry point:

```text
otterdog/
  <org>/                      # e.g. otterdog/exo-pet/
    <org>.jsonnet             # e.g. otterdog/exo-pet/exo-pet.jsonnet — org entry point
    vendor/                   # vendored base-template libsonnet (offline validate)
      otterdog-defaults/
        otterdog-defaults.libsonnet
```

- `<org>.jsonnet` is what `otterdog plan`/`apply` and the drift reconciler
  (`--config-jsonnet otterdog/<org>/<org>.jsonnet`) evaluate. Start it from the
  vendored defaults, e.g.:

  ```jsonnet
  local orgs = import 'vendor/otterdog-defaults/otterdog-defaults.libsonnet';

  orgs.newOrg('<org>', '<org>') {
    settings+: {
      // org settings the App can manage (see the github-app runbook for the
      // web-UI-only exclusions no App token can reach)
    },
  }
  ```

- `vendor/` pins the base template locally so `otterdog validate --local` and the
  reusable workflows' `--local` runs never re-fetch the upstream defaults. Keep it
  in lockstep with `base_template` in `otterdog.json`.

## Import an existing org

Bootstrap the initial `<org>.jsonnet` from the live org with
`otterdog import <org>`, then normalize away any base-template-seeded defaults so
the first `plan` shows an empty diff. See the upstream `vig-os/org-config`
`otterdog/vig-os/` tree for a worked example.
