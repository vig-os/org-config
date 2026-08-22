---
type: issue
state: closed
created: 2026-07-20T20:41:41Z
updated: 2026-08-10T13:12:24Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/69
comments: 2
labels: none
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-11T03:47:06.754Z
---

# [Issue 69]: [otterdog 1.3.4 cannot patch/create rulesets with numeric status-check prefixes (15368:...)](https://github.com/vig-os/org-config/issues/69)

The apply run for #65 (run 29776453420) failed partially: the `Signed commits` ruleset was created, but the `Main protection` patch (adding the `#OrganizationAdmin` bypass) failed with:

```
failed to apply patch: CHANGE - repo_ruleset[name="Main protection", repository=org-config]
failed retrieving app node id:
Exception while accessing 'https://api.github.com/apps/15368': (status=404, ...)
```

Root cause — upstream [eclipse-csi/otterdog#695](https://github.com/eclipse-csi/otterdog/issues/695): `import` renders live required status checks as `<integration_id>:<context>` (GitHub's ruleset REST payload carries only the numeric `integration_id`, and `15368` is the GitHub Actions app), but on any ruleset **write** (`create`/`update`), `get_mapping_to_provider` treats the prefix as an app *slug* and calls `GET /apps/15368`, which 404s. The two directions are inconsistent in 1.3.4 (latest release):

- numeric config (`15368:CI Summary`, what import emits and what we commit): plan compares clean, but every ruleset write fails;
- slug config (`github-actions:CI Summary`): writes succeed, but live always renders back as `15368:...`, so every plan shows a permanent spurious diff — unacceptable under the strict-drift design (ADR-0002).

Consequence: **any change to a ruleset that declares status checks fails at apply** across the whole config (org-config, devkit, commit-action, sync-issues-action, devkit-smoke-test all use `15368:` checks). Ruleset creates without status checks (e.g. `Signed commits`) are unaffected.

Interim procedure (used for #65): apply the declared change to the live ruleset manually (`gh api -X PUT /repos/vig-os/org-config/rulesets/<id>` with the target field), which reconciles live to the committed config and returns plan/drift to an empty diff.

Resolution: track upstream #695; when a fixed otterdog release lands, bump the `justfile.project` pin (and migrate the committed `15368:` tokens if the fix changes the canonical rendering).

Refs: #65
---

# [Comment #1]() by [c-vigo]()

_Posted on August 10, 2026 at 09:49 AM_

Closed via #145 (merge 0cb9ac6, apply run 31376064384): otterdog pin 1.3.4 -> 1.4.0 (upstream fix eclipse-csi/otterdog#700 for #695, write-path-only) + the eighteen status-check tokens restored to numeric `15368:` form. Canonical prefix form is per-app — numeric for first-party apps (never org installations, so live always reads back numeric), slug for org-installed apps — recorded inline in the jsonnet. Phantom drift #130–#141 auto-closed by drift run 31376253402. The `gh api` manual-PUT interim stays the fallback until a real ruleset write under 1.4.0 confirms end-to-end (nightly Testbed E2E).

---

# [Comment #2]() by [c-vigo]()

_Posted on August 10, 2026 at 01:12 PM_

Upstream report for the read-side asymmetry filed: eclipse-csi/otterdog#732 (status checks bound to non-installed apps always render numeric on read; suggested slug->id canonicalization at diff time via `GET /apps/{app_slug}`). Until it lands, the per-app canonical form documented in the jsonnet stands.

