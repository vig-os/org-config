---
type: issue
state: open
created: 2026-10-12T00:18:59Z
updated: 2026-10-12T00:18:59Z
author: gerchowl
author_url: https://github.com/gerchowl
url: https://github.com/vig-os/org-config/issues/336
comments: 0
labels: none
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-10-12T08:46:30.676Z
---

# [Issue 336]: [stepv: declare the crates-io environment and the release secrets (stepv#10)](https://github.com/vig-os/org-config/issues/336)

stepv's release train (vig-os/stepv#10) needs 7 repo secrets and a `crates-io` environment, in scitadel's shape:

- `MACOS_SIGNING_P12`, `MACOS_SIGNING_P12_PASSWORD`, `MACOS_SIGNING_IDENTITY`;
- `APPLE_NOTARY_KEY_P8`, `APPLE_NOTARY_KEY_ID`, `APPLE_NOTARY_ISSUER`;
- `CARGO_REGISTRY_TOKEN`.

The stepv block says not to declare a `'********'` placeholder before the live secret exists. So **this merges only after** the maintainer has set all 7 with `gh secret set -R vig-os/stepv`. The PR is a draft until then.

The `CARGO_REGISTRY_TOKEN` declaration is removed again after the first publish, once crates.io Trusted Publishing takes over.
