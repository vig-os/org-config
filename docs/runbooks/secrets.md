# Runbook — secrets as code (SOPS/age)

How `vig-os` org secret **values** are managed as committed ciphertext and
applied to live GitHub. Decision record: [ADR-0003](../adr/0003-secrets-backend-sops-age.md).
Pipeline issue: [#22](https://github.com/vig-os/org-config/issues/22).

## Model in one paragraph

Secret values live as SOPS/age **ciphertext** under `secrets/*.yaml`, committed
and PR-reviewed. `.sops.yaml` pins the age **recipient** (public key). The apply
workflow decrypts in-memory at apply time, loads each value into a throwaway
`pass` store, and otterdog reads it for any secret declared in
`otterdog/vig-os/vig-os.jsonnet` with `value: 'pass:org-config/<NAME>'`. Values
are masked and never logged.

## What NEVER goes here (bootstrap exclusions — BINDING, ADR-0003)

- **GitHub App private key** (`ORG_CONFIG_APP_PRIVATE_KEY`) — authenticates the
  apply; cannot be bootstrapped by the pipeline it enables.
- **age private key** (`SOPS_AGE_KEY`) — decrypts everything here; cannot decrypt
  itself.

Both are provisioned out-of-band and held **only** as Actions/environment
secrets. One poisoned commit must never own both authentication and decryption.
Because this repo is **public**, keep the managed set **small and rotatable** — a
leaked age key retroactively exposes all ciphertext ever committed. Anything
heavily sensitive belongs in a **private** config repo, not here.

## Prerequisites (local)

`nix develop` provides `sops` and `age` (ADR-0005). You only need the **public**
recipient to add or re-encrypt a value; the private key is never required for
authoring.

## Create / add a secret

1. Add or edit the plaintext key in a staging copy, then encrypt in place — or
   add the key directly through the editor view:

   ```bash
   sops secrets/vig-os.yaml        # opens decrypted; re-encrypts on save
   # add:  MY_SECRET: the-value
   ```

   `.sops.yaml` auto-selects the recipient by path; SOPS encrypts **values only**
   (keys stay readable so reviewers see which secrets exist).
2. Declare it in `otterdog/vig-os/vig-os.jsonnet` so otterdog manages it:

   ```jsonnet
   orgs.newOrgSecret('MY_SECRET') {
     value: 'pass:org-config/MY_SECRET',
   },
   ```

3. Open a PR. Review the **ciphertext** diff. Merge to `dev` → apply-on-merge
   pushes it live.

> The pass path may contain `/` but **no `:`** — otterdog splits a secret value
> on the single `:` into `provider:path`, so a second colon breaks resolution.

## Rotate a value

A rotation is a normal change: `sops secrets/vig-os.yaml`, replace the value,
PR, merge, re-apply. Never mutate the live secret out-of-band — the next apply
would flag or revert it.

## Rotate the age key (or add/remove a recipient)

1. Generate/obtain the new recipient; update `SOPS_AGE_KEY` (the private half) as
   the Actions secret out-of-band.
2. Add the new `age:` recipient in `.sops.yaml`.
3. Re-wrap every managed file to the new recipient set:

   ```bash
   sops updatekeys secrets/*.yaml
   ```

4. Remove the old recipient from `.sops.yaml`, re-run `updatekeys`, PR + apply.

A suspected age-key leak forces immediate rotation of the **entire** managed set
(ADR-0003 supersession trigger).

## How apply consumes values (reference)

`.github/workflows/apply.yml` (issue #22): installs a pinned, checksum-verified
`sops`; generates an ephemeral passphrase-less GPG key; `pass init`s a temp
store under `runner.temp`; decrypts each `secrets/*.yaml` and inserts every key
as `org-config/<NAME>`; then `otterdog apply` resolves each `pass:org-config/…`
reference by shelling `pass`. The GPG key and store are discarded with the
runner and are **not** bootstrap secrets. Values are `::add-mask::`-ed and never
echoed (no `set -x` over secret vars).

## Canary acceptance (issue #22)

`ORG_CONFIG_CANARY` (a harmless value) proves the round trip: **encrypted in
repo → decrypted at apply → written as an org Actions secret → readable by a
workflow in a target repo**. A target-repo workflow reads it as
`${{ secrets.ORG_CONFIG_CANARY }}` (inherited from the org secret) — do not print
it; assert on it (e.g. non-empty / expected value) instead.

## Guardrails

- `detect-private-keys` (pre-commit) rejects a committed private key; only
  ciphertext ever lands. `check-yaml` keeps SOPS files valid YAML.
- Only the `production` environment (reviewer-gated) can read `SOPS_AGE_KEY` at
  apply time.
