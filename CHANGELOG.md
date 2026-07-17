# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- **Adopt vigOS devkit 1.3.1** ([#2](https://github.com/vig-os/org-config/issues/2))
  - Greenfield scaffold of the shared vigOS dev environment in `direnv` mode: `flake.nix` + `.envrc` dev-shell, layered `justfile`s, managed pre-commit and `.github/` CI, and the `.vig-os` project manifest.
  - Pins move in lockstep: `.vig-os` `DEVKIT_VERSION=1.3.1`, `flake.nix` `vigos.url = "github:vig-os/devkit?ref=1.3.1"`, `flake.lock` locked to the 1.3.1 revision.
  - No language template and no release tag scheme yet (`DEVKIT_TAG_PREFIX`/`DEVKIT_FLOATING_TAGS` unset); the managed `codeql.yml` degrades to the language-less case (`actions` leg only, workflows-only push paths, vig-os/devkit#1142). Release workflows ship dormant.

### Changed

### Deprecated

### Removed

### Fixed

### Security
