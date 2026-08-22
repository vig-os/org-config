---
type: issue
state: closed
created: 2026-08-21T20:36:19Z
updated: 2026-08-21T20:51:49Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/189
comments: 1
labels: change-request
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-22T02:56:11.941Z
---

# [Issue 189]: [[CHANGE-REQUEST] suppress CodeQL default setup org-wide; advanced codeql.yml is the standard](https://github.com/vig-os/org-config/issues/189)

### Target repo(s)

vig-os/tessera, vig-os/vigos-mvp, vig-os/vs-dolt — plus org-level code-security configuration `237480`

### Setting area

Code scanning / org security configuration

### Current behavior

7 of 11 org repos run the devkit-standard advanced `codeql.yml`; the other mechanism — CodeQL **default setup** — is live on exactly three repos, enabled in the committed config (`otterdog/vig-os/vig-os.jsonnet`, refs as of `7249220`):

- tessera `:850`, vigos-mvp `:890`, vs-dolt `:900` — `code_scanning_default_setup_enabled: true`
- vigos-mvp `:887-889` (`python`) and vs-dolt `:897-899` (`javascript-typescript`) — `code_scanning_default_languages+`; tessera pins no list, leaving GitHub in dynamic auto-detect mode

All three are attached to the **enforced** org code-security configuration `237480` ("Github + Advanced QL allowed", `code_scanning_default_setup: enabled`), which is what actually holds default setup on — repo-level writes to covered settings bounce off enforcement (the documented 200-OK-no-change pattern from the devkit secret-scanning rows in `unmanaged-controls.toml`).

Documented consequences of this split-brain state:

- tessera's language list flapped: GitHub auto-added `"actions"` on 2026-08-18T12:23Z with no otterdog run that day, and the plan now wants to remove it — likely a permanent tug-of-war, since applying an empty list leaves dynamic mode on.
- vs-dolt produces a perpetual cosmetic diff (GitHub returns `javascript`/`typescript` split, otterdog's validator only accepts the combined form), carried as `drift-allowlist.toml:21` plus a hand-maintained footnote in `plan.yml`'s PR comment.
- vigos-mvp's live `["python"]` scans nothing: repo language is Typst, no workflows, no CodeQL-supported code.

### Desired change

1. **Pre-step, out of otterdog's scope** (otterdog has no model for org security configurations; its only knob, `default_code_security_configurations_disabled`, covers default-for-new-repo configs only, and the org has none): flip configuration `237480`'s code-scanning field — UI: Org settings → Advanced Security → Configurations → "Github + Advanced QL allowed" → Code scanning default setup → Disabled; or `gh api -X PATCH /orgs/vig-os/code-security/configurations/237480 -f code_scanning_default_setup=disabled`. **Do not detach the configuration** — its secret-scanning declarations are load-bearing for the devkit rows in `unmanaged-controls.toml`.
2. Delete the three `code_scanning_default_setup_enabled: true` lines and both `code_scanning_default_languages+` lists. The vendored defaults (`false` / `[]`) then apply, and otterdog PATCHes `state: not-configured` on all three repos (write path confirmed in 1.4.0's `repo_client.py:555`). Must land **after** step 1 or the PATCHes bounce off enforcement.
3. Record the new expectation in `unmanaged-controls.toml`: configuration `237480` → `code_scanning_default_setup` expect `disabled`, so the daily drift run guards the out-of-otterdog control.
4. Cleanup once applied: remove the vs-dolt entry at `drift-allowlist.toml:21` and the matching benign-drift footnote in `plan.yml` — both exist only to paper over default-setup drift.

### Justification

Config-first single-source-of-truth, applied to code scanning. Default setup's state lives in GitHub's database — it flaps, is only partially modelled by otterdog, and is pinned in place by an enforced configuration the config layer cannot express. Advanced `codeql.yml` is already the de facto org standard (7/11 repos): versioned, sha-pinned by Renovate, and merge-gating via `15368:`-prefixed required status checks in otterdog-managed rulesets. After this change, code scanning reduces to one question answerable from the config tree: does the repo carry the managed workflow.

Post-change scanning coverage, stated explicitly: tessera is unscanned **until** its follow-up lands (see below — GitHub blocks CodeQL SARIF upload while default setup is on, so suppression must come first); vigos-mvp loses nothing (no CodeQL-supported code); vs-dolt is left unscanned **by decision** (out of scope here); nvd-mirror was already unscanned.

### Urgency

Low — whenever capacity allows

### Additional context

- Follow-up: vig-os/tessera issue to add the devkit-standard `codeql.yml` (`actions` leg), depends on this landing first.
- Lineage: root-caused in the #184 evaluation thread (see PR #186's plan comment showing both drift diffs). Related: #184, #186.
---

# [Comment #1]() by [c-vigo]()

_Posted on August 21, 2026 at 08:43 PM_

Data point from #186's apply run (2026-08-21): the tessera `code_scanning_default_languages` PATCH did **not** bounce off the enforced configuration 237480 — tessera's default setup now reads `state: configured, languages: [], updated_at: null`. So enforcement pins **enablement** only; language writes go through (the 200-OK-no-change pattern from the devkit secret-scanning rows is about entitlement-gated fields, not all covered settings).

Two consequences for this issue:

1. Tessera is currently scanning **nothing** (configured, zero languages), and GitHub's dynamic detection may re-add `actions` at any time, so the drift can reappear until this lands — mild urgency bump for step 1 + 2.
2. Step 2's `state: not-configured` PATCH is the part that will still be blocked while 237480 declares default setup enabled — the pre-step ordering in the issue stands unchanged.

