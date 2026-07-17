---
id: adr-0005-repo-tooling
type: adr
status: accepted
source: internal
date: 2026-07-17
owner: carlos.vigo@exoma.ch
tags: [tooling, nix, otterdog, ci]
refs: [org-config#1, org-config#12, org-config#ADR-0001, org-config#ADR-0003, org-config#ADR-0007]
---

# ADR-0005 — Repo tooling

- Status: Accepted
- Date: 2026-07-17
- Component / area: `org-config` repo dev tooling and CI runtime (otterdog + supporting tools)
- Reviewers: Carlos Vigo (v1 plan approved in working session 2026-07-17; issue #1 plan comment)

## Context

`org-config` adopts Otterdog as its reconciliation engine (org-config#ADR-0001) and
keeps only a thin strict-drift layer in-house. Otterdog is a Python tool that renders
[Jsonnet](https://jsonnet.org/) config and diffs it against the live GitHub API; the
secrets flow uses SOPS/age (org-config#ADR-0003). Two distinct audiences need this
toolchain, and their constraints pull in opposite directions:

- **Humans** working in the repo want a single reproducible shell with otterdog and
  every supporting tool (`sops`, `age`, `jsonnet`) already present. This repo runs in
  devkit **direnv mode** (`.vig-os`: `DEVKIT_MODE=direnv`, `DEVKIT_VERSION=1.3.1`), so
  `flake.nix` already exposes a `mkProjectShell` dev-shell entered via `direnv allow`
  or `nix develop`.
- **CI and downstream consumers** run the plan / apply / drift workflows. Downstream
  orgs (`exo-pet`, `exoma-ch`, `MorePET`) each receive a **private `org-config` repo
  created from template — never a fork** (org-config#ADR-0006), and must be able to run
  `plan` and scheduled drift without depending on this repo's Nix stack. Emergency runs
  (an incident where the flake or devcontainer is broken or unavailable) must likewise
  work standalone.

There is a further coupling to testing: org-config#ADR-0007 records that the strict-drift
layer is unit-tested (L1) against recorded `otterdog plan` fixtures, so the otterdog
version must be pinned — a floating version would let the plan-output format drift and
silently break fixture parsing. Whatever we pick for CI must therefore pin an exact
otterdog version, not a range.

The open question is how CI (and downstream forks) obtain otterdog and its supporting
tools: reuse the human dev-shell / devcontainer flake, or stay self-sufficient.

## Alternatives considered

Mandatory.

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **Dev-shell + pinned `uvx` in CI** | Human shell; CI = `uvx`+`gh`; pin anchors fixtures | Two entry points | Chosen |
| devcontainer / flake dep in CI | One version source | CI and every fork depend on the flake | Rejected |
| `pip` / `requirements.txt` | Familiar; explicit list | No isolation; weaker reproducibility than a pin | Rejected |
| Vendored otterdog | Immune to PyPI outage | Maintenance burden; defeats Renovate bumps | Rejected as default |

## Decision

**Humans** consume the vigOS dev-shell: `flake.nix`'s `mkProjectShell` gains `sops`,
`age`, and `jsonnet` as project `extraPackages`, and otterdog is run through `uvx`.

**CI** (plan / apply / drift workflows, and every downstream template-derived config
repo) stays self-sufficient on an **exact-version-pinned `uvx otterdog` plus `gh`**, and
never depends on the `vig-os/devcontainer` flake — so downstream forks and emergency
runs work standalone. The exact-version pin does double duty: it is also the
plan-output fixture-format anchor that keeps the drift layer's recorded-plan tests
stable (org-config#ADR-0007).

## Rationale

- **Self-sufficiency is the hard requirement.** Downstream config repos are private,
  live inside the orgs they govern, and are created from template rather than forked
  (org-config#ADR-0006); they cannot be made to evaluate this repo's Nix flake or pull
  the `vig-os/devcontainer` image just to run a read-only `plan`. Direnv-mode CI already
  runs on the host runner without the flake loader, so a flake-in-CI dependency would be
  a regression for the exact runs that matter most.
- **`uvx` is the lightest reproducible runner.** It executes a pinned tool in an
  isolated, throwaway environment with no manual venv and no runner-Python pollution —
  the same isolation a checked-in `requirements.txt` would need scaffolding to achieve,
  from a single pin line.
- **One pin, two guarantees.** Pinning the exact otterdog version both freezes CI
  behaviour and freezes the `otterdog plan` output format that the L1 fixtures parse
  (org-config#ADR-0007). A single source of truth for "which otterdog" avoids a class of
  drift between what CI runs and what the tests were recorded against.
- **Humans still get the full shell.** Nothing above weakens local ergonomics: the
  dev-shell carries every tool, so contributors do not hand-install otterdog, sops, age,
  or jsonnet.

## Consequences

- **Renovate owns the pin.** The exact `uvx otterdog` version is bumped by Renovate,
  keeping the tool current without hand edits.
- **A pin bump that breaks fixture parsing is an early-warning signal, not a nuisance.**
  Because the same pin anchors the L1 plan fixtures, a Renovate bump that makes fixture
  parsing fail is the first, cheap indication that upstream otterdog changed its plan
  output format — caught in a PR against recorded fixtures rather than in a live drift
  run. The bump PR is the place to re-record fixtures deliberately.
- **Two otterdog entry points must stay coherent.** The dev-shell path (`uvx` inside the
  shell) and the CI path (pinned `uvx`) must not silently diverge in major version;
  Renovate bumping one implies re-checking the other.
- **`flake.nix` is edited, `ci.yml` is not.** Adding `sops`/`age`/`jsonnet` is a project
  `extraPackages` edit (the block `flake.nix` reserves as "yours"); the pinned `uvx`
  invocation lives in repo-owned plan/apply/drift workflows, never in managed `ci.yml`
  (org-config#ADR-0007).
- **Downstream inherits self-sufficiency for free.** Template-derived private config
  repos copy the pinned-`uvx` workflows and run without any vigOS flake or image.

## Corrections

None to date. Entries are added here only if an assumption above is later found wrong,
preserved verbatim for audit:

> **YYYY-MM-DD:** original claimed X; source Y showed Z. Updated above.

## Open questions / supersession triggers

- **otterdog stops shipping to PyPI, or gains a native dep `uvx` cannot resolve on a
  runner.** Would force the vendor/pin-at-minimum fallback (already the org-config#ADR-0001
  insurance) or a container image — revisit this ADR.
- **A `uvx`-at-run-time supply-chain incident** (PyPI unavailability during an
  emergency, or a compromised release) makes on-demand resolution unacceptable → move to
  the vendored path.
- **org-config#ADR-0007 changes the fixture strategy** such that plan-format stability no
  longer rides on the tool pin — removes one of the two reasons for an *exact* pin and
  may relax it to a range.
- **The devcontainer flake becomes cheap and universally available to private
  downstream repos** (e.g. a lightweight, offline-capable form) — would reopen the
  "flake dependency in CI" option.

## References

- [org-config#1 — reevaluation and v1 plan comment](https://github.com/vig-os/org-config/issues/1)
- [org-config#12 — ADR-0005 decision summary](https://github.com/vig-os/org-config/issues/12)
- `flake.nix` — `mkProjectShell` dev-shell; `.vig-os` (`DEVKIT_MODE=direnv`, `DEVKIT_VERSION=1.3.1`)
- org-config#ADR-0001 — Otterdog engine choice (and fork/vendor bus-factor insurance)
- org-config#ADR-0003 — SOPS/age secrets backend
- org-config#ADR-0006 — distribution topology (private template-derived config repos)
- org-config#ADR-0007 — CI and testing (managed `ci.yml`, plan fixtures, extension points)
- [Otterdog](https://github.com/eclipse-csi/otterdog)
- [uv / uvx](https://docs.astral.sh/uv/)
- [vig-os/devkit](https://github.com/vig-os/devkit)
