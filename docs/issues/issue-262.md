---
type: issue
state: closed
created: 2026-09-25T17:08:07Z
updated: 2026-09-25T20:35:02Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/262
comments: 1
labels: bug, priority:low, area:workflow, effort:small, semver:patch
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-26T07:11:52.514Z
---

# [Issue 262]: [An App bypass actor that is not an org installation is silently dropped on otterdog's read path — permanent phantom plan diff](https://github.com/vig-os/org-config/issues/262)

## What's wrong

Otterdog's **read** path maps a ruleset's `Integration` bypass actors from numeric
`actor_id` back to a slug using the organization's installed Apps, and drops any actor it
cannot map.

`models/github_organization.py:761-765` (otterdog 1.5.0, the ADR-0005 pin) — note the
project's own `FIXME` two lines above it:

```python
# FIXME: need to associate an app id to its slug
#        GitHub does not support that atm, so we lookup the currently installed
#        apps for an organization which provide a mapping from id to slug.
for actor in github_ruleset.get("bypass_actors", []):
    if actor.get("actor_type", None) == "Integration":
        actor_id = str(actor.get("actor_id", 0))
        if actor_id in app_installations:          # only org installations
            actor["app_slug"] = app_installations[actor_id]
```

`app_installations` is built from `GET /orgs/{org}/installations`. An App that holds a
bypass slot on a live ruleset but is **not installed on that org** therefore gets no
`app_slug`, and `models/ruleset.py:541-547` then discards it from the model entirely:

```python
elif actor_type == "Integration":
    app_slug = actor.get("app_slug")
    if app_slug is None:
        _logger.warning("fail to map integration actor '%s', skipping", actor.get("actor_id", "unknown"))
        continue
```

The warning goes to the otterdog log, not to the plan output.

## Why it matters

The actor exists live and is invisible to the model, so:

- **`plan` shows a permanent phantom diff.** If the config declares the actor, every plan
  proposes to add it back; if the config does not, the live bypass slot is never reported
  at all — a standing, unreported bypass of a protected branch or tag.
- **`apply` cannot converge.** Writing the ruleset re-sends the whole bypass list
  (`models/repo_ruleset.py:63-71` passes `expected_object.to_provider_data(...)` on
  `LivePatchType.CHANGE`), so the actor is rewritten each time and read back as absent
  each time. The diff never closes, and a never-closing diff is exactly the kind of
  standing noise that trains a reviewer to wave plans through.
- **The drift leg inherits it.** `drift.yml` reconciles the same plan text, so the phantom
  becomes a recurring drift record rather than a one-off.

This is the read-side sibling of #256 (which is the *write* side of the same field) and the
same family as upstream **eclipse-csi/otterdog#732**, the read-side variant for status
checks bound to non-installed apps — and the same class as the old #130-#141 batch.

## Not biting here, filed before it does

`vig-os` is unaffected: both Apps it names as bypass actors — `commit-action-bot` and
`vig-os-release-app`, ten actors across ten rulesets in `otterdog/vig-os/vig-os.jsonnet` —
are org installations, so both map. `exo-pet` likewise resolves `exopet-doc-issuer`
(`/apps/exopet-doc-issuer` -> id `5059344`, listed as installation `164391965` on
`exo-pet`).

The case that trips it is ordinary and undetectable from the config alone: a bypass slot
granted out of band to an App that is installed on *some* repositories of the org without
being an org installation, or one whose installation is later removed while the ruleset
keeps the `actor_id`.

## Suggested fix

Nothing can be fixed in otterdog from here; the useful move is detection, and it is one
extra GET on a check this repo is already going to build. The plan-time App check spun off
from #256 reads `GET /apps/{slug}` for every declared App actor; reading
`GET /orgs/{org}/installations` alongside it lets the same step report a second class:

- `UNWRITABLE` — declared, but `GET /apps/{slug}` is not 200 under the engine's token
  (#256): `apply` will fail.
- `UNREADABLE` — declared and resolvable, but the slug is absent from the org's
  installations: `plan` will show a phantom diff forever.

Failing that, a one-line note beside the `bypass_actors+` declarations saying an App bypass
actor must be an org installation to survive the read path.

Upstream: worth attaching to eclipse-csi/otterdog#732 rather than filing a third issue —
same mechanism, different field.

## Acceptance

- [ ] An App bypass actor that is not an org installation is reported at review time rather
      than silently dropped, or
- [ ] The limitation is documented where bypass actors are declared, with the upstream
      reference
- [ ] The behaviour is re-checked at the next ADR-0005 otterdog pin bump

## Context

Related: #256 (the write side of the same field), upstream eclipse-csi/otterdog#732 and
#772, #69 / #130-#141 (the earlier App-id resolution batch).

---

# [Comment #1]() by [c-vigo]()

_Posted on September 25, 2026 at 08:29 PM_

## Detection is delivered by #259, one half of it

The "Suggested fix" above proposes folding the detection into the plan-time App check spun off from
#256. That is what is happening, as **#259's own scope** — one extra `GET /orgs/{org}/installations`
alongside the `GET /apps/{slug}` reads it already performs — so the two classes this issue names are
distinguished in the plan report:

- `UNWRITABLE` — declared, but `GET /apps/{slug}` is not 200 under the engine's installation token
  (#256): `apply` will fail on it.
- `UNREADABLE` — declared and resolvable, but the slug is absent from the org's installations
  (this issue): `plan` will show a phantom diff forever.

**Gated to the two ruleset sites.** The installation-membership half only applies where the read
path consults the id→slug map — repository ruleset `bypass_actors`
(`models/github_organization.py:761-765`) and `required_status_checks` (`:771-777`). The other
declared-App sites #259 covers (branch-protection-rule checks, environment reviewers) are not
subject to it, so the check does not emit the class-2 finding for them. On the two real configs it
is clean today: `vig-os`'s three declared slugs all resolve and all whose read path needs it are org
installations; `exo-pet`'s two likewise.

## What is NOT covered — the half this issue also describes

Only the **declared** direction is detected. A bypass actor that exists live but is **not** declared
in the committed config is still invisible: the model drops it at `models/ruleset.py:541-547`, so
there is nothing for a config-driven check to compare against. That is the worse half of this issue
("a standing, unreported bypass of a protected branch or tag"), and detecting it would need a
separate read of the live ruleset via `GET /repos/{owner}/{repo}/rulesets/{id}` outside otterdog's
model — not in #259, not scheduled. Worth keeping on this issue after #259 merges.

Two adjacent blind spots belong with it: `GET /orgs/{org}/rulesets` returns 403 on a Free-plan org,
so org-level rulesets cannot be read back at all here; and the id→slug map is additionally truncated
at 30 entries because the call that builds it is unpaginated — filed as #269, which makes the
dropped set larger than this issue and upstream #732 describe.

## Docs PR

The docs-only leg of this issue (README known-limitations bullet + CHANGELOG) is prepared and lands
as its own PR, with the private App's slug and numeric id removed — this is a public repo, so it
reads "an App owned by a sibling org", matching how #256's merged CHANGELOG already words it. The
sentence "neither reaches the pull request" is true at that commit and is amended by #259's PR when
the declared half starts being reported.

## Upstream — draft comment for eclipse-csi/otterdog#732, to be posted by hand

Recommend attaching to #732 rather than filing a third upstream issue: same function, same map, one
patch closes both. Worth adding a line to #772 (the write-side bypass-actor issue from #256)
cross-linking the two, so a future fixer sees that one `bypass_actors` patch closes all of them.

<details>
<summary>Comment text</summary>

> The same installation map breaks a second field, ten lines away, and worse.
>
> `models/github_organization.py` applies `app_installations` to a repo ruleset's `bypass_actors`
> (1.5.0: `:758-765`) immediately before it applies it to `required_status_checks` (`:771-777`). But
> the two readers behave differently when the map misses:
>
> - **Status checks degrade.** `transform_status_check` (`models/ruleset.py:145-151`) falls back to
>   `str(integration_id) + ":" + context`, so the check stays visible and — since #700 — writable.
>   That is this issue: a wrong-*form* diff.
> - **Bypass actors vanish.** `models/ruleset.py:541-548` has no fallback: with no `app_slug` it logs
>   `fail to map integration actor '<id>', skipping` and `continue`s, dropping the actor from the
>   model entirely. There is no numeric form on the write side either (no `isdigit()` branch at
>   `models/ruleset.py:649`, unlike `:208-209`), so there is no workaround at all.
>
> Consequences, both silent on the plan because the warning goes to the log and not to `plan.txt`:
>
> - if the config declares the actor, every `plan` proposes to add it back, and `apply` cannot
>   converge — `models/repo_ruleset.py:63-71` re-sends the whole bypass list on
>   `LivePatchType.CHANGE`, so the actor is written and read back as absent on every cycle;
> - if the config does not declare it, a live bypass of a protected branch or tag is never reported
>   at all, which for a drift-detection setup is a standing hole rather than noise.
>
> The reproduction is an App with a bypass slot on a ruleset that is installed on individual
> repositories of the org without being an org-level installation, or an installation removed while
> the ruleset keeps the `actor_id`.
>
> This issue's suggested fix — lazily extend `app_installations` with `GET /apps/{slug}` for slugs
> present in the committed config — closes it too, as long as it is applied to the `bypass_actors`
> loop and not only to `required_status_checks`. The `bypass_actors` case may also want the #700
> treatment (accept and pass through a numeric `actor_id`), since that is the only direction that
> works without any slug lookup at all.
>
> Both paths are unchanged on `main` as of 2026-09-25 (`models/ruleset.py:545-552`).

</details>


