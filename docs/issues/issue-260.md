---
type: issue
state: closed
created: 2026-09-25T17:07:54Z
updated: 2026-09-25T20:28:33Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/260
comments: 0
labels: bug, priority:medium, area:workflow, effort:small, semver:patch
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-26T07:11:53.512Z
---

# [Issue 260]: [inventory sweep: `list_org_repos` stops on a short page, so a truncated org repo list is swept as if it were complete](https://github.com/vig-os/org-config/issues/260)

## What's wrong

`RestGitHubClient.list_org_repos()` — the org sweep behind the ADR-0002 inventory leg —
walks pages by number and decides it has reached the end from the *size of the batch*,
never from the response's `Link` header:

```python
def list_org_repos(self, org: str) -> list[str]:          # src/drift_layer/github_client.py:122
    names: list[str] = []
    page = 1
    while True:
        path = f"/orgs/{org}/repos?per_page=100&page={page}"      # :132
        batch = self._request("GET", path) or []                  # :133
        names.extend(raw["name"] for raw in batch)                # :134
        if len(batch) < 100:                                      # :135
            break
        page += 1
    return names
```

`_request` (`:75-91`) reads the body inside `with urllib.request.urlopen(req) as resp` and
lets the response — headers included — die with the block, so `rel="next"` is not merely
ignored, it is unavailable. The same `len(batch) < 100` stop is in
`list_open_drift_issues` (`:117`), `list_org_secrets` (`:161`) and
`list_org_secret_repositories` (`:175`).

This is the same header-blind assumption as #258, one layer down — and the consequence is
worse. #258's `get_json` degrades *a row*; a short-but-not-last page here silently shortens
the **input to the whole sweep**.

## Why it matters

`list_org_repos` is called once, at `src/drift_layer/cli.py:164`, and its result is the
`live` side of `sweep_inventory` (`src/drift_layer/inventory.py:163-204`):

```python
live_set = set(live)
undeclared = sorted((live_set - declared) - scoped)   # inventory.py:182
missing    = sorted((declared - live_set) - scoped)   # :183
```

So an undercounted `live` fails in both directions at once:

- **A live repo past the truncation point never produces an `undeclared` record.** That is
  the ADR-0002 shadow-repo detection the sweep exists for — it goes quiet, with a green
  run and no annotation. Silent absence of a finding, which is the failure mode the
  controls doctrine calls worse than no row at all.
- **A declared repo past the truncation point produces a false `absent` record** —
  "Declared repository absent from org: `<name>`" — manufactured drift with a real issue
  opened against it.

Neither degrades. `cli.py:163-175` wraps the sweep in `except Exception` and drops the
inventory leg on a *raised* failure; a truncation raises nothing, so the leg runs to
completion on a partial view.

## Not biting today, and why it is still worth closing

`vig-os` has 14 repositories and `exo-pet` 8 — both far inside one 100-item page — and
`GET /orgs/vig-os/repos?per_page=100` returns no `Link` header at all, so nothing is
truncated now. The stop condition is nevertheless an inference about GitHub's behaviour
rather than a reading of what GitHub said, and it is wrong for any endpoint that filters
after paginating (a full-sized page is requested, a short one is returned, and the walk
ends early). A fleet that grows past 100 repos gets the bad half of this without a signal.

## Suggested fix

Once #258 lands, the transport exposes the response headers (`_send`), so the correct stop
condition is available to all four list methods: **walk while the response advertises
`rel="next"`, not while the batch is full.** One shared page-walk helper over `_send`,
replacing four copies of `len(batch) < 100`; the projection helper `_advertises_next_page`
from #258 is reusable as-is.

Worth doing in the same change: the four list helpers are tested against a
`_RecordingClient` that fakes `_request`
(`tests/test_github_client.py::_RecordingClient`), so none of them exercises the real
transport. A paginated fixture at the `_send` level would cover them properly.

## Acceptance

- [ ] The four list methods stop on the absence of `rel="next"`, not on a short page
- [ ] A paginated fixture proves a multi-page walk and a short-but-not-last page
- [ ] The inventory sweep's `live` set is either complete or the leg degrades loudly —
      never a partial set compared as if it were the whole org

## Context

Follow-up to #258 (which fixes the generic `get_json` read and leaves the dedicated list
methods explicitly out of scope). Related: #116 (the unmanaged-controls leg that added
`get_json`), ADR-0002 (the inventory sweep's contract), ADR-0007 (the edge/core split that
puts every network call in this module).

