# `YOUR_ORG/org-config`

Declarative configuration for the **`YOUR_ORG`** GitHub organization, governed by
the [`vig-os/org-config`](https://github.com/vig-os/org-config) engine (ADR-0006).

> **Onboarding note:** this file is the repo's own README. During onboarding it is
> renamed from `README.repo.md` to `README.md`, replacing the template's
> onboarding runbook (which is not carried into the repo). If you still see the
> onboarding runbook here, finish
> [`vig-os/org-config` template onboarding](https://github.com/vig-os/org-config/blob/main/template/README.md)
> first.

## What this repo is

A **private** repo that holds only this org's configuration — no engine code. It
contains:

- `otterdog.json` + `otterdog/YOUR_ORG/` — the declarative Otterdog config for the
  org (settings, repos, rulesets, secrets).
- `.github/workflows/` — thin caller workflows that `uses:` the reusable
  `plan`/`apply`/`drift` workflows of `vig-os/org-config`, **pinned to an exact
  tag or SHA** of that public engine. The engine logic lives upstream; only config
  data and these callers live here.
- `.sops.yaml` + `secrets/` — SOPS/age ciphertext for any org secrets (ADR-0003).
- `drift-allowlist.toml`, `.github/CODEOWNERS`, `renovate.json` — drift allow-list,
  review gates, and the pin-bump automation.

## How changes flow

1. Open a PR to `main`. The **plan** caller runs a read-only `otterdog plan` against
   the live org and posts the diff as a PR comment — nothing is applied.
2. On merge to `main`, the **apply** caller (once enabled) runs `otterdog apply`.
   How it is gated depends on what this repo can enforce:
   - **Private repo below Enterprise (dispatch-only).** Environment required
     reviewers are unavailable here (HTTP 422), so apply has **no merge trigger**:
     a human dispatches it (**Actions -> Apply -> Run workflow**) and **that
     dispatch is the approval gate**. The **apply-reminder** caller comments each
     pending apply onto the pinned **Apply dispatch tracker** issue — whose
     assignees get the mail — so a merge is never silently left unapplied, and the
     apply posts the "applied" confirmation on the same thread.
   - **Public repo or Enterprise org (apply-on-merge).** Apply runs on merge inside
     a required-reviewer `production` environment, so every mutation pauses for
     human approval.
3. The **drift** caller runs on a schedule, opening deduplicated issues for any
   divergence between the committed config and live org state (ADR-0002) — the
   backstop that catches an apply nobody ever dispatched.

This repo is **org-admin-equivalent** — it holds the App credentials and the config
that rewrites org settings. Every admin-critical path is gated by CODEOWNERS.

## Posture

Per ADR-0006, a **Free-plan** org runs plan-first / read-only until it upgrades to
GitHub Team; only then is the write (`apply`) path wired. See the engine's
[onboarding runbook](https://github.com/vig-os/org-config/blob/main/template/README.md)
and [`docs/`](https://github.com/vig-os/org-config/tree/main/docs) for the full
model.

## License

Proprietary — see [`LICENSE`](LICENSE). This config repo is **not** covered by the
engine's Apache-2.0 license.
