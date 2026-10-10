---
type: issue
state: open
created: 2026-10-09T12:11:53Z
updated: 2026-10-09T12:11:53Z
author: gerchowl
author_url: https://github.com/gerchowl
url: https://github.com/vig-os/org-config/issues/327
comments: 0
labels: none
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-10-10T08:12:36.488Z
---

# [Issue 327]: [chore(config): declare vigil — tier A gitflow repo (like revkit), config-first](https://github.com/vig-os/org-config/issues/327)

Declare the new public `vig-os/vigil` **config-first** (created by `otterdog apply`, not `gh repo create`; cf. stepv's after-the-fact declaration in #317).

## What vigil is
**vigil**, *Verifiable Integrity-Guarded Instrumentation & Logging*: the opinionated observability crate for every vig-os / gerchowl Rust project (crates.io package `vigil-telemetry`, lib name `vigil`).
- **Core:** `tracing` → OpenTelemetry → OTLP/JSON Lines files (logs, metrics, traces) conformant with the OTel file-exporter spec, with multi-process-safe rotation.
- **`audit` feature:** a lossless, hash-chained audit trail with signed checkpoints for user actions on device (21 CFR Part 11 §11.10(e)-style), built on `tessera-core` primitives.

devkit will wire it into the Rust scaffold; it is not code *in* devkit.

## Declaration (same shapes as revkit, #311)
- devkit **gitflow** scaffold (`DEVKIT_WORKFLOW` unset, devkit 1.18.0), Tier A under ADR-0008: `devProtection` / `mainProtection` / `releaseProtection` gated on `15368:CI Summary`, `commit-action-bot` bypass on dev/release, `signedCommits()`, `tagProtection(['vig-os-release-app'])`; house merge policy via `newRepo`; `allow_update_branch` (#188); `type: ['tools']`.
- Joins the **six client-ID-form** App org secrets only (`COMMIT_APP_CLIENT_ID`/`_PRIVATE_KEY`, `RELEASE_APP_CLIENT_ID`/`_PRIVATE_KEY`, `DEVKIT_UPGRADE_APP_CLIENT_ID`/`_PRIVATE_KEY`), not the numeric `*_APP_ID` lists (#112, #313).
- Companion edits (#319): `tests/conftest.py` `DECLARED_REPOS` + `DECLARED_ORG_SECRETS`, `tests/test_app_actors.py` site count (+3, gitflow), CHANGELOG.

## Not yet declared, on purpose
The `crates-io` environment and `CARGO_REGISTRY_TOKEN` land with the first release (as stepv).

## After apply (#318)
The secret grants are dummy-valued, so `apply` won't grant them live: run the six `gh api -X PUT …/secrets/{name}/repositories/{id}` calls that `plan`'s "Declared org-secret readers" section prints.
