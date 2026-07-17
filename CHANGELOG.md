# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- **Plan-on-PR workflow (L2)** ([#18](https://github.com/vig-os/org-config/issues/18))
  - `.github/workflows/plan.yml` runs a read-only `otterdog plan --local --no-web-ui` of the committed config against live `vig-os` on same-repo PRs touching `otterdog.json`/`otterdog/**`/the workflow, plus `workflow_dispatch`; forks are excluded per the ADR-0007 same-repo credential guard.
  - `--local` skips otterdog's `_init_base_template` vendor re-fetch, so plan evaluates the exact committed `otterdog/vig-os/vendor/` tree that L0 `otterdog validate --local` checks (no upstream EclipseFdn hooks re-introduced).
  - Uses the full App installation token (ADR-0004 Corrections) with two scoped, justified `github-app` inline zizmor ignores; least-privilege `permissions:` (`contents: read`, `pull-requests: write`); per-PR concurrency with cancel-in-progress.
  - Posts the plan as a marker-keyed PR comment updated in place (truncated safely, with run link) and to the job summary; the job fails only on validation/auth/harness errors — drift (exit 0) is report content, not failure. A fixed footnote flags the expected benign `vs-dolt` `code_scanning_default_languages` drift.
- **Import `vig-os` Otterdog configuration** ([#17](https://github.com/vig-os/org-config/issues/17))
  - `otterdog.json` (repo root) declares the `vig-os` org, `org-config` config repo, the `env` credential provider (`OTTERDOG_TOKEN` + dummy web-UI credential keys, unused on the App-token path), the pinned `EclipseFdn/otterdog-defaults@v0.13.1` base template, and `config_dir: otterdog` so all config lives under `otterdog/` (ADR-0006 dogfooding).
  - `otterdog/vig-os/vig-os.jsonnet`: normalized org config imported from live `vig-os`, declaring all 16 repos including the private `qms` (ADR-0006), plus org settings, secrets, rulesets, environments, and the `type` custom property. Drift-free against live so #18's first `plan` shows an empty diff; the 12 web-UI-only org settings stay unmanaged (spike #16).
  - Fixes the imported-config evaluation bug (#16): the `type` custom property used an inherited-`null` `default_value+:` merge (`null + array`); expressed as a plain `default_value:` override so evaluation succeeds.
  - Normalizes the base template's Eclipse-Foundation defaults out of vig-os state (they would otherwise be phantom drift): overrides `custom_properties`, `_repositories`, `security_managers`, and `teams` with `:`/`::` instead of the import's `+:`/`+::` appends, dropping the inherited `eclipse_project` org property, the `.eclipsefdn` example repo, the Eclipse security-manager teams, and the default org teams. vs-dolt's code-scanning languages are collapsed to the schema-valid `javascript-typescript`.
  - `otterdog/vig-os/vendor/otterdog-defaults/` vendors the base-template libsonnet (jsonnetfmt-formatted) so `otterdog validate --local` runs offline; the Eclipse-Foundation-specific Python validation/PMI hooks are omitted (they enforce Eclipse-only org policy).
  - Dev shell seeds a placeholder `OTTERDOG_TOKEN` (`flake.nix` `shellHook`) so the guarded `just validate` (jsonnetfmt + `otterdog validate --local`) is green locally; `/otterdog.json` added to `CODEOWNERS`.
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
