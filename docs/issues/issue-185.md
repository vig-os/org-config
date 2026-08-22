---
type: issue
state: closed
created: 2026-08-19T03:59:12Z
updated: 2026-08-22T03:56:50Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/185
comments: 3
labels: drift, critical
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-08-22T09:25:35.158Z
---

# [Issue 185]: [Drift: repository[name="tessera"]](https://github.com/vig-os/org-config/issues/185)

<!-- drift-fingerprint: 8ccca8a1149ecfa2 -->
## Drift detected: `repository[name="tessera"]`

- **Organization:** `vig-os`
- **Change type:** `change`
- **Last observed:** 2026-08-21 04:01 UTC

The live GitHub state diverges from the committed Otterdog config. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Plan diff</summary>

```text
  ~ repository[name="tessera"] {
    ~ code_scanning_default_languages = [
      - "actions"
    ~ ]
  ~ }
```

</details>
---

# [Comment #1]() by [vig-os-org-config[bot]]()

_Posted on August 20, 2026 at 03:58 AM_

Drift still present as of 2026-08-20 03:58 UTC. Refreshed the report above.

---

# [Comment #2]() by [vig-os-org-config[bot]]()

_Posted on August 21, 2026 at 04:01 AM_

Drift still present as of 2026-08-21 04:01 UTC. Refreshed the report above.

---

# [Comment #3]() by [vig-os-org-config[bot]]()

_Posted on August 22, 2026 at 03:56 AM_

Drift resolved as of 2026-08-22 03:56 UTC: the divergence no longer appears in the plan (config and live state reconciled). Closing automatically.

