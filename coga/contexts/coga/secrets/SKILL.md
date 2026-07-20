---
name: coga/secrets
description: A description of service account and vault usage for managing secrets in Coga. 
---

# Secrets

A ticket's `secrets:` are `op://vault/item/field` references. The SA token lives in the root-level vault, never in the vault it references (it's the key, not a payload) and never as an op:// ref. A human delivers it into the cron/systemd environment as OP_SERVICE_ACCOUNT_TOKEN at run time.

## The service account and its vault

- **Service account** — the headless 1Password identity.
  Authenticates via `OP_SERVICE_ACCOUNT_TOKEN`, read-only, scoped to a single
  vault. A leaked token can read that one vault and nothing else.
- **Vault** — the container the SA reads. Secrets will accrue in vaults named by their trust level

The `op` CLI auto-uses `OP_SERVICE_ACCOUNT_TOKEN` when it is set, so no coga
code changes for headless auth — exporting the token in the job process is
enough for every `op://` ref to resolve.

## Adding a headless secret

1. Create the item in a vault based on the trust level.
2. On the ticket that *consumes* it, declare the inline ref. The ref lives
   where its subject lives, not where the credential lives.

   ```yaml
   secrets:
     - NAME: op://coga-low-trust/<item>/<field>
   ```
3. Verify with `coga secret get op://coga-low-trust/<item>/<field>` in a clean
   env where `OP_SERVICE_ACCOUNT_TOKEN` is the only credential. A personal `op`
   login reads everything and gives a false pass on SA scoping.
