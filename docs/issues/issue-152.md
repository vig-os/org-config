---
type: issue
state: open
created: 2026-08-11T11:29:21Z
updated: 2026-08-27T17:14:01Z
author: renovate[bot]
author_url: https://github.com/renovate[bot]
url: https://github.com/vig-os/org-config/issues/152
comments: 0
labels: none
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-28T13:56:13.075Z
---

# [Issue 152]: [Dependency Dashboard](https://github.com/vig-os/org-config/issues/152)

This issue lists Renovate updates and detected dependencies. Read the [Dependency Dashboard](https://docs.renovatebot.com/key-concepts/dashboard/) docs to learn more.<br>[View this repository on the Mend.io Web Portal](https://developer.mend.io/github/vig-os/org-config).

## Awaiting Schedule

The following updates are awaiting their schedule. To get an update now, click on a checkbox below.

 - [ ] <!-- unschedule-branch=renovate/python-(minor-and-patch) -->build(pip): update dependency ruff to v0.16.5
 - [ ] <!-- unschedule-branch=renovate/lock-file-maintenance -->build(pip): lock file maintenance
 - [ ] <!-- create-all-awaiting-schedule-prs -->🔐 **Create all awaiting schedule PRs at once** 🔐

## Detected Dependencies

<details><summary>github-actions (24)</summary>
<blockquote>

<details><summary>.github/actions/setup-devkit-toolchain/action.yml</summary>


</details>

<details><summary>.github/workflows/abandon-release.yml</summary>


</details>

<details><summary>.github/workflows/apply-reminder.yml (1)</summary>

 - `ubuntu 24.04`

</details>

<details><summary>.github/workflows/apply.yml (5)</summary>

 - `actions/checkout v7.0.1@3d3c42e5aac5ba805825da76410c181273ba90b1`
 - `astral-sh/setup-uv v10.0.1@20cfd1bf945f4377ade1205e4dbc17946fc9a30d`
 - `actions/create-github-app-token v3@bcd2ba49218906704ab6c1aa796996da409d3eb1`
 - `actions/create-github-app-token v3@bcd2ba49218906704ab6c1aa796996da409d3eb1`
 - `ubuntu 24.04`

</details>

<details><summary>.github/workflows/ci.yml</summary>


</details>

<details><summary>.github/workflows/codeql.yml</summary>


</details>

<details><summary>.github/workflows/devkit-upgrade.yml</summary>


</details>

<details><summary>.github/workflows/drift.yml (6)</summary>

 - `actions/checkout v7.0.1@3d3c42e5aac5ba805825da76410c181273ba90b1`
 - `astral-sh/setup-uv v10.0.1@20cfd1bf945f4377ade1205e4dbc17946fc9a30d`
 - `actions/create-github-app-token v3@bcd2ba49218906704ab6c1aa796996da409d3eb1`
 - `actions/checkout v7.0.1@3d3c42e5aac5ba805825da76410c181273ba90b1`
 - `actions/create-github-app-token v3@bcd2ba49218906704ab6c1aa796996da409d3eb1`
 - `ubuntu 24.04`

</details>

<details><summary>.github/workflows/plan.yml (4)</summary>

 - `actions/checkout v7.0.1@3d3c42e5aac5ba805825da76410c181273ba90b1`
 - `astral-sh/setup-uv v10.0.1@20cfd1bf945f4377ade1205e4dbc17946fc9a30d`
 - `actions/create-github-app-token v3@bcd2ba49218906704ab6c1aa796996da409d3eb1`
 - `ubuntu 24.04`

</details>

<details><summary>.github/workflows/prepare-release-extension.yml (1)</summary>

 - `ubuntu 24.04`

</details>

<details><summary>.github/workflows/prepare-release.yml</summary>


</details>

<details><summary>.github/workflows/promote-release.yml</summary>


</details>

<details><summary>.github/workflows/release-core.yml</summary>


</details>

<details><summary>.github/workflows/release-extension.yml (1)</summary>

 - `ubuntu 24.04`

</details>

<details><summary>.github/workflows/release-publish.yml</summary>


</details>

<details><summary>.github/workflows/release.yml</summary>


</details>

<details><summary>.github/workflows/scorecard.yml</summary>


</details>

<details><summary>.github/workflows/sync-issues.yml</summary>


</details>

<details><summary>.github/workflows/testbed-e2e.yml (5)</summary>

 - `actions/checkout v7.0.1@3d3c42e5aac5ba805825da76410c181273ba90b1`
 - `astral-sh/setup-uv v10.0.1@20cfd1bf945f4377ade1205e4dbc17946fc9a30d`
 - `actions/create-github-app-token v3@bcd2ba49218906704ab6c1aa796996da409d3eb1`
 - `actions/create-github-app-token v3@bcd2ba49218906704ab6c1aa796996da409d3eb1`
 - `ubuntu 24.04`

</details>

<details><summary>template/.github/workflows/apply-reminder.yml (1)</summary>

 - `vig-os/org-config vX.Y.Z`

</details>

<details><summary>template/.github/workflows/apply.yml (1)</summary>

 - `vig-os/org-config vX.Y.Z`

</details>

<details><summary>template/.github/workflows/drift.yml (1)</summary>

 - `vig-os/org-config vX.Y.Z`

</details>

<details><summary>template/.github/workflows/import.yml (5)</summary>

 - `actions/checkout v7.0.1@3d3c42e5aac5ba805825da76410c181273ba90b1`
 - `astral-sh/setup-uv v10.0.1@20cfd1bf945f4377ade1205e4dbc17946fc9a30d`
 - `actions/create-github-app-token v3@bcd2ba49218906704ab6c1aa796996da409d3eb1`
 - `actions/upload-artifact v7.0.1@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a`
 - `ubuntu 24.04`

</details>

<details><summary>template/.github/workflows/plan.yml (1)</summary>

 - `vig-os/org-config vX.Y.Z`

</details>

</blockquote>
</details>

<details><summary>pep621 (1)</summary>
<blockquote>

<details><summary>pyproject.toml (3)</summary>

 - `pytest ==9.1.1`
 - `pytest-cov ==7.1.0`
 - `ruff ==0.16.4` → [Updates: `==0.16.5`]

</details>

</blockquote>
</details>

---

- [ ] <!-- manual job -->Check this box to trigger a request for Renovate to run again on this repository


