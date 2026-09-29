---
type: issue
state: closed
created: 2026-09-28T08:55:59Z
updated: 2026-09-28T09:30:05Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/288
comments: 0
labels: chore, docs, priority:low, effort:small
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-29T08:00:44.877Z
---

# [Issue 288]: [[CHORE] Refresh the App-installation evidence for the 1.6.1 pin — the bump-time re-measure did not run on the Renovate-authored bump](https://github.com/vig-os/org-config/issues/288)

## Chore Type

General task

## Description

The App-installation-truncation limitation in `README.md:317-361` and the pin
comment in `justfile.project:30-39` both carry a **bump-time instruction**: at
every otterdog pin bump, re-read `get_app_installations` in the new release to
see whether it still reaches `GET /orgs/{org}/installations` unpaginated, and
re-measure each managed org's installation count. Those are the two reads no
test in this repo can make for you — one needs an upstream file, the other a
network call, and ADR-0007 keeps the suite pure and offline.

The pin then moved **1.5.0 → 1.6.1** in
[#283](https://github.com/vig-os/org-config/pull/283), merged 2026-09-28, as
exactly the mechanical five-literal change the
[#250](https://github.com/vig-os/org-config/issues/250) custom manager exists to
raise. Everything the repo *can* check, it checked: `tests/test_otterdog_pin.py`
proved the five literals agree and each kept its `# renovate:` marker, and
`plan.yml` ran on the PR because [#230](https://github.com/vig-os/org-config/issues/230)
put `justfile.project` in its `paths:` filter. None of that touches the two
reads, and nothing in the PR the reviewer saw asked for them.

**The consequence is stale citation, not a behavioural bug.** The prose now
attributes its evidence to a version the repo no longer runs:

- `README.md:319` — `org_client.py:484-491` **"(1.5.0, the ADR-0005 pin)"**
- `README.md:333` — **"Unfixed at the 1.5.0 pin"**
- `justfile.project:36-37` — the two counts dated **2026-09-25**, naming two orgs

All five pin literals read `1.6.1` (`justfile.project:54`,
`.github/workflows/{plan,apply,drift}.yml`, `template/.github/workflows/import.yml`).

Re-verified 2026-09-28, and the evidence is unchanged — which is the point: the
claim is still true, but it was true by luck rather than by reading, and the
version it names is wrong.

- `otterdog/providers/github/rest/org_client.py:484-491` in the pinned 1.6.1 is
  **byte-identical** to 1.5.0 — same file, same line numbers, still
  `request_json("GET", f"/orgs/{org_id}/installations")` with no `per_page`, no
  `Link` walk, returning `response["installations"]`.
- `gh api /orgs/<org>/installations --jq .total_count`: `vig-os` **8**,
  `exo-pet` **12**, `exoma-ch` **7**, `MorePET` **5** — every org in ADR-0006
  scope, all far under 30.
- Upstream unmoved: [#732](https://github.com/eclipse-csi/otterdog/issues/732)
  open (last activity 2026-09-23),
  [#772](https://github.com/eclipse-csi/otterdog/issues/772) open (2026-09-24),
  `main` still at `ba3d1f9` — the commit the README already cites, where the call
  is still byte-identical.

**The durable half: the checklist is the mechanism, and it should live where the
bump is reviewed.** Neither read can be automated honestly here, so there is
nothing to build — but the checklist currently sits in a `justfile.project`
comment, and a reviewer reading a five-line version diff has no reason to scroll
into it. Renovate can put the two reads in the body of the PR itself via
`prBodyNotes` on the existing otterdog `packageRules` entry, whose own
description already says *"the review is where the empty-plan evidence is
actually read"*. That is one config key, no new workflow, no new job, and no
pretence of checking the reads for the human.

## Acceptance Criteria

- [ ] `README.md:319` and `:333` name the pinned version, with the code location
      and its byte-identity re-verified against the pinned release rather than
      inferred from the previous one
- [ ] The `justfile.project` pin comment carries re-measured, re-dated counts for
      every org in ADR-0006 scope, not just the two with a live `org-config`
      repo
- [ ] The 31–100 "silent band" paragraph (`README.md:350-361`) is left intact —
      both thresholds are unchanged and it is still exactly true
- [ ] The two reads appear in the body of the next Renovate otterdog PR
      (`prBodyNotes` on the existing rule), so the checklist is read where the
      bump is adopted
- [ ] `CHANGELOG.md` gains one `### Changed` bullet

## Implementation Notes

Touch only the citations and the one Renovate key. The other `1.5.0` mentions in
`README.md` (`:226`, `:297`, `:369`) belong to *different* limitations whose own
evidence was not re-measured here — `:226` is a historical statement about when
the read gate was retired and is correctly past-tense; `:297` and `:369` each
need their own re-read (`_update_code_scanning_config`, the numeric-actor path)
and should be refreshed by whoever makes that read, not batched in on trust.

`README.md` is not generated in this repo, so it is edited directly; there is no
`docs/templates/` here.

## Related Issues

Refreshes the evidence recorded by
[#269](https://github.com/vig-os/org-config/issues/269) (whose own acceptance
items are complete); follows the bump in
[#283](https://github.com/vig-os/org-config/pull/283); touches the Renovate rule
from [#250](https://github.com/vig-os/org-config/issues/250); the limitation
itself tracks [upstream #732](https://github.com/eclipse-csi/otterdog/issues/732)
and is the sibling of [#262](https://github.com/vig-os/org-config/issues/262).

## Priority

Low

## Changelog Category

Changed

## Additional Context

Nothing is broken and no plan or apply behaves differently — this is maintenance
of written evidence. It is filed separately rather than reopened anywhere because
the miss is in the *bump*, not in the guard: the guard says what to do, and the
bump that arrived after it did not do it.

