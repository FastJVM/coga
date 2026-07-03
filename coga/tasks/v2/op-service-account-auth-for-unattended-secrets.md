---
slug: v2/op-service-account-auth-for-unattended-secrets
title: Support 1Password service-account auth for op:// secrets (unattended, no prompt)
status: draft
mode: agent
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

Follow-up to inline `op://` secrets (each ticket's `secrets:` resolves an
`op://vault/item/field` reference live with `op read` at launch).

### Problem

With 1Password **desktop app integration**, every `op read` triggers a system
authentication prompt (on Pop!_OS / COSMIC, a polkit "allow?" dialog). That is:

- **Fatal for unattended use** — recurring sweeps and `autonomy: auto` launches
  that resolve an `op://` secret have no human to click the prompt, so they
  hang or fail.
- **High-friction even interactively** — a click per `op read`, i.e. per
  op-backed secret per launch.

### What we want

First-class support for resolving `op://` secrets via a **1Password service
account** (`OP_SERVICE_ACCOUNT_TOKEN`), which `op read` honors natively and
which authenticates **non-interactively**, scoped to the vaults granted to the
account (this scoping is also the RBAC trust boundary for what an inline
`op://` reference can read — see `op-secret-dependency-init-enforcement`).

### Likely scope (verify)

`op` already reads `OP_SERVICE_ACCOUNT_TOKEN` from the environment, and relay
shells out to `op read`, so this may be mostly:

1. Confirm relay's launch / `secret get` subprocess environment passes
   `OP_SERVICE_ACCOUNT_TOKEN` through to the `op read` child (and that
   `build_launch_env`'s scrubbing doesn't strip it).
2. Decide where the operator sets it — a machine-local credential, so shell env
   / `relay.local.toml`, never committed. (The `[secrets]` catalog was removed,
   so this is operator env, not a relay secret key.)
3. Document the setup (README External CLI Tools + `relay/architecture` capability
   boundary): create a scoped service account, grant it the vault(s), export the
   token; interactive desktop-app integration stays the default for humans.
4. Make any failure loud (token invalid / lacks vault access → `op read`
   non-zero → the existing launch crash, naming the reference).

### Done when

A documented, working path to resolve `op://` secrets with no interactive
prompt via a service-account token, suitable for recurring / `autonomy: auto`
launches; verified the token reaches the `op read` subprocess and that a
bad/absent token fails loud without leaking the value.

## Context

- `_resolve_op_reference` / `select_launch_secrets` / `build_launch_env` in
  `src/relay/config.py`.
- Sibling v2 ticket: `op-secret-dependency-init-enforcement`.
- 1Password service accounts: https://developer.1password.com/docs/service-accounts/

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
