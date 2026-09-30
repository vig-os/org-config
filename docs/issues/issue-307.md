---
type: issue
state: closed
created: 2026-09-29T08:50:09Z
updated: 2026-09-29T13:08:01Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/307
comments: 1
labels: chore, priority:low, area:workflow, effort:small
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-30T08:09:22.310Z
---

# [Issue 307]: [chore(config): watch for duplicate Dependabot and Renovate advisory PRs on tier-A repos until 2026-10-29](https://github.com/vig-os/org-config/issues/307)

## Chore Type

Dependency update

## Description

#294 / #304 turned on Dependabot security updates (`dependabot_security_updates_enabled: true`) on the eight tier-A repos that lacked it: `commit-action`, `sync-issues-action`, `h5v`, `scitadel`, `qx`, `tessera`, `devkit-smoke-test` and `org-config` (`devkit` already had it). See the repository-settings section of [ADR-0008](https://github.com/vig-os/org-config/blob/main/docs/adr/0008-repository-protection-and-merge-policy.md#repository-settings).

Renovate may raise a PR for the same advisory. None of those repos sets `vulnerabilityAlerts` or `osvVulnerabilityAlerts` in its `renovate.json`, nor does the shared `.github/renovate-default.json` preset, and the Renovate App holds `vulnerability_alerts: read`, so Renovate's vulnerability-alert PRs are on by default.

Where they would collide:

| Repo | Renovate base branch | Dependabot target |
|---|---|---|
| `commit-action`, `sync-issues-action`, `scitadel`, `tessera`, `devkit-smoke-test` | `dev` | default branch |
| `h5v`, `org-config` | `main` | default branch |
| `qx` | no Renovate | default branch |

`scitadel`'s Renovate skips Cargo, so Cargo advisories there come from Dependabot only.

**Requirement:** one fix PR per advisory. Watch for duplicate advisory PRs (same package and advisory from both bots) until **2026-10-29**.

## Acceptance Criteria

- [ ] Checked the eight repos for duplicate advisory PRs through 2026-10-29
- [ ] If none: close with the result recorded here
- [ ] If any: choose one of the two changes below, land it, apply, and record it in ADR-0008 and `CHANGELOG.md`

## Implementation Notes

Two ways out if duplicates appear; either is valid:

- **Prefer Dependabot:** set `"vulnerabilityAlerts": {"enabled": false}` in `.github/renovate-default.json` (every repo extending the preset inherits it).
- **Prefer Renovate:** set `dependabot_security_updates_enabled: false` on the affected repos in `otterdog/vig-os/vig-os.jsonnet` and amend the ADR-0008 decision. `qx` has no Renovate and `scitadel` has no Renovate Cargo coverage, so both would keep Dependabot.

## Related Issues

Refs #294, #304.

## Priority

Low

## Changelog Category

No changelog needed

---

# [Comment #1]() by [c-vigo]()

_Posted on September 29, 2026 at 01:08 PM_

Resolved early, 2026-09-29: took the 'Prefer Renovate' option instead of watching until 10-29. #310 merged and applied (run 36572077080). Dependabot security updates are now off on the 8 devkit-managed repos (qx keeps them as an ADR-0008 exception). The org default for new repos was set to false through the API, which matches unmanaged-controls.toml. Renovate coverage landed first: h5v#13, tessera#512, scitadel#241/#243, qx#313, devkit#1764. Obsolete Dependabot PRs are closed.

