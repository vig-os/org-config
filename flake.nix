{
  description = "Project development environment (vigOS toolchain).";

  # Downstream repos consume the shared toolchain as a flake INPUT, so updating
  # the dev environment means bumping that input — it never overwrites your
  # files. To update: `nix flake update vigos`.
  inputs = {
    # The shared vigOS toolchain (single source of truth).
    # This scaffold deliberately FLOATS on the default branch so a fresh
    # project works before its first pin. Once you depend on stability
    # (especially the vigos.* home-manager module options), pin a release
    # tag instead and bump deliberately:
    #   vigos.url = "github:vig-os/devkit?ref=<tag>";
    # Policy: https://github.com/vig-os/devkit/blob/main/docs/NIX.md
    # "Home-manager modules - versioning & release policy".
    vigos.url = "github:vig-os/devkit?ref=1.4.0-rc5";
    # Follow vigos's pinned nixpkgs + flake-utils so your tools match the
    # toolchain exactly (one resolved nixpkgs, no drift).
    nixpkgs.follows = "vigos/nixpkgs";
    flake-utils.follows = "vigos/flake-utils";
  };

  outputs =
    {
      self,
      vigos,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [ vigos.overlays.default ];
          config.allowUnfree = true;
        };

        # ────────────────────────────────────────────────────────────────────
        # Your project tools go here. This block is YOURS: a dev-environment
        # update never overwrites it (scaffold-once / never-overwrite, the same
        # guarantee as justfile.project and docker-compose.project.yaml).
        #
        #   extraPackages = pkgs: [
        #     pkgs.postgresql_16
        #     pkgs.ffmpeg
        #   ];
        # ────────────────────────────────────────────────────────────────────
        extraPackages = pkgs: [
          # Otterdog toolchain (ADR-0005). otterdog itself is run via `uvx`
          # (pinned in justfile.project) so CI and downstream template repos
          # stay self-sufficient without this flake; the dev-shell carries the
          # supporting tools so humans do not hand-install them.
          pkgs.sops # secrets: SOPS/age backend (ADR-0003)
          pkgs.age # secrets: age keys for SOPS
          pkgs.go-jsonnet # jsonnet + jsonnetfmt (config renderer / L0 fmt)
          pkgs.actionlint # L0: GitHub Actions workflow linter
          pkgs.zizmor # L0: GitHub Actions security auditor
        ];
      in
      {
        # The dev shell = the shared vigOS toolchain + your extras.
        # `direnv allow` (via .envrc) or `nix develop` enters it.
        devShells.default = vigos.lib.mkProjectShell {
          inherit pkgs;
          extraPackages = extraPackages pkgs;

          # `otterdog validate --local` (L0, ADR-0007) always resolves the
          # `env` credential provider before it evaluates the config, so it
          # needs OTTERDOG_TOKEN present even though local validation makes no
          # authenticated call (the org declares no teams, and the per-repo
          # code-scanning language checks fail soft on 401). Seed a clearly
          # non-functional placeholder so `just validate` is green out of the
          # box in the dev shell; a real token in the environment (CI, or a
          # human running `plan`) always wins via the `:-` default. This is a
          # dummy, NOT a secret — real credentials land with SOPS/age (#22).
          shellHook = ''
            echo "devcontainer dev environment loaded (nix)"
            export OTTERDOG_TOKEN="''${OTTERDOG_TOKEN:-otterdog-local-validate-placeholder}"
            # libstdc++ for native extensions of uvx-run Python tools (otterdog's
            # rjsonnet): a Nix CPython's loader does not search /usr/lib, so the
            # manylinux .so fails with "libstdc++.so.6: cannot open shared
            # object file" (same failure class as the devkit pymarkdown/pyjson5
            # drop). Exported as a VARIABLE — not a global LD_LIBRARY_PATH,
            # which would leak the nix libstdc++ into every child process — and
            # consumed command-scoped by the otterdog invocation in
            # justfile.project's `validate` recipe. Note: direnv-mode CI
            # forwards only the dev-shell PATH (setup-devkit-toolchain), never
            # shellHook env, so this export covers `nix develop`/direnv entry
            # only; the recipe independently derives the same dir from the
            # dev-shell `cc` when this variable is absent. The interpolation
            # also roots the lib in the shell closure. libstdc++.so.6 is
            # backward-compatible, so pointing a manylinux wheel at nix's
            # (GCC 15) copy is safe on the CI host runner and on NixOS alike.
            export VIGOS_STDCPP_LIB="${pkgs.stdenv.cc.cc.lib}/lib"
          '';

          # Opt into the flake-generated pre-commit config (#883): the shared
          # base hook set sourced from the pinned vigos toolchain, replacing the
          # hand-managed .pre-commit-config.yaml. In direnv mode CI runs on the
          # host runner, where the scaffolded YAML's upstream `pymarkdown` hook
          # cannot load its `pyjson5` native dep (no FHS libstdc++ off the flake
          # loader path) — the generated set omits pymarkdown (not in nixpkgs),
          # matching the sibling direnv consumers (commit-action,
          # sync-issues-action). .pre-commit-config.yaml is now a generated store
          # symlink, gitignored via .gitignore.project.
          #
          # L0 config-specific hooks (ADR-0007) composed on top of the shared
          # base set. Custom `language = "system"` hooks resolve their tools
          # from the dev-shell PATH (extraPackages above), the same pattern the
          # devkit base uses for actionlint/shellcheck. zizmor is deliberately
          # NOT a hook — it needs the repo-root zizmor.yml baseline and stays in
          # `just validate` only (see justfile.project) so a devkit-managed
          # workflow finding can never turn `just precommit`/CI red.
          hooks = {
            # jsonnetfmt --test: fail on unformatted otterdog jsonnet. No-op
            # until the config lands (#17): with no matching files prek skips
            # it. go-jsonnet's implementation, per ADR-0005.
            jsonnetfmt = {
              enable = true;
              name = "jsonnetfmt (check otterdog jsonnet formatting)";
              entry = "jsonnetfmt --test";
              language = "system";
              files = "^otterdog/.*\\.(jsonnet|libsonnet)$";
            };
            # actionlint over this repo's workflows (auto-discovery, like the
            # devkit base hook — pass_filenames = false).
            actionlint = {
              enable = true;
              name = "actionlint (lint GitHub Actions workflows)";
              entry = "actionlint";
              language = "system";
              files = "^\\.github/workflows/.*\\.ya?ml$";
              pass_filenames = false;
            };
          };

          # Opt-in: let the flake GENERATE .pre-commit-config.yaml from the
          # shared base hook set instead of hand-managing the scaffolded
          # YAML — toggle base hooks, add per-hook/global excludes, or add
          # fully custom hooks; hook updates then flow with `nix flake
          # update vigos`, and your customization lives HERE (preserved).
          # Contract + migration steps:
          # https://github.com/vig-os/devkit/blob/main/docs/MIGRATION.md ("Customizing
          # pre-commit hooks from the project flake"). Uncomment to opt in, then
          # delete .pre-commit-config.yaml (the generated config refuses to
          # overwrite an existing file). The generated store symlink is ignored
          # automatically on (re)scaffold (#1092); add durable root ignores you
          # own to .gitignore.project.
          #
          #   hooks = {
          #     typos.enable = false;                    # toggle a base hook
          #     detect-private-keys.excludes = [ "worker/src/index\\.ts" ];
          #     my-data-check = {                        # fully custom hook
          #       enable = true;
          #       entry = "./scripts/check-dat.sh";
          #       files = "\\.dat$";
          #       language = "system";
          #     };
          #   };
          #   hooksExcludes = [ "^data/stopping/" "\\.dat$" ]; # global excludes
        };

        # Opt-in local dev services (#795): a daemonless process-compose stack
        # (Postgres, SeaweedFS/S3, Redis, …) with service versions from the
        # pinned vigos nixpkgs — no Docker/Podman daemon, no extra flake
        # inputs. Uncomment, then `nix run .#services` (or enable the
        # `services` recipe in justfile.project); service state lands in
        # ./data — add it to .gitignore.
        #
        #   packages.services = vigos.lib.mkProjectServices {
        #     inherit pkgs;
        #     modules = [ { services.postgres."db".enable = true; } ];
        #   };

        # Future (upstream, opt-in): vigos may expose modular language shells —
        # e.g. `vigos.devShells.${system}.{cpp,geant4,dataAnalysis}` — that you
        # select without changing this scaffold. Out of scope today.
      }
    );
}
