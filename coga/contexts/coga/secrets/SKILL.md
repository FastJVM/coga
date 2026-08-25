---
name: coga/secrets
description: A description of service account and vault usage for managing secrets in Coga. 
---

# Secrets

A ticket's `secrets:` are indirection references, never literal values: either
`op://vault/item/field` (resolved live with `op read`) or `env:VAR` (read from
the operator's environment). Both are safe to commit — they are pointers, not
payloads — and a raw literal is rejected outright. The SA token lives in the
root-level vault, never in the vault it references (it's the key, not a payload)
and never as an op:// ref. A human delivers it into the cron/systemd environment
as OP_SERVICE_ACCOUNT_TOKEN at run time.

## The service account and its vault

- **Service account** — the headless 1Password identity.
  Authenticates via `OP_SERVICE_ACCOUNT_TOKEN`, read-only. Grant one service
  account per repo / automation purpose only the vaults that purpose's headless
  work needs, and never the root-level vault holding its own token. A leaked
  token can read every vault granted to that account.
- **Vault** — the container the SA reads. Secrets will accrue in vaults named by their trust level.
  The tiers **classify**: they buy legible sensitivity, separate *human* access
  grants, and independent rotation. They do not contain a leaked SA token, which
  reaches every vault that account was granted.

The `op` CLI auto-uses `OP_SERVICE_ACCOUNT_TOKEN` when it is set, so no coga
code changes for headless auth — exporting the token in the job process is
enough for every `op://` ref a **ticket's `secrets:`** declares to resolve.
Config values are not `op://`-aware at all: `coga.toml` / `coga.local.toml`
resolve only `env:VAR` indirection (as in `[notification.slack].webhook`), and
an `op://` string there is passed through as a literal.

## Adding a headless secret

1. Create the item in a vault based on the trust level.
2. On the ticket that *consumes* it, declare the inline ref. The ref lives
   where its subject lives, not where the credential lives.

   ```yaml
   secrets:
     - NAME: op://coga-low-trust/<item>/<field>
   ```

   A value the operator already exports locally can use the same shape with an
   `env:VAR` ref instead — no vault, no `op` involved.
3. Verify with `coga secret get op://coga-low-trust/<item>/<field>` in a clean
   env where `OP_SERVICE_ACCOUNT_TOKEN` is the only credential. A personal `op`
   login reads everything and gives a false pass on SA scoping.
