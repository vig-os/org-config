---
type: issue
state: closed
created: 2026-09-23T12:43:35Z
updated: 2026-09-23T12:58:37Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/237
comments: 0
labels: docs, priority:low, area:docs, effort:small, semver:patch
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-23T21:09:31.109Z
---

# [Issue 237]: [ADR-0007 still describes the pre-#63 `dev` trunk; apply has run from `main` since the trunk migration](https://github.com/vig-os/org-config/issues/237)

## Summary

#63 migrated the repo to a trunk model: PRs target \`main\`, the single
applied-state branch (\`plan.yml\`'s trigger comment and
\`apply-engine.yml\`'s header both say so, citing #63). ADR-0007 was never
reconciled and still describes the old \`dev\`/\`main\` split in four places:

- Line 56 (Axis B table): "Config from \`dev\`; engine to tags"
- Line 80: "\`apply\` is **environment-gated** (required reviewer) and runs only from trunk (\`dev\`)."
- Line 83: "config **applies from \`dev\` on merge**; the engine **releases to \`main\` + version tags**"
- Line 116: "a breaking workflow change is a tagged release, not a silent \`dev\` merge."

All four are false as written: applied state is \`main\`, and the engine
releases via version tags cut by the release train, not by promotion to a
separate \`main\` branch.

## Why it matters

Line 80 is a **binding credential rule** in the ADR's Decision section — a
reader auditing where the write token can run is told the wrong branch. The
others misdescribe the split-cadence decision that is the ADR's own Axis B
verdict.

## Proposed fix

Documentation only. Correct the four references to the post-#63 topology and
record the reconciliation as a dated entry in ADR-0007's \`## Corrections\`
block, matching how #225 handled ADR-0005 and #235 handles this ADR's L2
claim.

## Acceptance

- [ ] ADR-0007 nowhere claims apply runs from \`dev\` or that the engine releases to \`main\`
- [ ] Recorded as a dated \`## Corrections\` entry, not a silent rewrite

## Context

Found while evaluating #236 (which amends ADR-0007's L2 bullet) and split out
per the single-issue scope rule. Related: #63, #235.
