---
type: issue
state: open
created: 2026-10-09T19:15:53Z
updated: 2026-10-09T19:15:53Z
author: gerchowl
author_url: https://github.com/gerchowl
url: https://github.com/vig-os/org-config/issues/332
comments: 0
labels: area:ci, change-request
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-10-10T08:12:35.259Z
---

# [Issue 332]: [vigil: make the dev ruleset's required CI Summary check strict (up to date with base)](https://github.com/vig-os/org-config/issues/332)

From the vigil 0.1.0 milestone review: vigil#29's green `CI Summary` ran 16:52–16:55Z, before vigil#27 (a rewrite of the rotation module that #29 exercises) merged at 16:55:48Z. Because the required check isn't strict, #29 merged without re-running against the new base. It still passed when re-run locally afterwards, but that was luck, not a gate. **Ask:** in `otterdog/vig-os/vig-os.jsonnet`, have vigil's `orgs.devProtection(checks=['15368:CI Summary'], …)` require branches to be up to date (`strict`). The repo already has `allow_update_branch: true` for the cost side. (The rulesets themselves are still pending apply per #328.)
