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
  Authenticates via `OP_SERVICE_ACCOUNT_TOKEN`, read-only. Never grant it the
  root-level vault holding its own token. A leaked token reads every vault that
  account was granted, so the blast radius is exactly the grant.
- **Vault** — the container the SA reads. Secrets will accrue in vaults named by their trust level.
  The tiers **classify**: they buy legible sensitivity, separate *human* access
  grants, and independent rotation. Whether they also bound the *automation's*
  blast radius depends on how many vaults one account is granted.

> **Open decision — do not read a recommendation into the above.** How SA
> grants map to trust tiers (one account per repo spanning tiers, one account
> per vault, or a single untiered vault) is an unsettled, human-owned choice
> tracked in `coga/tasks/service-account-scoping-single-vault-rule-conflict`.
> It sets the blast radius of a leaked token and the per-vault option needs
> code Coga does not have. Until that ticket's human step closes, describe
> current behavior and leave the model to the operator; do not publish one
> option as the contract.

**Scoping bounds the grant, not the process.** Everything above describes how
1Password grants bound what a leaked token reads. It does not describe a
sandbox around a launched task, and the two are easy to conflate.
`coga/contexts/coga/architecture/SKILL.md` records the mechanism under "This is
a declaration, not a sandbox": `config.build_launch_env()` starts from the full
parent environment and scrubs only the source variables an `env:VAR` ref names.
It does not special-case `OP_SERVICE_ACCOUNT_TOKEN`, so the token normally
survives and a launched agent can run `op read` against every vault that service
account can reach, regardless of what its ticket declared. Secret construction
first removes every named `env:VAR` source, then writes each resolved value
under its declared destination alias. The final alias set therefore matters as
much as the sources: `TASK_OP_TOKEN: env:OP_SERVICE_ACCOUNT_TOKEN` removes the
well-known name and prevents that variable from providing service-account-token
auto-authentication, while
`OP_SERVICE_ACCOUNT_TOKEN: env:OP_SERVICE_ACCOUNT_TOKEN` restores it and
`OP_SERVICE_ACCOUNT_TOKEN: env:OTHER_TOKEN` overwrites any inherited value with
the resolved `OTHER_TOKEN`. Removing that token does not log the `op` CLI out:
an inherited personal session, desktop-app integration, or other ambient
credential may still authenticate the child and may carry broader vault access.
A ticket's `secrets:` list bounds what Coga *resolves and names* for the task;
it does not otherwise bound what the task's process can reach. For the service-
account-token path, read the final child environment plus the vault and SA grant
as its boundary. For the process as a whole, include every other inherited auth
session and credential; read the declaration as documentation of intent, not
confinement.

The `op` CLI auto-uses `OP_SERVICE_ACCOUNT_TOKEN` while it remains set, so no
coga code changes are normally needed for headless auth — exporting the token
in the job process is enough for every `op://` ref a **ticket's `secrets:`**
declares to resolve. When the launched process itself must continue using `op`
specifically through the service account, ensure the *final destination
aliases* still include `OP_SERVICE_ACCOUNT_TOKEN`; merely using it as an
`env:` source is not enough. A personal `op` session may make the command work
without that variable, but that is inherited operator authority, not evidence
of ticket-scoped access.
Config values resolve almost nothing. Exactly two fields —
`[notification.slack].webhook` and `[notification.slack].important_webhook` —
run an `env:VAR` reference through the shared resolver; every other string in
`coga.toml` / `coga.local.toml` is taken literally, so an `env:VAR` written
anywhere else is a nonfunctional configuration, not an indirection. `op://` is
not understood in config at all, in those two fields or any other.

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
