---
type: issue
state: closed
created: 2026-09-23T09:14:52Z
updated: 2026-09-23T11:41:42Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/226
comments: 0
labels: priority:low, change-request
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-23T21:09:34.652Z
---

# [Issue 226]: [[CHANGE-REQUEST] tessera: main protection requires a `nix flake check` context main's CI cannot produce](https://github.com/vig-os/org-config/issues/226)

## Target repo(s)

`vig-os/tessera` — its `main` branch protection rule, declared in `otterdog/vig-os/vig-os.jsonnet:909-916`.

## Problem

`tessera`'s `main` protection requires a `any:nix flake check` status context that **no workflow on `main` can produce**, so every PR into `main` is structurally unmergeable and lands only by admin override (`enforce_admins` is off, which is the sole reason `main` is not simply frozen).

Verified live:

- Declared: `required_status_checks: ['any:nix flake check']`, `requires_strict_status_checks: true`. Live `/branches/main/protection` agrees — one context, `nix flake check`, `app_id: null`, `strict: true`. Config and live match; this is a deliberate change to make, not drift to adopt.
- `main`'s `.github/workflows/ci.yml` defines exactly two PR jobs: `Dependency Review` and `CI Summary`. Nothing named `nix flake check`. Its own header comment says so: *"Tessera's actual gate is `nix flake check` (workspace clippy/test/fmt, wasm, OCI/WORM roundtrips, guardrails), which lives on the development branch."*
- `release-nix.yml`, the workflow that emits that context, exists only on `dev` — `main` carries `ci.yml`, `release.yml`, `scorecard.yml`, `sync-issues.yml` and nothing else.
- `tessera` has **no rulesets** (`/rulesets` is empty, `/rules/branches/main` returns `[]`), so classic branch protection is the whole story here. It is also the only repo in `vig-os.jsonnet` still using classic `branch_protection_rules` rather than `newRepoRuleset` — which matters for the syntax below.

This is the same unsatisfiable-control pathology as #195 (org-config's own count-1 approval gate), #115 (devkit) and #167 (devkit-smoke-test): a rule that reads like a gate, gates nothing, and whose only observable effect is normalizing the bypass that routes around it. It was flagged in passing by the merger of [tessera#383](https://github.com/vig-os/tessera/pull/383) — *"this PR's required check will never report on its own — it needs an admin merge… Worth reconciling that protection rule vs. main's actual CI separately"* — and never followed up.

## Desired change — two steps, deliberately

### Step 1 (this issue): make the rule satisfiable

In `otterdog/vig-os/vig-os.jsonnet`, `tessera` › `branch_protection_rules` › `main`:

```jsonnet
required_status_checks: [
  // Un-prefixed = bound to the `github-actions` app, exactly as the `dev`
  // rule above. Numeric `15368:` prefixes are RULESET syntax and are invalid
  // in a classic branch protection rule — see the note below.
  'CI Summary',
],
```

`CI Summary` is `main`'s own aggregating job (`needs: [dependency-review]`, `if: always()`, and it `exit 1`s when dependency-review failed), so one context covers the lane. Keep `requires_strict_status_checks: true` — with a context that can actually report, "up to date with base" finally means something.

**Syntax note — the prefix forms are per-model, not per-org.** In a classic branch protection rule, otterdog resolves the prefix as an **app slug** via `GET /apps/{slug}` (`models/branch_protection_rule.py:341-361` → `get_app_node_ids` → `rest/app_client.py:61`), with un-prefixed defaulting to `github-actions` and `any:` meaning unbound. There is no numeric branch. A `15368:` prefix here resolves as `GET /apps/15368`, 404s, and raises `RuntimeError: failed retrieving app node id` — and because that resolution lives on the write path, **plan still passes and the failure lands at apply**, after the `production` approval. The numeric form belongs to rulesets only (`models/ruleset.py:208`, `elif app_slug.isdigit()`), which is where every `15368:` literal in this config sits.

Be explicit about what step 1 buys: `main`'s CI runs one real job, so the gate means *"no new high-severity dependency vulnerabilities"*. That is thin. It is also honest, satisfiable, and ends the routine admin bypass — which is the whole point of the #195/#115/#167 lineage.

### Step 2 (follow-up, at the first alpha cut)

When `dev` promotes and `main` inherits the real CI, the required context should become the actual flake check. Track it then; it is not actionable while `main` holds a landing README and a stale tree.

Out of scope: the `dev` rule (its un-prefixed `nix flake check` is correct for this same code path), and the `default_branch` adoption already merged in #227.

## Justification

`main` is about to matter. `0.1.0-alpha.1` is held pending the first release cut ([tessera#383](https://github.com/vig-os/tessera/pull/383)), after which `dev` → `main` promotions become routine — and each one currently needs an admin bypass to merge. Step 1 is cheap now; discovering the gate mid-promotion is not.

## Acceptance criteria

- [ ] Plan preview shows exactly one changed field on `tessera` › `main` protection.
- [ ] Apply completes green — the prefix form is the thing most likely to break here, and it breaks at apply, not at plan.
- [ ] Live `/repos/vig-os/tessera/branches/main/protection` lists `CI Summary` bound to the `github-actions` app as the sole required context, `strict: true`.
- [ ] The next `dev` → `main` PR merges on green CI with no admin override.

## Urgency

Low — no data or access is at risk, and `main` receives roughly one PR a quarter today. It becomes blocking at the first alpha cut.

## Additional context

Surfaced while evaluating the #215 drift issue (`tessera` default branch, adopted in #227), filed separately to keep that adoption a one-line diff. Same lineage as #195 / #115 / #167.

---

**Correction (2026-09-23).** The original body recommended `'15368:CI Summary'` and framed the change as a single step. Both were wrong: the numeric prefix is ruleset-only syntax that would have failed this repo's apply (see the syntax note), and the "revisit at the alpha cut" dismissal of porting the flake check contradicted the same alpha cut used to justify the issue's urgency. Body corrected on both points; the problem statement and priority are unchanged.

