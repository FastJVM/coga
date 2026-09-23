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
  Authenticates via `OP_SERVICE_ACCOUNT_TOKEN`, read-only, **scoped to a single
  automation vault**. Never grant it the root-level vault holding its own token.
  A leaked token reads that one vault and nothing else.
- **Vault** — the container the SA reads. Secrets accrue in vaults named by
  their trust level, but those tiers are a **human** access taxonomy: they buy
  legible sensitivity, separate *human* access grants, and independent
  rotation. They do **not** bound the automation's blast radius, because they
  are not granted to the service account at all. The SA holds exactly one
  automation vault, and that vault is its blast radius.

**The model: one service account, one automation vault.** There is one Coga
repo backed by 1Password and one read-only service account, granted a single
automation vault. Every other trust-named vault is human password/access
management the SA is never granted, and neither is the root-level vault holding
its own token. A ticket therefore must not declare `op://` refs outside the
automation vault — nothing will resolve them.

Treat that scope as close to irreversible. 1Password fixes a service account's
vault access **at creation**; there is no way to add a vault later. Widening
scope means a new account, a rotated token, and re-delivery to every machine and
cron environment, so a second vault is a migration, not a config change.

**Scoping bounds the grant, not the process.** Everything above describes how
1Password grants bound what a leaked token reads. It does not describe a
sandbox around a launched task, and the two are easy to conflate.
`coga/contexts/coga/architecture/SKILL.md` records the mechanism under "This is
a declaration plus an env scrub, not a sandbox": `config.build_launch_env()`
resolves the declared refs in the parent, then drops every 1Password CLI auth
variable (`OP_SERVICE_ACCOUNT_TOKEN`, `OP_CONNECT_TOKEN`, `OP_CONNECT_HOST`,
`OP_SESSION_*`) and each named `env:VAR` source from the child environment,
then writes each resolved value under its declared destination alias. A
launched agent therefore cannot `op read` through an inherited token, whatever
its ticket declared. The final alias set still matters:
`TASK_OP_TOKEN: env:OP_SERVICE_ACCOUNT_TOKEN` hands the token on under that
alias only, while `OP_SERVICE_ACCOUNT_TOKEN: env:OTHER_TOKEN` deliberately
restores the well-known name with the resolved `OTHER_TOKEN` — an explicit,
reviewable opt-in. The scrub bounds the child's environment, not its process:
a token file on disk, a shell profile that re-exports it, or a signed-in
desktop app may still authenticate the child and may carry broader vault
access. A ticket's `secrets:` list bounds what Coga *resolves and names* for
the task; read the vault and SA grant as the boundary of what a leaked token
reads, and every same-user credential source as the boundary of the process.

The `op` CLI auto-uses `OP_SERVICE_ACCOUNT_TOKEN` while it remains set, so no
coga code changes are normally needed for headless auth — exporting the token
in the job process is enough for every `op://` ref a **ticket's `secrets:`**
declares to resolve. When the launched process itself must continue using `op`
specifically through the service account, declare `OP_SERVICE_ACCOUNT_TOKEN`
as a *destination alias*; without that, the scrub removes it. A signed-in
desktop app may make the command work anyway, but that is ambient operator
authority, not evidence of ticket-scoped access.
Config values resolve almost nothing. Exactly two fields —
`[notification.slack].webhook` and `[notification.slack].important_webhook` —
run an `env:VAR` reference through the shared resolver; every other string in
`coga.toml` / `coga.local.toml` is taken literally, so an `env:VAR` written
anywhere else is a nonfunctional configuration, not an indirection. `op://` is
not understood in config at all, in those two fields or any other.

## Adding a headless secret

1. Create the item in the **automation vault** — the one vault the service
   account is granted. An item filed in a trust-named human vault is
   unreadable to the SA, so its ref will never resolve at launch.
2. On the ticket that *consumes* it, declare the inline ref. The ref lives
   where its subject lives, not where the credential lives.

   ```yaml
   secrets:
     - NAME: op://<automation-vault>/<item>/<field>
   ```

   A value the operator already exports locally can use the same shape with an
   `env:VAR` ref instead — no vault, no `op` involved.
3. Verify with `coga secret get op://<automation-vault>/<item>/<field>` in a
   clean env where `OP_SERVICE_ACCOUNT_TOKEN` is the only credential. A personal
   `op` login reads everything and gives a false pass on SA scoping.
