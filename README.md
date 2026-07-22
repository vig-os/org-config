# org-config

GitHub organization configuration as code for the [`vig-os`](https://github.com/vig-os)
organization. This repository is the declarative source of truth for org-level
settings, repository configuration, access, and branch rulesets — managed via a
GitOps workflow (plan on pull request, apply on merge, with drift detection).

The design and roadmap are tracked in issue
[#1](https://github.com/vig-os/org-config/issues/1).

The GitOps tooling is **live**: `otterdog plan` runs read-only on every pull
request and posts the diff, `otterdog apply` runs on merge to `main` inside a
reviewer-gated `production` environment, and a scheduled drift job reconciles the
committed config against live org state.

## Requesting a change

To change any managed org or repository setting (org settings, repo settings,
rulesets/branch protection, teams & permissions, secrets/variables, webhooks),
**do not edit the jsonnet directly** — open a request and let the pipeline apply
it:

1. Open a [**change-request** issue](https://github.com/vig-os/org-config/issues/new?template=change-request.yml)
   describing the target repo(s), the setting area, and the desired end state.
2. A maintainer turns an accepted request into an Otterdog config pull request.
3. The **plan** workflow posts the exact diff as a PR comment — nothing is applied
   yet.
4. On merge to `main`, **apply** runs in the reviewer-gated `production`
   environment, so every mutation pauses for human approval.
5. Scheduled **drift** detection reconciles the committed config against the live
   org and opens an issue for any out-of-band change.
