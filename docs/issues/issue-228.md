---
type: issue
state: closed
created: 2026-09-23T09:28:57Z
updated: 2026-09-23T12:56:04Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/228
comments: 0
labels: none
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-23T21:09:33.814Z
---

# [Issue 228]: [Give otterdog_version a non-empty workflow_call default so downstream inherits the pin instead of mirroring it (#56's "Renovate can bump both" does not hold)](https://github.com/vig-os/org-config/issues/228)

## The premise behind the current contract does not hold

**#56** made `otterdog_version` an optional `workflow_call` input and put the
burden on downstream:

> `template/` callers pass `otterdog_version` explicitly (lockstep comment;
> **Renovate can bump both**).

Renovate does not bump both. It bumps the engine SHA pin and never touches the
otterdog literal, so "lockstep" is a hand-mirrored convention that nothing
enforces and nothing reminds anyone about.

The shipped `template/renovate.json` is the proof — one manager, one rule, one
dep:

```json
"enabledManagers": ["github-actions"],
"packageRules": [{
  "matchManagers": ["github-actions"],
  "matchDepNames": ["vig-os/org-config"],
  …
}]
```

The `github-actions` manager extracts `uses:` refs (and container images). A
bare `with:` input string is not a dependency to any enabled manager, has no
datasource, and carries no annotation. On a downstream caller repo, Renovate's
dependency dashboard lists exactly one dep — the engine ref across the caller
workflows — and no otterdog entry.

`template/.github/workflows/plan.yml` therefore ships a claim that is false as
configured, next to a literal nothing maintains:

```yaml
# Keep in lockstep with the engine's justfile.project otterdog pin (#56);
# Renovate can bump this alongside the engine SHA pin above.
otterdog_version: "1.4.0"
```

The failure mode is silent and one-directional: Renovate advances a downstream's
engine ref on schedule while its otterdog pin stays wherever onboarding left it.
Nothing fails, no drift issue opens, and the divergence is visible only to
someone who thinks to diff two files in two repositories. Every org onboarded
from `template/` starts with the same stale literal.

## Proposal

Give the input a non-empty default in `plan.yml`, `apply.yml` and `drift.yml`:

```yaml
otterdog_version:
  type: string
  default: '1.5.0'      # currently: ''
```

and drop the input from the `template/` callers, so a downstream inherits the
engine's pin with the engine ref it already pins.

## Why this does not regress #56

The three workflows declare `schedule` and a bare `workflow_dispatch:` with **no
inputs** — `otterdog_version` exists only under `workflow_call`. A default there
is therefore visible only to callers:

- **Engine's own events** — `inputs.otterdog_version` is empty, the resolve step
  falls through to `justfile.project`, ADR-0005 SSoT unchanged.
- **Downstream callers** — receive the default instead of the current `''`, so
  the `else` branch that #56 was filed about (`no otterdog_version input and no
  justfile.project in the checkout`) becomes unreachable rather than merely
  documented-around. #56's actual bug is more fixed, not less.
- **A downstream that wants a different version** still passes the input; a
  non-empty default does not remove the override.

The resolution order in the step is untouched.

Non-empty `workflow_call` defaults are already the idiom two inputs up
(`org_github_id: default: vig-os`, `config_repo: default: org-config`).

## Cost

One mirrored literal per callable workflow inside this repo, bumped in the same
commit as `justfile.project`. That is a real duplication of the ADR-0005 SSoT and
should be guarded rather than trusted — a one-line CI assertion that each
workflow default equals the justfile pin is enough, and it fails here, in this
repo's own CI, instead of silently in someone else's org.

The trade is **N downstream mirrors that nothing checks → 1 in-repo mirror that
CI checks.**

## Consequence worth stating in the docs

Once inherited, bumping the engine ref silently changes which otterdog a
downstream runs. That is the intent, but it raises the stakes on release notes:
see #225, where moving the pin to 1.5.0 makes previously-unreadable rulesets
visible and can turn a downstream's plan into a set of proposed deletions. A
downstream's required `plan` check on the Renovate PR remains the backstop — the
diff is visible before merge — but the release note is what makes it expected
rather than alarming.

## Alternative considered and rejected

A downstream Renovate `customManagers` regex over the three literals, with
`datasource: pypi`, `depName: otterdog`. It works, and it needs no change here —
but it tracks PyPI rather than this repo, so each downstream would be proposed
new otterdog versions *ahead* of the engine's pin. That inverts ADR-0005 instead
of implementing it, and it would have to be repeated in every consumer.

## Acceptance

- [ ] `otterdog_version` defaults to the current pin in `plan.yml`, `apply.yml`
      and `drift.yml`
- [ ] CI asserts the defaults equal `justfile.project`'s `otterdog_version`
- [ ] `template/` callers no longer pass the input, and the stale
      "Renovate can bump this" comment is removed
- [ ] Onboarding docs state that the otterdog version now rides with the engine
      ref, and that overriding it is still possible via the input
- [ ] Release note tells existing downstreams they can delete their literals

Related: #56 (the contract this revises), #225 (the pin bump that exposed it),
ADR-0005, ADR-0006.

