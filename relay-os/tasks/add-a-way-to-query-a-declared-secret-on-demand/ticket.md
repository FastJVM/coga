---
title: Add a way to query a declared secret on demand
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

**Concept-capture draft — shape not yet settled, deliberately workflow-less.**
Cannot be activated until a workflow is added and the shape below is pinned.

Third of the secrets-management split (sibling:
`fail-loud-when-an-env-indirected-secret-is-missing`, which adds the per-ticket
`secrets:` field + least-privilege injection + fail-loud). This ticket adds a
way to **query/retrieve** a declared secret on demand, rather than relying
solely on env-var injection at launch.

Open shape question (decide before activating):
- `relay secret get <key>` CLI subcommand that resolves and prints a secret's
  value (fail-loud if unset)?
- An in-process resolution helper agents/launch code call on demand?
- Both (CLI backed by a shared helper)?

Depends on the `secrets:` field from the sibling ticket landing first.

## Context

Code: secret resolution lives in `src/relay/config.py`
(`_resolve_secret_value` / `_resolve_secrets`, ~840-865). Whatever query
surface we build should reuse that resolution path (and the fail-loud behavior
the sibling ticket adds) rather than re-implementing env lookup.
