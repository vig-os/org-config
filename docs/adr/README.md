# Architecture Decision Records

Every non-trivial decision in `org-config` gets an **Architecture Decision Record (ADR)**, authored **before** the
implementation it governs (see the M1 milestone in issue #1). The format is a **house blend**: filenames use exo-fleet
`NNNN-slug` numbering, and each record's content follows the EXOPET `vault/decisions` `_template.md` layout — YAML
frontmatter with a `status` enum, a status-line block, a **mandatory alternatives table**, Decision / Rationale /
Consequences, a Corrections log, supersession triggers, and References. Each ADR carries its own `status`, so this
index has no status column. Cross-repo decisions are referenced as `<repo>#ADR-NNNN`, never copied.

## Index

| ADR | Decision |
|---|---|
| [0001](0001-reconciliation-engine-otterdog.md) | Reconciliation engine — Otterdog |
| [0002](0002-drift-semantics.md) | Drift semantics |
| [0003](0003-secrets-backend-sops-age.md) | Secrets backend — SOPS/age |
| [0004](0004-auth-model-github-app.md) | Auth model — GitHub App |
| [0005](0005-repo-tooling.md) | Repo tooling |
| [0006](0006-distribution-topology-and-versioning.md) | Distribution topology & versioning |
| [0007](0007-ci-and-testing-strategy.md) | CI & testing strategy |
