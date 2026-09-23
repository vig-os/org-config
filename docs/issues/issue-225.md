---
type: issue
state: open
created: 2026-09-23T08:08:59Z
updated: 2026-09-23T11:36:10Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/225
comments: 3
labels: none
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-23T21:09:35.080Z
---

# [Issue 225]: [Bump the ADR-0005 otterdog pin to 1.5.0 — ungates ruleset reads (#107), needs a declare-before-bump migration note](https://github.com/vig-os/org-config/issues/225)

## What

Move the ADR-0005 single-source-of-truth pin in `justfile.project`

```just
otterdog_version := "1.4.0"
```

to `1.5.0`, and cut a release — because the release note is the part downstream
actually needs (see *Migration* below), not the one-line diff.

## Why now

`eclipse-csi/otterdog` [#731](https://github.com/eclipse-csi/otterdog/pull/731)
(`ab66569`, 2026-08-18) removed the `repo.private is False or
org_settings.plan == "enterprise"` condition from the ruleset read paths — the
exact gate behind **#107** and
[eclipse-csi/otterdog#729](https://github.com/eclipse-csi/otterdog/issues/729),
both still open here. It shipped in **otterdog v1.5.0** (2026-09-07). Verified
at the release tag:

```console
$ gh api /repos/eclipse-csi/otterdog/compare/v1.4.0...v1.5.0 \
    --jq '[.commits[].sha[0:8]] | index("ab665694")'
23

$ gh api "/repos/eclipse-csi/otterdog/contents/otterdog/models/github_organization.py?ref=v1.5.0" \
    --jq .content | base64 -d | grep -n "ruleset_config is not None"
659:            if jsonnet_config.default_org_ruleset_config is not None:
754:    if jsonnet_config.default_repo_ruleset_config is not None:
```

Both read paths are ungated at v1.5.0. A private-repo-only org below Enterprise
can finally declare its repository rulesets instead of hand-managing them, which
is what #107 exists to unblock.

Renovate will not do this on its own: `renovate.json` enables `github-actions`,
`pep621` and `npm`, and the pin is a bare literal in a `justfile`, matched by
none of them.

## Migration — this release is not safe to adopt blind

This is the reason to treat it as more than a version bump, and it applies to
**every** downstream org that has rulesets created out of band.

Before v1.5.0, a private repo's live rulesets were never read, so the live model
held none, the config declared none, and the plan was silent. That silence is
exactly what made hand-managed rulesets possible under #107. At v1.5.0 the live
model holds them while the config still declares none, so the plan flips from
silence to proposing a **deletion per ruleset**:

- the scheduled `drift` run opens a `drift` + `critical` issue per ruleset, and
- an `apply` dispatch **deletes live branch protection** — including things a
  config has no rows for, such as signature requirements and no-bypass tag
  rulesets.

The dispatch gate (#202) bounds this to a deliberate human act, but the plan
would be inviting that act, and the drift issues would arrive unprompted on the
next schedule.

So the release note should state the order explicitly: **declare the rulesets in
the jsonnet first, then bump the pin, in one change**, with an empty plan as the
acceptance evidence. A downstream that bumps first gets a plan that proposes
dismantling its own protection.

## The bump does not propagate to downstream callers

Worth saying in the release note, because it is the opposite of what a version
bump usually implies. Per **#56**, the reusable workflows check out the
*caller's* repository, which has no `justfile.project`, so the fallback path
cannot reach this pin:

```yaml
- name: Resolve otterdog version pin
  env:
    OTTERDOG_VERSION_INPUT: ${{ inputs.otterdog_version || '' }}
  run: |
    if [ -n "${OTTERDOG_VERSION_INPUT}" ]; then
      version="${OTTERDOG_VERSION_INPUT}"
    elif [ -f justfile.project ]; then
      version="$(grep -oP 'otterdog_version\s*:=\s*"\K[^"]+' justfile.project)"
    else
      echo "::error::no otterdog_version input and no justfile.project in the checkout (downstream callers must pass the input — issue #56)"
      exit 1
    fi
```

Downstream callers pass the pin as a literal input beside the engine SHA pin.
Updating the engine ref alone therefore changes nothing about which otterdog
runs — each downstream must edit the literal in its own `plan` / `apply` /
`drift` callers. The "lockstep" is a hand-mirrored convention, not inheritance,
and the release note is the only thing that tells downstream to mirror it.

If that is considered a wart, a follow-up could let the reusable workflow
default to its own checked-out pin rather than failing — but that is a separate
change from this bump, and #56 chose the explicit input deliberately.

## Also worth checking while bumping

v1.5.0 is a minor, not a patch. From its release notes, the items most likely to
move a plan independently of the ruleset fix:

- **#718** warn on unknown properties found while validating an organization —
  may surface new warnings against existing configs
- **#712** failfast when required configuration is missing, empty or untrimmed —
  touches `otterdog.json` handling
- **#643** `deploy_keys_enabled_for_repositories` and **#642** custom-property
  `values_editable_by` — new schema fields, the usual source of surprise
  `to change` lines
- whether the pinned `otterdog-defaults` base template needs to move with it

## Still blocked upstream

Organization-level rulesets remain unusable below Enterprise even at v1.5.0:
`GitHubOrganization.validate()` still raises an `ERROR` on a non-enterprise plan,
although #731 removed the plan gate from the org read path in the same commit.
Filed as
[eclipse-csi/otterdog#763](https://github.com/eclipse-csi/otterdog/issues/763)
(2026-09-23). So this bump unblocks **repository** rulesets only; anything
org-wide stays hand-managed.

## Acceptance

Revised after evaluation (see the evaluation comment on this issue, which
corrects four claims in the Migration / "Also worth checking" sections above —
most importantly that `apply` does **not** delete: the workflow omits
`--delete-resources`, so the exposure is a red plan plus drift issues, not lost
branch protection).

**Pin — all five literals move together** (the 1.4.0 bump missed one, #164 item 7):

- [ ] `justfile.project:19` — `otterdog_version := "1.5.0"`
- [ ] `template/.github/workflows/plan.yml` — `otterdog_version: "1.5.0"`
- [ ] `template/.github/workflows/apply.yml` — `otterdog_version: "1.5.0"`
- [ ] `template/.github/workflows/drift.yml` — `otterdog_version: "1.5.0"`
- [ ] `template/.github/workflows/import.yml` — `default: "1.5.0"`

**Explicitly NOT in scope**

- [ ] `otterdog.json` keeps `otterdog-defaults@v0.13.1`. v0.14.x adds
      `max_cache_size_gb`, whose endpoint answers `402` on this org's Free plan,
      which would write a permanent `WARNING` into `plan.txt` on every run.
      A deliberate decision, recorded — not an oversight.

**Verification**

- [ ] `just precommit` green (includes `otterdog@1.5.0 validate --local`)
- [ ] `just test` green — L1 plan-fixture recheck per ADR-0007: 1.5.0 is a
      **minor**, and this pin is the plan-format anchor (ADR-0005), so confirm
      the recorded fixtures still parse or re-record them deliberately
- [ ] This PR's own `plan` check reports an **empty** diff against live `vig-os`
      before merge — the acceptance evidence, as in PR #145

**Documentation truth**

- [ ] README "Known limitations" — the private-repo ruleset read-gate bullet
      (#191) is retired or restated as fixed-at-1.5.0
- [ ] ADR-0005 `## Corrections` — "Renovate owns the pin" is false;
      `renovate.json` enables only `github-actions`/`pep621`/`npm`, none of which
      can see a `justfile`. Fix the same claim at `justfile.project:18` and the
      "Renovate can bump this" comments in the `template/` callers.
- [ ] `CHANGELOG.md` `## Unreleased` entry

**Release + follow-through**

- [ ] Release cut, with a migration note covering: declare-before-bump ordering,
      the corrected severity (red plan + drift issues, **not** deletion), the
      fact that downstream callers must hand-edit their own literals (#56), and
      that the defaults pin stays at v0.13.1
- [ ] #107 closed against the released version
- [ ] Note what remains blocked by eclipse-csi/otterdog#763 (org-level rulesets
      still ERROR below Enterprise — `validate()` gate untouched by #731)
- [ ] Note that #209 is **not** fixed by this bump (eclipse-csi/otterdog#738
      still open; `_update_code_scanning_config` byte-identical at v1.5.0), so it
      does not read as silently resolved

---

# [Comment #1]() by [c-vigo]()

_Posted on September 23, 2026 at 09:29 AM_

Filed #228 alongside this: the `otterdog_version` contract itself, rather than the pin value.

Relevant to the timing here — #56 put the pin literal in every downstream caller on the stated premise that "Renovate can bump both", and it does not: the shipped `template/renovate.json` enables only the `github-actions` manager, which sees `uses:` refs and not a bare `with:` input, so downstream otterdog pins are maintained by nothing. If #228's default lands in the same release as this bump, existing downstreams delete their literals and inherit the pin with the engine ref they already track, instead of each hand-mirroring `1.5.0` and the next one after that.

The migration note in this issue covers both either way — a downstream that inherits the version still needs to know the ruleset reads are now ungated before it merges the bump.


---

# [Comment #2]() by [c-vigo]()

_Posted on September 23, 2026 at 09:31 AM_

## Evaluation — proceed, with four corrections to the body above

Evaluated against tag `v1.5.0` and the live `vig-os` org. 1.5.0 is confirmed the
newest release (PyPI `1.5.0`, uploaded 2026-09-07T17:13:25Z; no 1.5.1/1.6.0), so
the target is current. `ab665694` is in `v1.4.0..v1.5.0` and both read gates are
gone. **The bump is worth doing and is low-risk for this repo** — but four claims
above are wrong, and the two facts that actually make it safe are missing. Both
matter for the release note, which is the real deliverable here.

### Verified safe for this repo

`otterdog 1.5.0 validate --local` against the committed config produces output
**identical** to 1.4.0 — validation succeeds, same info set, no new warnings, no
failfast.

The ungated read adds exactly two HTTP calls against this org, both of which
fail closed on the Free plan:

```console
$ gh api repos/vig-os/qms/rulesets
403 Upgrade to GitHub Pro or make this repository public to enable this feature.
$ gh api orgs/vig-os/rulesets
403 Upgrade to GitHub Team to enable this feature.
```

Every other repo here is public, so its rulesets were always read and are already
declared; `qms` is the only private repo and declares none. **Net effect on
`vig-os`: two extra calls, zero plan change.**

### Four claims above are wrong

**1. An `apply` dispatch does not delete live branch protection.** This is the
most consequential correction, because it inverts the severity of the Migration
section. `apply.yml:411` runs `apply --local --no-web-ui --force` and
deliberately omits `--delete-resources` (rationale at `apply.yml:91-93`).
`git diff v1.4.0..v1.5.0 -- otterdog/operations/apply.py` is **empty**, and at
`v1.5.0` the loop still reads:

```python
for patch in patches_ordered_by_readonly_status:
    if patch.patch_type == LivePatchType.REMOVE and not self._delete_resources:
        progress.advance(task)
        continue
```

The summary still prints deletions as `"live resources ignored"`. So the REMOVE
patches are counted and skipped, not executed. The real exposure is narrower and
entirely on the read side: a **red plan** plus one `drift`+`critical` issue per
phantom-deleted ruleset (`models.py:19` maps `-` → `delete`, `parser.py` records
one `DriftRecord` per `-` resource, `reconcile.py` opens one issue per record),
and those issues do **not** self-close. Declare-before-bump remains the right
ordering — for noise and a red plan, not for destroyed protection.

**2. #712 does not touch `otterdog.json` handling.** It is webapp-only
(`otterdog/webapp/config.py` + its tests). This engine runs
`plan --local --no-web-ui`; zero impact.

**3. #718 is backwards.** It does not surface new warnings — it *downgrades* a
previously-fatal error. At 1.4.0 an unknown property raised; at 1.5.0
`additionalProperties` errors are logged as warnings and only other errors
block. A config that validates green at 1.4.0 cannot acquire a warning at
1.5.0, by construction. Strictly more permissive.

**4. #643 / #642 produce no surprise `to change` lines.** Both add fields absent
from the pinned `otterdog-defaults` **v0.13.1**. otterdog builds `included_keys`
from the base template, so neither key is fetched or diffed. Confirmed by the
identical validate output above.

### Two things the body misses

**#731 also added the 403/404 tolerance, and that is what makes this safe.** The
same commit gave both ruleset clients `if ex.status in (403, 404): return []`
(`repo_client.py`, and `org_client.py` for the org path), at `debug` level — so
the Free-plan 403s above are absorbed silently and add no lines to `plan.txt` for
the drift layer to parse. Worth stating in the release note: it is the reason a
Free-plan org can take this bump at all.

**The pinned `otterdog-defaults` must stay at v0.13.1 — answering the open
question in the body with an active "no".** Upstream defaults have moved to
v0.14.2, which adds the three new 1.5.0 fields *plus* `max_cache_size_gb: 10`.
That key would enter `included_keys` and trigger a call that is not free:

```console
$ gh api /orgs/vig-os/actions/cache/storage-limit
402 Please ensure your account has a valid payment method on file to access this service.
```

#739 added `_get_optional_json()`, which tolerates 402/403/404 but logs a
`_logger.warning`. So bumping the defaults would write a permanent WARNING line
into `plan.txt` on every run and leave the setting unvalidated. Keeping v0.13.1
avoids the call entirely. (#739 is also, incidentally, the largest code change in
the release — it rewrote the repo read path with `expected_org` key-narrowing —
and is inert at the current defaults pin.)

### Scope corrections

- **Five pin literals, not one.** `justfile.project:19` plus
  `template/.github/workflows/{plan,apply,drift,import}.yml`. Precedent: the
  1.4.0 bump (`818e1f8`) touched six files and *still* missed `import.yml`,
  logged as #164 item 7 — a downstream org would import on one version and plan
  on another. Enumerated in the acceptance criteria below.
- **The ADR-0007 fixture gate belongs in acceptance.** 1.5.0 is a minor, and
  ADR-0005 makes this pin the plan-fixture format anchor; ADR-0007 requires a
  refresh if the format moved. PR #145 ran exactly this check for 1.4.0.
- **#209 is not fixed by this bump.** `_update_code_scanning_config` is
  byte-identical at v1.5.0 and still raises unconditionally; upstream
  eclipse-csi/otterdog#738 remains open. The release note should say so, or #209
  will read as silently resolved. The fix pattern now exists in-tree
  (`_get_optional_json`), so an upstream PR would be small.
- **Documentation-truth fixes this bump forces.** The README known-limitation
  (#191) describes the read gate as current and must be retired. Separately,
  `justfile.project:18` and ADR-0005's Consequences both state that **Renovate
  owns this pin** — false: `renovate.json` enables only `github-actions`,
  `pep621` and `npm`, none of which can see a `justfile`, which is precisely the
  observation this issue opens with. The template callers carry the same false
  "Renovate can bump this" comment. ADR-0005 has a `## Corrections` block for
  this.
- **Upstream #729 stays open** despite being fixed by #731, so any downstream
  comment keyed to "once otterdog#729 lands" will never fire. Trigger on the
  released version instead.

### Downstream impact

There is exactly one downstream consumer org (`exoma-ch` and `MorePET` have no
config repo). It is on Team with private repos, currently declares **no**
rulesets, has an **empty** drift allow-list, and hand-manages **six** live
rulesets recorded as `kind = "unassertable"` rows. A blind bump there turns all
six into proposed deletions — a red plan and six `drift`+`critical` issues on the
next scheduled run. Its config already carries the re-declare instruction, so the
migration is one PR on that side: declare the six in jsonnet, retire the rows,
and move its three caller literals with the engine SHA pin. Tracked downstream;
not actionable from here.

One interaction worth flagging: this release also ships #205, so that org gains
*two* mechanisms for the same controls at once — jsonnet declaration (reads now
work) and unmanaged-control assertion (list paths now work). They should not
double-manage; the jsonnet is the better home for the branch rulesets, which
makes most of those rows redundant rather than convertible.

### Corrected acceptance criteria

Applied to the issue description.


---

# [Comment #3]() by [c-vigo]()

_Posted on September 23, 2026 at 11:36 AM_

Reopening: GitHub auto-closed this on the PR #229 merge via the linked-branch
association (`gh issue develop`), not because the acceptance criteria are met.
The engine work is done; the release-facing half is not.

**Done in PR #229** (merge commit `d00fddd`):

- [x] All five pin literals at `1.5.0` — `justfile.project` plus
      `template/.github/workflows/{plan,apply,drift,import}.yml`
- [x] `otterdog.json` keeps `otterdog-defaults@v0.13.1`, recorded as a deliberate
      decision in ADR-0005 `## Corrections`
- [x] `just precommit` green (incl. `otterdog@1.5.0 validate --local`),
      `just test` 127/127 — the ADR-0007 L1 plan fixtures still parse, so 1.5.0
      did not move the plan output format; no re-record needed
- [x] Empty plan against live `vig-os` —
      [run 35844030809](https://github.com/vig-os/org-config/actions/runs/35844030809):
      `Plan: 0 to add, 0 to change, 0 to delete`
- [x] README "Known limitations" reconciled; ADR-0005 `## Corrections` seeded;
      the false "Renovate owns the pin" claim fixed in all four places
- [x] `CHANGELOG.md` `## Unreleased` entries

Worth noting the plan evidence had to be dispatched **by hand**: `plan.yml`'s
paths filter omits `justfile.project`, so a pure pin bump gets no plan check.
Split out as #230.

**Still open — the release-facing items:**

- [ ] Release cut, with the migration note (declare-before-bump ordering; the
      corrected severity — red plan + drift issues, **not** deletion; downstream
      callers hand-edit their own literals per #56; defaults stay at v0.13.1)
- [ ] #107 closed **against the released version** — downstream consumes a
      released tag, not `main`
- [ ] Release note records what stays blocked by
      [upstream #763](https://github.com/eclipse-csi/otterdog/issues/763)
      (org-level rulesets still ERROR below Enterprise) and that #209 is **not**
      fixed by this bump
      ([upstream #738](https://github.com/eclipse-csi/otterdog/issues/738) open;
      `_update_code_scanning_config` byte-identical at v1.5.0)

The `## Unreleased` block now carries both this and #205, so the same release
gives the downstream org the ruleset-declaration capability *and* the
list-addressable unmanaged-control paths — the two should not be used to manage
the same control.

