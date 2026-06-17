---
title: Fail loud when an env-indirected secret is missing instead of empty string
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

Priority: medium. Security/correctness footgun in the secrets path.

`_resolve_secrets` resolves `env:VAR` indirection by
`os.environ.get("VAR", "")` (`config.py:435`) — a **missing env var resolves to
an empty string, not an error**. The comment claims secrets are "validated at
launch time when needed," but no such validation exists: `launch.py:259-260`
just does `env.update(cfg.secrets)`, injecting the empty value. A typo like
`env:STRPE_KEY` silently injects an empty secret, and the downstream tool fails
later with a confusing, unrelated error.

This directly contradicts Relay's fail-loud principle. A declared secret that
points at an unset env var should be a hard, named error at the point of
resolution (or at launch, before the agent starts), not a silent empty string.

Fix: when an `env:VAR` indirection resolves to an unset variable, raise a clear
`ConfigError`/launch error naming both the secret key and the missing env var.
Consider a `relay validate` check that flags declared `env:` secrets whose
variables are unset in the current environment (warn, since env differs per
shell), and a hard fail at `relay launch`.

Acceptance: launching a task whose config declares `env:MISSING` exits non-zero
with a message naming the secret and the env var; no empty-string secret is ever
injected silently; covered by a config test.

## Context

Code: `src/relay/config.py` (`_resolve_secrets` ~424-435),
`src/relay/commands/launch.py:259-260` (secret injection). Also note
`extra_local` (`config.py:174`) silently retains arbitrary unknown local keys —
no typo protection there either; worth a warn in the same pass.
