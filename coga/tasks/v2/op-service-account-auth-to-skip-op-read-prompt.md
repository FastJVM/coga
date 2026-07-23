---
slug: v2/op-service-account-auth-to-skip-op-read-prompt
title: Support 1Password service-account token to skip the per-`op read` prompt
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow: null
---

## Description

With 1Password desktop-app integration, every `op read` fires a system
authentication prompt (a polkit "allow?" dialog on Pop!_OS / COSMIC), so a
launch that resolves inline `op://` secrets costs one click per op-backed
secret. Support resolving `op://` references via a 1Password service-account
token (`OP_SERVICE_ACCOUNT_TOKEN`), which `op read` honors natively without a
prompt, so an operator running several op-backed launches in a row (e.g. a
hand-run `coga recurring` sweep) isn't clicking through prompts. Desktop-app
integration stays the default for humans; the token is an opt-in convenience.

### Likely scope (verify)

- Confirm the launch / `coga secret get` subprocess env passes
  `OP_SERVICE_ACCOUNT_TOKEN` through to the `op read` child, and that
  `build_launch_env`'s scrubbing doesn't strip it.
- Set it as machine-local operator env (shell / `coga.local.toml`), never
  committed.
- Document the setup: create a scoped service account, grant it the vault(s),
  export the token.
- Keep failures loud: a bad or vault-scoped-out token makes `op read` non-zero,
  which is the existing launch crash naming the reference (never the value).

### Done when

An operator can export a service-account token and have `op://` references
resolve with no prompt, verified the token reaches the `op read` subprocess and
that a bad token fails loud without leaking the value.

## Context

- `_resolve_op_reference` / `select_launch_secrets` / `build_launch_env` in
  `src/coga/config.py`.
- Sibling v2 ticket: `op-secret-dependency-init-enforcement`.
- 1Password service accounts: https://developer.1password.com/docs/service-accounts/

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
