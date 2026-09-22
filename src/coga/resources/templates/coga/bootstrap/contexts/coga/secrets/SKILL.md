---
name: coga/secrets
description: Ticket secret references (`env:` and `op://`), how launch resolves and injects them, `coga secret get`, the one-service-account vault policy, and why a declaration is not process isolation.
---

# Secrets

Never commit a credential. Tickets carry pointers, the operator's machine
carries values, and config carries almost nothing
([coga/configuration](../configuration/SKILL.md)).

## Declaring a ticket's secrets

There is no central catalog. A ticket declares what it uses inline:

```yaml
secrets:
  - STRIPE_KEY: op://<automation-vault>/stripe/api-key
  - WEBHOOK_URL: env:SLACK_WEBHOOK_URL
```

`src/coga/config.py` `parse_inline_secrets` accepts null or `[]` (none), or a
list of single-key maps `NAME: <ref>`. It rejects a non-list, a bare string
(the removed catalog form), a multi-key entry, a duplicate or empty name, a
name in the reserved `COGA_` namespace, and any ref that is not `op://…` or
`env:VAR`. A raw literal cannot live in a committed ticket. A ref lives on the
ticket that consumes it, not where the credential lives.

## Resolution at launch

`select_launch_secrets` resolves each ref live. `op://` refs are passed
verbatim to `op read`, stripping one trailing newline. `env:VAR` refs are read
from the operator's environment. Failure is loud and happens before any agent
or recipe process spawns, and before a draft's activation is written
([coga/launch](../launch/SKILL.md)). Failures are `op` missing, `op read`
non-zero (not signed in, no access), or an unset variable. Messages name the
Coga secret and reference, never the value.

`build_launch_env` then builds the child environment: it starts from the
**full parent environment**, removes each source variable an `env:VAR` ref
names, and writes each resolved value under its declared name.

## `coga secret get <ref>`

A human-facing query: resolve one `op://…` or `env:VAR` ref through the same
`select_launch_secrets` path and print the value to stdout, never logged or
posted (`src/coga/commands/secret.py`). It needs no `user`. A raw literal,
unset variable, or `op` failure exits 2 without printing a value. Agents do
not call it.

## Vault policy: one service account, one automation vault

Headless runs authenticate `op` with a 1Password **service account** through
`OP_SERVICE_ACCOUNT_TOKEN`, which `op` uses automatically while it is set. A
human delivers that token into the cron or systemd environment at run time.

- The service account is read-only and granted exactly **one automation
  vault**. That vault is its blast radius. A leaked token reads that vault
  and nothing else.
- Its own token lives in a separate root-level vault it is never granted,
  and never as an `op://` ref.
- Other vaults named by trust level are a human access taxonomy: legible
  sensitivity, separate human grants, independent rotation. The service
  account holds none of them, so a ticket must not declare `op://` refs
  outside the automation vault; they will not resolve.
- 1Password fixes a service account's vault access at creation. Widening it
  means a new account, a rotated token, and re-delivery to every machine and
  cron environment. Treat the scope as close to irreversible.

**Adding a headless secret:** create the item in the automation vault;
declare the `op://` ref on the consuming ticket (or `env:VAR` for a value the
operator already exports); verify with `coga secret get <ref>` in a clean
environment where `OP_SERVICE_ACCOUNT_TOKEN` is the only credential. A
personal `op` login reads everything and gives a false pass.

## A declaration, not a sandbox

Vault scoping bounds what a leaked token can read. It does not confine a
launched task. Because the child inherits the whole parent environment:

- `OP_SERVICE_ACCOUNT_TOKEN` normally survives, so the agent can `op read`
  anything in the automation vault, whatever its ticket declared.
- Destination names change the outcome.
  `TASK_OP_TOKEN: env:OP_SERVICE_ACCOUNT_TOKEN` scrubs the well-known name.
  `OP_SERVICE_ACCOUNT_TOKEN: env:OP_SERVICE_ACCOUNT_TOKEN` restores it.
  `OP_SERVICE_ACCOUNT_TOKEN: env:OTHER_TOKEN` replaces it. A child that must
  keep using the service account needs that name among the final
  destinations; using it only as a source is not enough.
- Scrubbing the token does not log `op` out. An inherited personal session,
  desktop-app integration, or other ambient credential may still
  authenticate, possibly with broader access. A command that works that way
  proves operator authority, not ticket-scoped access.

The `secrets:` list bounds what Coga resolves and names for a task. Read the
service-account boundary as the final child environment plus the vault
grant, and the process boundary as every inherited credential. Real
confinement needs process isolation Coga does not have. New reference kinds
would be another prefix branch in `parse_inline_secrets` /
`select_launch_secrets`, not a provider registry.
