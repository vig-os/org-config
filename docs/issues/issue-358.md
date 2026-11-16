---
type: issue
state: open
created: 2026-11-15T10:54:22Z
updated: 2026-11-15T10:54:22Z
author: vig-os-org-config[bot]
author_url: https://github.com/vig-os-org-config[bot]
url: https://github.com/vig-os/org-config/issues/358
comments: 0
labels: drift, critical
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-11-16T09:08:26.286Z
---

# [Issue 358]: [Drift: repository[name="tessera"]](https://github.com/vig-os/org-config/issues/358)

<!-- drift-fingerprint: 8ccca8a1149ecfa2 -->
## Drift detected: `repository[name="tessera"]`

- **Organization:** `vig-os`
- **Change type:** `change`
- **Last observed:** 2026-11-15 10:54 UTC

The live GitHub state diverges from the committed Otterdog config. This is **issue-only** (ADR-0002): nothing is auto-reverted — a human decides whether to revert the change or adopt it into config, then closes this issue (it also closes automatically once the divergence is resolved).

<details><summary>Plan diff</summary>

```text
  ~ repository[name="tessera"] {
    ~ description = "Self-describing, sealed FAIR container (.tsra): Vortex tables + Zarr v3 arrays, with provenance and versioning." -> "FAIR Data on HDF5 — self-describing, FAIR-principled data format 
for scientific data products"
  ~ }
```

</details>
