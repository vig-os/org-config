---
type: issue
state: closed
created: 2026-10-09T14:16:20Z
updated: 2026-10-11T14:14:31Z
author: gerchowl
author_url: https://github.com/gerchowl
url: https://github.com/vig-os/org-config/issues/331
comments: 2
labels: bug, priority:high, area:ci
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-10-12T08:46:31.599Z
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

---

# [Comment #2]() by [gerchowl]()

_Posted on October 11, 2026 at 02:14 PM_

Resolved, 2026-10-11.

- **Live:** `GET repos/vig-os/vigil/dependency-graph/sbom` returns 13 packages, and **Dependency Review passes** on the open vigil PRs (#84, #85).
- **Config: already declared, nothing to add.** `orgs.newRepo` defaults `dependabot_alerts_enabled: true` (`otterdog/vig-os/vendor/otterdog-defaults/otterdog-defaults.libsonnet:55`), so vigil's block inherits it. The org-level `dependency_graph_enabled_for_new_repositories` is asserted `true` in `unmanaged-controls.toml` (`new-repo-dependency-graph`) and is `true` live.

So new config-first repos already get it by default. A freshly created repo's graph can lag until it is first populated (stepv needed the same toggle, vig-os/stepv#16). If the next config-first repo shows it again, check Settings → Code security before changing config.

