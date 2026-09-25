---
type: issue
state: open
created: 2026-09-24T14:42:23Z
updated: 2026-09-24T14:42:23Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/256
comments: 0
labels: none
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-25T07:16:18.709Z
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

