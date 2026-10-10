---
type: issue
state: open
created: 2026-10-09T14:16:20Z
updated: 2026-10-09T15:37:05Z
author: gerchowl
author_url: https://github.com/gerchowl
url: https://github.com/vig-os/org-config/issues/331
comments: 1
labels: bug, priority:high, area:ci
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-10-10T08:12:35.632Z
---

# [Issue 331]: [vigil: Dependency graph unavailable, so the managed Dependency Review lane fails and CI Summary can never go green](https://github.com/vig-os/org-config/issues/331)

vig-os/vigil (declared config-first in #327/#328, created 2026-10-09T13:07Z) has no usable dependency graph:

- Every PR's **Dependency Review** job fails with `Dependency review is not supported on this repository. Please ensure that Dependency graph is enabled` (e.g. https://github.com/vig-os/vigil/actions/runs/37942502773 on vigil#19), so the required `CI Summary` is red on every PR.
- `gh api repos/vig-os/vigil/dependency-graph/compare/dev...feature/18-run-rust-checks` → 404, `…/dependency-graph/sbom` → 404, while the same calls work for vig-os/scitadel and vig-os/devkit. `vulnerability-alerts` → 204 (enabled). The repo is PUBLIC, and `main` carries `Cargo.toml` + `Cargo.lock`.
- `otterdog/vig-os/vig-os.jsonnet`'s `newRepo('vigil')` declares no dependency-graph / dependabot-alerts setting.

**Ask:** enable Dependency graph for vigil (Settings → Code security), and declare it in the vigil block (e.g. `dependabot_alerts_enabled: true`, which implies the graph) so it doesn't drift and new config-first repos get it by default. Until then no vigil PR can merge with a green `CI Summary`.
---

# [Comment #1]() by [gerchowl]()

_Posted on October 9, 2026 at 03:37 PM_

Dependency graph has been enabled on vigil (2026-10-09); Dependency Review now passes (vigil#19). Leaving this open for the otterdog declaration, so it doesn't drift.

