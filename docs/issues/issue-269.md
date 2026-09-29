---
type: issue
state: open
created: 2026-09-25T20:26:44Z
updated: 2026-09-25T21:41:54Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/269
comments: 1
labels: bug, priority:low, area:workflow, effort:small
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-26T07:11:51.319Z
---

# [Issue 269]: [otterdog `get_app_installations` is unpaginated and sends no `per_page` — an org with more than 30 App installations gets a truncated id→slug map, dropping more actors than #262/#732 predict](https://github.com/vig-os/org-config/issues/269)

## What's wrong

The id→slug map that #262 is about is not only *partial by design* (org installations only) — it is
also **truncated at 30 entries**, because the call that builds it is unpaginated and sends no
`per_page`.

otterdog 1.5.0 (the ADR-0005 pin), `providers/github/rest/org_client.py:484-491` — verified against
the published wheel (`otterdog-1.5.0-py3-none-any.whl`, sha256 `138b6090…`, downloaded from PyPI and extracted locally):

```python
async def get_app_installations(self, org_id: str) -> list[dict[str, Any]]:
    _logger.debug("retrieving app installations for org '%s'", org_id)

    try:
        response = await self.requester.request_json("GET", f"/orgs/{org_id}/installations")
        return response["installations"]
    except GitHubException as ex:
        raise RuntimeError(f"failed getting app installations for org '{org_id}':\n{ex}") from ex
```

`request_json` (`requester.py:116`) is the single-shot form: it issues one request, sends no
`per_page`, and never looks at the `Link` header. `GET /orgs/{org}/installations` is a paginated
endpoint whose default page size is **30**, and it returns an envelope
(`{"total_count": N, "installations": [...]}`) — so the 31st installation onward is silently
dropped, and `total_count` (which is right there in the body) is never compared against
`len(installations)`.

The sole consumer is the map at `models/github_organization.py:555-558`:

```python
app_installations = {
    str(installation["app_id"]): installation["app_slug"]
    for installation in await provider.rest_api.org.get_app_installations(github_id)
}
```

which is exactly the dict #262 documents being consulted at `github_organization.py:761-765`
(ruleset `bypass_actors`) and `:771-777` (`required_status_checks`).

**The project already has the right primitive.** `requester.request_paged_json` (`requester.py:78`)
defaults to `per_page=100`, follows `rel="next"`, and takes an `entries_key` argument for precisely
this envelope shape — used that way at `action_client.py:28` (`entries_key="workflows"`) and
`:54` (`entries_key="artifacts"`). Same file, `org_client.py`, already calls it for repos (`:307`),
members (`:714`), security advisories (`:723`) and rulesets (`:732`). The installations call is the
odd one out. The upstream fix is one line:

```python
return await self.requester.request_paged_json(
    "GET", f"/orgs/{org_id}/installations", entries_key="installations"
)
```

## Why it matters

Not today, and that is why this is a tracker rather than a change. Measured 2026-09-25:

| org | `total_count` |
| --- | --- |
| `vig-os` | 8 |
| `exo-pet` | 12 |

Both are under 30, so the map is complete in both orgs and neither #262's symptom nor this one is
live. But the failure is worth recording because of its **shape**:

- It is **strictly worse than #262 and upstream eclipse-csi/otterdog#732 predict.** Both of those
  reason about an App that is *not an org installation*. This drops Apps that **are** org
  installations — they simply landed on page 2. So the set of dropped bypass actors is larger than
  the upstream issues describe, and a reader who has mitigated #262 by "make sure the App is an org
  installation" is not covered.
- It is **silent and order-dependent.** The drop produces the #262 symptoms exactly (a bypass actor
  vanishes from the model; a status check renders numeric) with no log line naming pagination, and
  which Apps survive depends on GitHub's page ordering — so the same config can plan differently on
  two runs if an installation is added or removed.
- It **degrades as an org grows**, without any config change. `exo-pet` is at 12 of 30 and its
  installation list is the one that keeps growing (12 today, several org-specific Apps added this
  year). Crossing 30 changes plan behaviour with nothing in this repo touched.

## Suggested fix

Nothing is fixable from here — this is upstream code reached through the pinned binary. The useful
actions are:

1. **Record it** as a known limitation beside the #262 material (README known-limitations bullet
   and/or the `bypass_actors+` declarations), with the 30-entry number and the `total_count` check
   an operator can run by hand: `gh api /orgs/<org>/installations --jq .total_count`.
2. **Post the drafted upstream comment below** on eclipse-csi/otterdog#732 — the same function, the
   same map, and the same one-patch fix as #732 and #772; a third upstream issue would fragment it.
   (Left for a human to post: this repo's spikes are read-only on GitHub.)
3. **Add the count to the pin-bump checklist** (ADR-0005): at the next otterdog bump, re-read
   `get_app_installations` and re-measure both orgs' `total_count`. If either org approaches 30
   before upstream fixes it, the plan-time App check from #259 is the place to surface it — it
   already reads `GET /orgs/{org}/installations` for the class-2 (`UNREADABLE`) check and can
   compare `total_count` against the number of entries it received, which is a two-line assertion
   in code this repo owns.

## Drafted upstream comment (not posted)

<details>
<summary>Comment text for eclipse-csi/otterdog#732 — to be posted by a maintainer of this repo</summary>

> The installation map this issue is about is also **truncated at 30 entries**, which makes the
> dropped set larger than "apps that are not org installations".
>
> `providers/github/rest/org_client.py:484-491` (1.5.0, unchanged on `main` as of 2026-09-25):
>
> ```python
> response = await self.requester.request_json("GET", f"/orgs/{org_id}/installations")
> return response["installations"]
> ```
>
> `request_json` is single-shot: no `per_page`, no `Link` following. `GET /orgs/{org}/installations`
> paginates at a default page size of 30 and returns `{"total_count": N, "installations": [...]}`,
> so for an org with more than 30 installed Apps the map built at
> `models/github_organization.py:555-558` silently omits everything past page 1 — and `total_count`,
> which is in the response body, is never compared with `len(installations)`.
>
> Downstream that map is consulted for ruleset `bypass_actors`
> (`models/github_organization.py:761-765`) and `required_status_checks` (`:771-777`), so the
> symptoms are exactly the ones already reported — a status check rendering numeric, a bypass actor
> dropped outright at `models/ruleset.py:541-548` — but they now also hit Apps that **are** proper
> org installations, purely by page position. Which Apps survive depends on the order GitHub returns
> them in, so the same committed config can plan differently between two runs after an unrelated App
> is installed or removed.
>
> The codebase already has the primitive: `requester.request_paged_json` (`requester.py:78`) sends
> `per_page=100`, follows `rel="next"`, and accepts `entries_key` for exactly this envelope shape
> (`action_client.py:28` uses `entries_key="workflows"`; the same `org_client.py` uses the paged form
> for repos `:307`, members `:714`, advisories `:723` and rulesets `:732`). So:
>
> ```python
> return await self.requester.request_paged_json(
>     "GET", f"/orgs/{org_id}/installations", entries_key="installations"
> )
> ```
>
> Worth folding into whatever patch closes this issue, since it is the same map and the same file —
> and worth doing even if the lazy `GET /apps/{slug}` extension suggested here lands, because that
> extension only covers slugs present in the committed config.

</details>

## Acceptance

- [ ] The 30-entry truncation is documented alongside the #262 limitation, with how to measure
      (`gh api /orgs/<org>/installations --jq .total_count`)
- [ ] The comment above is posted on eclipse-csi/otterdog#732, or an upstream fix is confirmed to
      cover it
- [ ] Both orgs' installation counts are re-measured at the next ADR-0005 otterdog pin bump

## Context

Found while verifying #262's read-path citation against the published otterdog 1.5.0 wheel. Related:
#262 (the read-path drop this compounds), #256 / upstream eclipse-csi/otterdog#772 (the write side),
upstream eclipse-csi/otterdog#732 (the status-check variant of the same map), #259 (the plan-time
check that already reads the installations endpoint and could assert the count), ADR-0005 (the
otterdog pin).

---

# [Comment #1]() by [c-vigo]()

_Posted on September 25, 2026 at 09:41 PM_

## The code leg (suggested fix item 3) was considered and is dropped — docs only

Item 3 offers the plan-time App check (#259) as the place to surface this, "a two-line assertion in
code this repo owns". It was specced, reviewed adversarially, and dropped. Recording why, so it is
not re-proposed without new evidence.

**The issue itself conditions it, and the condition is not met.** Item 3 reads *"**If** either org
approaches 30 before upstream fixes it…"*. Re-measured today, `gh api /orgs/<org>/installations
--jq .total_count`: `vig-os` **8**, `exo-pet` **12**. Same numbers as when this was filed. Nothing
is near the threshold.

**When it fired, it would be unactionable.** At 31 installations the warning appears on *every* PR
of that org, and the only remedy it can name is "bump otterdog past a fix that does not exist yet"
— eclipse-csi/otterdog#732 is open and `org_client.get_app_installations` is still the single-shot
form on upstream `main`, past 1.6.0 and 1.6.1. A permanent warning with no action is noise on a
context that is a required check downstream (#268).

**And it would be unsuppressable.** `drift-allowlist.toml`'s `[[app_actor]]` section is keyed by
**slug** (`allowlist: Mapping[str, str]`, slug → reason), so it cannot suppress an org-level count
finding. `unmanaged-controls.toml` is not an alternative home either: `_evaluate_control` compares
`expect` by equality or set membership, there is no threshold operator, and an exact
`expect = 12` on `total_count` would open a drift issue every time an App is legitimately installed.

It also does not fit the shapes it would live in. `Installations` is `(slugs, complete, detail)`,
and at 31 entries *this repo's own* read is complete (`per_page=100` plus a refusal on `rel="next"`),
so `complete` stays `True`; `AppSlugReport.notes` is documented as "reads that could not be
completed, or not attempted", which this is not. Surfacing it properly means a new field, plumbing
through `check_app_slugs`, a renderer branch, a new key in `app-actors.json` (whose shape is
asserted by the test suite) and README text — not `effort:small` on a `priority:low` issue.

## What ships instead

The docs leg, unchanged from the spike, plus the guard the issue already asks for:

- the README known-limitations bullet keeps the **explicit 31–100 silent band** — otterdog sends no
  `per_page` and GitHub's default page size for this endpoint is 30, so 31 through 100 is the range
  where otterdog truncates and *this repo's* check does not (it refuses only a genuinely truncated
  read, i.e. 101+), with the operator measurement spelled out;
- the ADR-0005 pin-bump checklist entry is the guard: at the next otterdog bump, re-read
  `get_app_installations` and re-measure both orgs' `total_count`. That is a human step at the one
  moment the answer can change, rather than a check firing on every PR forever.

If either org does approach 30 while upstream is still unfixed, the warning becomes worth filing on
its own terms — and then it needs an `OTTERDOG_VERSION` gate (already in scope in the step's shell)
plus a test asserting **silence** past the threshold, so CI retires it rather than somebody's memory.

## Upstream (acceptance item 2) — prepared, not posted

The #732 comment and a patch PR against `eclipse-csi/otterdog` are both drafted and verified against
upstream `main`: `request_paged_json(..., entries_key="installations")`, return type and
`GitHubException → RuntimeError` wrapping preserved, with a unit test. They are **for Carlos to
post** — this repo's agents are read-only on GitHub outside this org, and the PR additionally needs
the Eclipse Contributor Agreement signed with the sign-off address before `eclipsefdn/eca` will pass.

This issue therefore stays **open** after the docs PR merges: acceptance item 2 is the human post.


