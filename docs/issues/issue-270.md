---
type: issue
state: open
created: 2026-09-25T20:27:32Z
updated: 2026-09-25T20:27:32Z
author: c-vigo
author_url: https://github.com/c-vigo
url: https://github.com/vig-os/org-config/issues/270
comments: 0
labels: chore, priority:low, effort:small
assignees: none
milestone: none
projects: none
parent: none
children: none
synced: 2026-09-26T07:11:50.823Z
---

# [Issue 270]: [Decide whether `ORG_CONFIG_APP_CLIENT_ID` should stay an Actions secret — `GET /apps/vig-os-org-config` returns the Client ID and the full grant unauthenticated](https://github.com/vig-os/org-config/issues/270)

## What's wrong

`ORG_CONFIG_APP_CLIENT_ID` is stored and declared as an **Actions secret** — but its value is
world-readable from GitHub's own public API, with no token at all. Probed 2026-09-25,
unauthenticated:

```console
$ curl -s https://api.github.com/apps/vig-os-org-config | jq '{client_id, permissions}'
{
  "client_id": "Iv23liFmoQq21Vex9JUi",
  "permissions": {
    "administration": "write",
    "organization_administration": "write",
    "organization_secrets": "write",
    …17 entries…
  }
}
```

So the anonymous payload carries both the Client ID **and** the full permission grant. Nothing about
the value is confidential, and treating it as a secret protects nothing: a Client ID mints no token
without the PEM, which is the actual credential (`ORG_CONFIG_APP_PRIVATE_KEY`).

Where it is held as a secret today:

- `otterdog/vig-os/vig-os.jsonnet:599` — declared as a repo secret on `org-config`
  (`orgs.newRepoSecret('ORG_CONFIG_APP_CLIENT_ID') { value: '********' }`), beside the private key
  and `SOPS_AGE_KEY`.
- `docs/runbooks/github-app.md:200-208` — the **Bootstrap secrets** table lists it with the PEM as
  a bootstrap secret "never managed as code" (ADR-0003).
- Consumed as `secrets.ORG_CONFIG_APP_CLIENT_ID` in `plan.yml:193`, `apply.yml:390`/`:499`,
  `drift.yml:222`/`:316`, `apply-engine.yml:118`/`:142`, `testbed-e2e.yml:162`/`:172`, and declared
  as a `workflow_call` secret input in `plan.yml:114`, `apply.yml:165`, `drift.yml:131`.
- `template/README.md:101` and the four `template/.github/workflows/*.yml` callers pass it as a
  secret to every downstream org.

## Why it matters

Low stakes either way — this is a **decision to record, not a leak to fix**. It matters for three
small reasons:

1. **Somebody will one day treat a leaked Client ID as an incident.** It appears in logs, in
   `workflow_call` secret plumbing, and in a runbook section headed "Bootstrap secrets". Nothing in
   the repo says it is public. The rotation runbook should not spend a step on a value anyone can
   `curl`.
2. **It costs plumbing.** Being a secret means it must be declared on every reusable workflow's
   `secrets:` block and passed explicitly by every downstream caller — a real onboarding step for
   `exoma-ch` / `MorePET` and a real failure mode (an unset secret resolves to empty and
   `actions/create-github-app-token` fails late). A **variable** (`vars.`) would need neither, since
   `workflow_call` inherits `vars` from the calling repository's org/repo scope automatically.
3. **It touches the client-ID-only convention (#112).** That program's whole point is that the
   client ID is the identifier form the App-token action prefers. Whether the *organization* treats
   client IDs as secrets or as variables is a convention worth stating once, because #112 will keep
   creating them (`COMMIT_APP_CLIENT_ID`, `RELEASE_APP_CLIENT_ID`, `DEVKIT_UPGRADE_APP_CLIENT_ID`
   are all declared `value: '********'` org secrets today, same question).

## Suggested fix

**Decide, then write the decision down. Do not change the storage without deciding first.**

Option A — **keep as a secret** (recommended default, lowest churn):
- Uniform with the private key it is always paired with, uniform with the three `*_APP_CLIENT_ID`
  org secrets #112 created, and no workflow, template or downstream caller changes.
- Add one sentence to `docs/runbooks/github-app.md` beside the Bootstrap secrets table: the Client
  ID is public (`GET /apps/{slug}` returns it unauthenticated), it is stored as a secret for
  uniformity with the key, and a disclosed Client ID is **not** a rotation trigger. Pairs naturally
  with the Visibility section #261 adds to the same file.

Option B — **move to a repository/organization variable**:
- Drops it from every `secrets:` block and every downstream caller; the value becomes visible in
  the org config, which is honest.
- Costs a coordinated edit across `plan.yml`, `apply.yml`, `drift.yml`, `apply-engine.yml`,
  `testbed-e2e.yml`, the four `template/` callers, `template/README.md`, the runbook, and the
  jsonnet — with a downstream cutover that is only safe at a pin bump (an engine that reads `vars.`
  and a caller that still passes `secrets.` is a silent empty credential). Otterdog models Actions
  variables, so the declaration would move from `secrets:` to `variables:` in the jsonnet and become
  genuinely asserted rather than dummy-valued — a real, if small, gain.

Either way the security posture is unchanged: the PEM is the credential, and it stays a secret.

## Acceptance

- [ ] A decision is recorded (secret for uniformity, or variable) with the reason
- [ ] `docs/runbooks/github-app.md` states that the Client ID is public and that its disclosure is
      not a rotation trigger
- [ ] If the decision is "variable", a migration issue exists that sequences engine and downstream
      callers across a pin bump rather than flipping both at once
- [ ] The decision covers the other `*_APP_CLIENT_ID` secrets (#112) or explicitly scopes itself to
      this one

## Context

Out-of-scope finding from the #261 spike (§6.1), which probed the App anonymously while verifying
its visibility. Related: #261 (the App's visibility decision, same runbook file), #112 (client-ID
consolidation, which created the three sibling `*_APP_CLIENT_ID` org secrets), ADR-0003 (bootstrap
secrets excluded from SOPS), ADR-0004 (the App auth model).

