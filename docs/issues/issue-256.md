---
type: issue
state: closed
created: 2026-09-24T14:42:23Z
updated: 2026-09-25T17:26:28Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/256
comments: 1
labels: docs, priority:medium, area:docs, effort:small, semver:patch
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-26T07:11:55.422Z
---

# [Issue 256]: [`plan` passes and `apply` fails when a ruleset names a GitHub App bypass actor — the engine's installation token cannot resolve the slug](https://github.com/vig-os/org-config/issues/256)


## What happened

A downstream consumer declared a tag ruleset whose single bypass actor is a
GitHub App, so that only that App may create tags in a protected namespace. The
`plan` check on the pull request passed and rendered the change correctly. The
change was merged and `apply` was dispatched from `main` — and failed:

```
Error:   failed to apply patch: CHANGE - repo_ruleset[name="<name>", repository=<repo>]
         failed retrieving app node id:
         Exception while accessing 'https://api.github.com/apps/<app-slug>':
         (status=403, {"message":"Resource not accessible by integration"})
```

The patch is refused atomically — the live ruleset was untouched, verified by
its unchanged `updated_at` — so the failure is safe. But the organization is
then left with committed config that cannot be applied, and the only record of
its state is a failed run.

## Why this is the engine's problem too, not only otterdog's

otterdog resolves an App bypass actor on the **write** path through
`GET /apps/{app_slug}`, an endpoint installation access tokens may not call.
This workflow mints an installation token with `create-github-app-token` and
passes it as `OTTERDOG_TOKEN`, so every apply here authenticates as an
installation. otterdog's CLI provider always uses token auth
(`token_auth(credentials.github_token)`); its JWT `app_auth` strategy is not on
that path, so the engine cannot avoid this by supplying App credentials
instead. Reported upstream as eclipse-csi/otterdog#772, where it is the same
class of defect as eclipse-csi/otterdog#695 — fixed there for required status
checks by accepting a numeric app id, never extended to bypass actors.

The part that belongs here is the **gate**: `plan` is this repository's L2
review gate, and for this class of change it is green on something that cannot
be applied. The read path needs no slug resolution, so `plan` cannot see the
problem — which means a reviewer's evidence is, in this one case, not evidence.

## What would help

1. **Document the limitation** where the ruleset fields are described: an App
   bypass actor cannot currently be created by `apply`, and must be created out
   of band through the REST API, which takes `actor_id` directly and needs no
   slug resolution. Once live, otterdog reads it back as a slug, matches the
   declaration and plans clean — so the declaration still detects drift.
2. **Surface it at plan time.** A pre-apply check that flags a bypass actor
   the engine's credential cannot resolve would move the failure from a live
   mutating run to the pull request, which is where this repository's model
   says failures belong.
3. **Record the residual gap** wherever ruleset ownership is described: for a
   ruleset carrying an App bypass actor, otterdog still *detects* drift but can
   no longer *repair* it, because any patch rewrites the whole bypass list and
   hits the same 403. Detection stays mechanism; repair becomes manual until
   eclipse-csi/otterdog#772 is fixed.

## Reproduction

Any organization on this engine, with any repository ruleset whose
`bypass_actors` names a GitHub App that is not already live in that list.
Removing an App bypass actor works, since only the actors being written are
resolved; adding the first one is the failing direction.

---

# [Comment #1]() by [c-vigo]()

_Posted on September 25, 2026 at 05:09 PM_

Spike + review outcome. Three corrections to this issue, and a split.

**1. The predicate proposed in item (2) is falsified by this org's own config.** The natural
reading — "warn when a bypass actor is an App **and** is not already live" — is wrong in both
directions:

- `otterdog/vig-os/vig-os.jsonnet` already declares **ten** App bypass actors across ten
  rulesets (`commit-action-bot` x7, `vig-os-release-app` x3), and they apply cleanly. That
  predicate would have fired on all ten the day they were introduced — 100% false positives
  on this org's own data, which is how a check gets ignored.
- It also misses the case this issue is about. A ruleset patch re-sends the **whole** bypass
  list (`models/repo_ruleset.py:63-71` passes `expected_object.to_provider_data(...)` on
  `LivePatchType.CHANGE`; `models/ruleset.py:635-652` re-resolves every actor in it), so an
  App that is *already live* but unreadable 403s on the next change to that ruleset too —
  the residual gap item (3) describes.

The real discriminator is **whether the engine's installation token can read
`GET /apps/{slug}` at all**, not whether the actor is live. Probed 2026-09-25,
unauthenticated: `commit-action-bot` 200, `vig-os-release-app` 200, `vig-os-org-config` 200,
`exopet-doc-issuer` **404** (200 to an org-owner PAT; 403 to an installation token, per the
traceback above). Stated as an observation, not as mechanism — GitHub's
`GET /apps/{app_slug}` reference documents no authentication requirement at all.

**2. "Both Apps have always applied" is six observations and one inference, not ten.** Of the
ten rulesets the 2026-08-08 installation-token apply rewrote (the #246 incident set), **six**
carry an App bypass actor — Dev + Release protection on `commit-action`, `devkit` and
`sync-issues-action` — and all six name `commit-action-bot`. The three Tag rulesets that carry
`vig-os-release-app` were not in that set: `vig-os/commit-action` Tag protection (18922488) is
still at `updated_at 2026-07-16T19:33:59.944+02:00`, i.e. before the engine App even existed
(`/apps/vig-os-org-config` `created_at 2026-07-17T10:00:24Z`). So `vig-os-release-app` has
never been resolved by an installation token — it is *expected* to work because it is public,
not observed to. Worth getting right in the CHANGELOG, which is this repo's standing forensic
record.

**3. No downstream action is owed.** The remediation is already done and predates this issue.
`exo-pet/vault` ruleset 23866115 ("Issued document tags") carries
`bypass_actors: [{actor_id: 5059344, actor_type: "Integration", bypass_mode: "always"}]` —
`/apps/exopet-doc-issuer` -> id 5059344 — written at `updated_at 2026-09-24T14:22:37.509+02:00`
(12:22Z), i.e. 2h20m *before* this issue was filed (14:42:23Z) and 45 min after the failing
apply (run 35994005556, 11:36:31Z). Four green `Apply` runs since: 36000190598, 36120273830,
36135497279, 36140481417. The one failure in between, 36119473230, is #257's teams 403, not
this. So no exo-pet issue, and the remaining exposure there is the **repair** gap — the next
change to that ruleset re-resolves the slug and 403s again — which is exactly item (3).

**Split.** Item (2) (surface it at plan time) is now **#259**: a warn-only step in `plan.yml`
between *Run otterdog plan* and *Build plan report*, scoped to all four write-path
`get_app_ids` call sites rather than just bypass actors — ruleset `bypass_actors`
(`models/ruleset.py:649`), ruleset `required_status_checks` with a non-numeric prefix
(`:177-189`, escaped today only because every prefix here is numeric `15368:`),
branch-protection-rule checks (`models/branch_protection_rule.py:348`), and environment
reviewers (`models/environment.py:244`), where an unreadable App is **silently skipped**
rather than refused (`providers/github/__init__.py:502-506`). It warns rather than fails, per
the ADR-0007 Axis D decision on #236. Also spun off: **#262**, the read-side sibling — an App
bypass actor that is not an org installation is dropped from the model entirely
(`models/github_organization.py:761-765` + `models/ruleset.py:541-547`), a permanent phantom
plan diff in the same family as upstream eclipse-csi/otterdog#732.

**This issue is therefore narrowed to items (1) + (3)** — document the limitation where the
ruleset fields are described, and record the residual gap wherever ruleset ownership is
described. Docs-only PR to follow; relabelled `docs` / `area:docs` / `priority:medium` /
`effort:small` / `semver:patch` to match. Upstream eclipse-csi/otterdog#772 remains open with
no PR, so the exit criterion stays "an ADR-0005 pin carrying the upstream fix".


