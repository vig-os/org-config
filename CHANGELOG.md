# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- **Otterdog toolchain integration (L0)** ([#15](https://github.com/vig-os/org-config/issues/15))
  - Dev-shell (`flake.nix` `extraPackages`) gains `sops`, `age`, `go-jsonnet` (jsonnetfmt), `actionlint`, and `zizmor` (ADR-0005); otterdog itself runs via pinned `uvx` so CI and downstream template repos stay flake-independent.
  - Flake-generated pre-commit hooks add `jsonnetfmt --test` (otterdog jsonnet, no-op until #17) and `actionlint` (workflows).
  - `justfile.project` `validate` recipe (new "L0 validation" group) runs `actionlint` + `zizmor` over `.github/workflows` and, guarded on config presence, `jsonnetfmt --test` and `otterdog validate --local`; the otterdog version pin is a single `otterdog_version` variable (ADR-0007).
  - `zizmor.yml` baselines the devkit-managed workflows (per-audit, per-file) so `just validate` gates only org-config-authored workflows.
- **Architecture decision records 0001–0007** ([#1](https://github.com/vig-os/org-config/issues/1), [#8](https://github.com/vig-os/org-config/issues/8)–[#14](https://github.com/vig-os/org-config/issues/14))
  - `docs/adr/` with the house ADR convention (exo-fleet numbering, EXOPET vault template format) and index: 0001 reconciliation engine (Otterdog), 0002 drift semantics, 0003 secrets backend (SOPS/age), 0004 auth model (GitHub App), 0005 repo tooling, 0006 distribution topology & versioning, 0007 CI & testing strategy.
- **GitHub App runbook** ([#5](https://github.com/vig-os/org-config/issues/5)): `docs/runbooks/github-app.md` — creation, permissions table, bootstrap-secret handling, key rotation, downstream-org installation.
- **Adopt vigOS devkit 1.3.1** ([#2](https://github.com/vig-os/org-config/issues/2))
  - Greenfield scaffold of the shared vigOS dev environment in `direnv` mode: `flake.nix` + `.envrc` dev-shell, layered `justfile`s, managed pre-commit and `.github/` CI, and the `.vig-os` project manifest.
  - Pins move in lockstep: `.vig-os` `DEVKIT_VERSION=1.3.1`, `flake.nix` `vigos.url = "github:vig-os/devkit?ref=1.3.1"`, `flake.lock` locked to the 1.3.1 revision.
  - No language template and no release tag scheme yet (`DEVKIT_TAG_PREFIX`/`DEVKIT_FLOATING_TAGS` unset); the managed `codeql.yml` degrades to the language-less case (`actions` leg only, workflows-only push paths, vig-os/devkit#1142). Release workflows ship dormant.
  - Pre-commit hooks are flake-generated (`hooks = { }` in `flake.nix`, vig-os/devkit#883), matching the sibling direnv consumers: `.pre-commit-config.yaml` is a generated `/nix/store` symlink (gitignored) and the upstream `pymarkdown` hook is dropped (its `pyjson5` native dep cannot load on the host-runner direnv CI).

### Changed

- **Harden org-config self-protection** ([#4](https://github.com/vig-os/org-config/issues/4))
  - Release tags now carry the `v` prefix (`DEVKIT_TAG_PREFIX=v`, actions-ecosystem convention; dormant until the first release).
  - `.github/CODEOWNERS` now gates admin-critical paths (`/.github/`, `/otterdog/`, `/secrets/`, `flake.nix`, `flake.lock`, `.vig-os`); `docs/` is intentionally left unowned so ADR/doc PRs to `dev` stay unblocked.

### Deprecated

### Removed

### Fixed

### Security
