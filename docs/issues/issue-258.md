---
type: issue
state: closed
created: 2026-09-25T12:38:55Z
updated: 2026-09-25T17:16:55Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/258
comments: 1
labels: bug, priority:medium, area:workflow, effort:small, semver:patch
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-26T07:11:54.491Z
---

# [Issue 258]: [unmanaged-controls: get_json reads one page, so a list-projection row can assert a truncated set as clean](https://github.com/vig-os/org-config/issues/258)

## What's missing

`GitHubClient.get_json()` — the generic read every `unmanaged-controls.toml`
row asserts against — issues **one** GET and returns the decoded body:

```python
def _request(self, method: str, path: str, payload: dict | None = None) -> object:
    url = path if path.startswith("http") else f"{self._api_root}{path}"
    ...
    with urllib.request.urlopen(req) as resp:
        raw = resp.read()
    return json.loads(raw) if raw else None
```

No `per_page`, no `page`, and the response headers — including
`Link: …; rel="next"` — are discarded. The client's own dedicated list methods
do paginate explicitly (`?per_page=100&page={page}` in `list_org_secrets`,
the repo sweep, the drift-issue search), so the asymmetry looks unintended
rather than decided.

## Why it matters

Since #205 a row can project over a list — `[].name`, `[].context`,
`[].permissions.push` — and `compare = "set"` compares the result as a set.
List-shaped rows are now a first-class supported shape. But under a projection
the transport reads **page 1 only**, and GitHub's default page size is 30.

The failure mode is the bad one. A truncated list does not error and does not
degrade to `MISSING`; it compares as a **shorter set**, exactly the outcome
`select_path`'s own docstring calls out as unacceptable for a partial
projection:

> a partial projection would compare as a shorter set and read as drift or,
> worse, as clean.

The docstring is right about the consequence and the guard is one layer too
high: `_walk` refuses a projection *it* cannot satisfy, but it cannot see a
list the transport already truncated. Over 30 elements, a row either
manufactures drift (expect longer than live) or — where `expect` was itself
seeded from a truncated read — reads permanently clean while the real
collection diverges underneath it.

## Not yet biting, filed before it does

Every list row today is small: `exo-pet`'s `exopet-team-*` rows read eight
repositories, ruleset `rules` arrays are a handful. Nothing is truncated right
now. The reason to file it anyway is that the next natural rows are the ones
that grow — repository collaborators, team members, a large org's repo list —
and a row that silently asserts the first 30 of something is worse than no row,
because the table's whole contract is that a green row means verified.

## Sketch (not a decision)

Cheapest first, all stdlib:

1. **Default `per_page=100`** on `get_json` when the path carries no
   `per_page`. One line, raises the ceiling 3.3×, fixes nothing structurally.
2. **Refuse a truncated read.** Keep the single GET, but read the response's
   `Link` header; if it has `rel="next"`, return a degradation
   (`UNRESOLVED`) rather than the partial body. The row then reports "could not
   resolve" instead of asserting a lie — consistent with the existing doctrine
   that a row degrades only itself and never guesses.
3. **Paginate `get_json`** the way the dedicated methods already do, and drop
   the guard. Most correct, most code, and it changes the memoization key shape
   in `_evaluate` slightly.

2 alone would close the correctness hole; 1 + 2 together are probably the right
increment, with 3 when a row genuinely needs a long list.

## Acceptance

- [ ] A list-projection row over a collection longer than one page either
      resolves completely or degrades — never asserts a truncated set
- [ ] The behaviour is covered by a test with a paginated fixture
- [ ] `select_path`'s docstring and the table's doctrine section say which

---

# [Comment #1]() by [c-vigo]()

_Posted on September 25, 2026 at 05:09 PM_

Spike outcome: the sketch's **options 1 + 2** are being implemented (TDD), and option 3 is
deferred on evidence. Notes worth recording before the PR.

**Option 3 (paginate `get_json`) is deferred, and not only on cost.** GitHub returns two
body shapes behind these rows: a root list (`/repos/{o}/{r}/rules/branches/{b}`,
`/orgs/{org}/repos`) and an envelope keyed by a name that differs per endpoint (`secrets`,
`repositories`, `check_runs`, `workflow_runs`, …). A *generic* merge therefore needs
per-endpoint body-shape knowledge — which is exactly what the four dedicated list methods
already encode, and what `get_json` exists to avoid. The defensible narrow version is
"paginate when the body is a root list, refuse otherwise" (~20 lines), and the refusal stays
as the backstop either way, which is why option 2 is the right thing to land first. The
refusal also converts the ceiling from a silent truncation into a loud `UNRESOLVED` naming
the endpoint — i.e. it gives option 3 a trigger instead of a guess.

**One claim in the sketch above is wrong: option 3 does not change the memoization key
shape.** `_evaluate_control` caches on the row's **resolved endpoint** — `cache[endpoint]`,
`controls.py:505-510`, over the `cache: dict[str, object | ApiError]` declared at `:469` —
and `get_json` rewrites the path internally (adding `per_page=100`), so the key is untouched
by this patch and would stay untouched by option 3. There is no cache-shape cost to weigh.

**Degradation verdict: reuse `UNRESOLVED`, do not add a fourth status.** The contract is
identical to the three existing causes (`ApiError` at `:512`, `MISSING` at `:527`, not-a-set
at `:542`): the row was not readable *as asserted*, so it degrades only itself, its issue is
left alone, and nothing joins `clean_fingerprints`. The distinction that matters is
human-readable, so it lives in the note and in the report's `actual` column (`truncated`),
not in the status string.

**Inert on merge day, by verification rather than by hope.** All seven distinct endpoints in
this repo's `unmanaged-controls.toml` return **no `Link` header at all** at `per_page=100`
(`/orgs/{org}`, `/orgs/{org}/actions/permissions`, `.../fork-pr-contributor-approval`,
`/orgs/{org}/code-security/configurations/237480`, `/repos/{org}/{repo}`,
`/repos/{org}/{repo}/actions/permissions` and its fork-PR variant), so no vig-os row can
change verdict — expect the same 13 OK / 3 TOLERATED. Positive control that the guard does
fire against real GitHub: `gh api -i "/repos/vig-os/devkit/commits?per_page=100"` returns
`Link: …page=2>; rel="next", …page=38>; rel="last"`.

**Downstream gets this only at its next engine pin bump.** `exo-pet/org-config` pins
`vig-os/org-config/.github/workflows/drift.yml@022462b # v1.4.0`, so nothing changes there
until that pin moves. When it does: exo-pet's list rows are all far inside one page (the
`exopet-team-*` rows read 8 repositories; 12 org installations; the `per_page=100` rows are
left alone by the query rewrite), so no flip is expected — but a downstream row over a
>100-element collection *would* flip `OK` -> `UNRESOLVED`, and that is the fix working, not a
regression. Worth a sentence in the release note. Labelled `semver:patch` on that basis:
backward-compatible bug fix, downstream-visible only where a row was asserting a partial set.

**Follow-up filed: #260.** `list_org_repos` (`src/drift_layer/github_client.py:122-137`) is
the same header-blind assumption one layer down, and worse: it stops on `len(batch) < 100`,
so a short-but-not-last page shortens the **input to the whole inventory sweep** rather than
degrading one row — a live repo past the cut produces no `undeclared` record (the ADR-0002
detection goes quiet) and a declared repo past the cut produces a false `absent` one. The
same stop is in `list_open_drift_issues` (`:117`), `list_org_secrets` (`:161`) and
`list_org_secret_repositories` (`:175`). Out of scope here; `_send` makes the correct fix
cheap afterwards.


