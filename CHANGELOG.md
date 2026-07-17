# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- **Strict-drift layer + scheduled reconciliation** ([#20](https://github.com/vig-os/org-config/issues/20))
  - `src/drift_layer/`: the in-house strict-drift core (ADR-0002/0007) — a pure-function pipeline with the GitHub client injected at the edge. `parser.py` turns `otterdog plan --local --no-web-ui` output into one `DriftRecord` per resource-level divergence (owning otterdog's `+`/`~`/`!`/`-` block syntax and the `Plan: X to add, Y to change, Z to delete` trailer, tolerating the uv/runner preamble); `allowlist.py` marks config-driven expected drift (`drift-allowlist.toml`) so known artifacts never open issues; `reconcile.py` diffs records against live issues into open/update/close actions; `github_client.py` is the stdlib-only REST edge (a `GitHubClient` Protocol tests fake).
  - Lifecycle (ADR-0002): exactly one deduplicated `drift`+`critical` issue per divergence, keyed by a stable per-resource fingerprint in a hidden `<!-- drift-fingerprint: … -->` marker; recurrence updates the existing issue in place (never duplicates) and adds a timestamped comment; resolution closes it with a comment. Title convention `Drift: <resource>`.
  - `drift-layer` CLI (`uv run drift-layer` / `python -m drift_layer`) with `--dry-run`; issues token read from `$GITHUB_TOKEN`.
  - `.github/workflows/drift.yml`: scheduled (daily 03:17 UTC) + `workflow_dispatch`; joins the static `otterdog-mutate` concurrency group (`cancel-in-progress: false`) so drift and apply never race; full org-wide App token for the read-only plan leg, a second `issues: write`-narrowed token for the issue-ops leg (ADR-0004/0007 least-privilege).
  - TDD: `tests/` with recorded plan fixtures (PR #41 ECA drift / 17 changes, PR #42 vs-dolt-only, synthetic empty and mixed-symbols plans) drives the L1 core. Repo becomes a `uv` project: `pyproject.toml` (`org-config-drift`, `requires-python >=3.12`, ruff + pytest, `src/` layout) + `uv.lock`; the `justfile.project` pytest/lint recipes activate.
- **Apply-on-merge workflow** ([#19](https://github.com/vig-os/org-config/issues/19))
  - `.github/workflows/apply.yml` runs a mutating `otterdog apply --local --no-web-ui --force` of the committed config against live `vig-os` on `push` to `dev` touching `otterdog.json`/`otterdog/**` (engine/workflow edits carry no config delta and are excluded from `paths:`), plus `workflow_dispatch` for reruns (ADR-0007 split cadence: config applies from `dev` on merge).
  - The job runs in the `production` environment (required reviewer `c-vigo`, `dev`-only deployment branch policy): entering it pauses the run until the deployment is approved — the designed human gate before any write token touches live `vig-os`. `push` fires only on this repo (never a fork), so org-admin credentials are never exposed to fork code; an explicit `github.repository` guard asserts this.
  - A static `otterdog-mutate` concurrency group with `cancel-in-progress: false` serializes all mutations without cancelling mid-apply; the future scheduled drift workflow (#20/#21) must reuse the same group so apply-vs-drift never races.
  - Uses the full App installation token (ADR-0004 Corrections) with two scoped, justified `github-app` inline zizmor ignores; least-privilege `permissions: contents: read`; `persist-credentials: false` checkout.
  - `--force` is mandatory for unattended apply (otterdog 1.3.4 prompts and blocks on stdin otherwise); `--local` gates only the vendor re-fetch (same `_init_base_template` skip as `plan`/`validate`), so apply evaluates the exact committed tree; `--delete-resources` is omitted so absent resources are never deleted. Reports otterdog's own apply output to the job summary (truncated safely); a nonzero exit is a failed/partial mutation and reddens the job (unlike plan, mutation errors are not benign report content).
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

- **Normalize the base template's ECA status check out of all rulesets** ([#17](https://github.com/vig-os/org-config/issues/17)): the first live plan (PR #41, 17 changes) showed `+ "eclipse-eca-validation:eclipsefdn/eca"` on every ruleset with status checks — `newStatusChecks()`/`newBranchProtectionRule()` seed that Eclipse default and the imported config's `status_checks+:` appends inherited it (same class as the `custom_properties` `null + array` fix). All 15 ruleset `status_checks` lists and tessera's branch-protection `required_status_checks` are now plain overrides expressing live state exactly (cross-checked read-only against `gh api .../rulesets`); no other template-seeded injection remains (all other appended fields have empty template defaults). The only remaining plan line is the known benign `vs-dolt` `code_scanning_default_languages` artifact (otterdog's live read filters out `javascript-typescript` while its schema rejects the split values — upstream inconsistency, already baselined in plan.yml's footnote).

### Security
