---
type: issue
state: closed
created: 2026-08-08T07:26:48Z
updated: 2026-08-08T07:33:41Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/128
comments: 0
labels: none
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-09T03:45:12.895Z
---

# [Issue 128]: [[BUG] otterdog apply cannot patch rulesets with numeric integration-id status checks (GET /apps/15368 → 404)](https://github.com/vig-os/org-config/issues/128)

Apply run [31246081165](https://github.com/vig-os/org-config/actions/runs/31246081165) (for #127) failed:

```
Error: failed to apply patch: CHANGE - repo_ruleset[name="Main protection", repository=devkit-smoke-test]
failed retrieving app node id:
Exception while accessing 'https://api.github.com/apps/15368': (status=404, ...)
```

`GET /apps/{app_slug}` takes a **slug**, not a numeric id — `15368` is the numeric id of the GitHub Actions app (slug `github-actions`). Our jsonnet encodes status checks as `'15368:CI Summary'` throughout (imported form). Ruleset **creation** apparently tolerated it, but otterdog 1.3.4's ruleset **patch** path resolves the app node id via the slug endpoint and 404s, so any config change touching such a ruleset cannot be applied.

Plan (#127's PR check) passed — plan does not resolve app node ids, so this class of failure only surfaces at apply.

Immediate workaround used for #127: live value reconciled to the committed config by a direct API `PUT` on the ruleset (maintainer-run), after which otterdog computes no diff for the ruleset and apply is unblocked.

Candidate fix: switch status-check entries from `'15368:CI Summary'` to the slug form (e.g. `'github-actions:CI Summary'`) if otterdog supports it, or upgrade otterdog if fixed upstream. Needs a low-stakes test ruleset change to verify the patch path before trusting it.
