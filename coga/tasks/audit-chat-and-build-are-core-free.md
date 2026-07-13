---
slug: audit-chat-and-build-are-core-free
title: Audit chat and build are core-free
status: done
mode: agent
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
---

## Description

Confirm the `chat` and `build` default aliases are pure argv sugar with no
residual kernel logic, and remove any core handling if present. Both already
look alias-only, so this is most likely a verification that closes with a
finding rather than a code change. Part of the "move things out of core"
program.

## Context

`chat` and `build` ship as default aliases in `src/relay/cli.py`
`_DEFAULT_ALIASES` (`chat` → `launch bootstrap/orient`; `build` is also listed
among the aliases in `relay-os/contexts/relay/extension-model/SKILL.md`). For
each: verify it round-trips purely through alias expansion with no special-case
core code, and if already clean, close with that finding. Depends on the
shim-concept removal landing first (`remove-the-shim-concept`). (`dream` is also
a default alias if you want the same check applied to it.)

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

- No feature branch/worktree or code commit created. The implementation audit found the requested behavior already satisfied, so there is no code diff to review.

## Findings

- `chat` and `build` are pure default aliases in `src/coga/cli.py`, not built-in commands.
- `_BUILTIN_COMMANDS` contains no `chat` or `build`; `_DEFAULT_ALIASES` maps `chat` -> `launch bootstrap/orient` and `build` -> `launch coga-build`.
- Alias execution is one path for every alias: `main()` validates the merged default/user alias map, registers help placeholders, then rewrites `sys.argv` to `expansion + rest` before Typer dispatch. There is no pre/post hook specific to `chat` or `build`.
- The durable extension-model docs agree: aliases are only fixed `launch X` / `recurring launch X` argv sugar with no logic on either side; `chat`, `dream`, and `build` are classified as alias sugar.
- Existing regression coverage already proves both default aliases dispatch without a user `[aliases]` section: `test_default_chat_alias_dispatches_without_user_aliases_section` and `test_default_build_alias_dispatches_without_user_aliases_section`.

## Verification

- `PYTHONPATH=/home/n/Code/codex/coga/.coga/worktrees/c4e3cf962ec7469ba1e25adef0fe8a9a/src python3.12 -m pytest -q tests/test_aliases.py` -> 20 passed.
- `PYTHONPATH=/home/n/Code/codex/coga/.coga/worktrees/c4e3cf962ec7469ba1e25adef0fe8a9a/src python3.12 -m pytest` -> 1072 passed, 1 skipped.

## Decision

- Close as already satisfied/no-op. There is no residual core handling to remove for `chat` or `build`.

## Usage

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":2328320,"cli":"codex","input_tokens":286841,"model":"gpt-5.5","output_tokens":15403,"provider":"openai","schema":1,"session_id":"019f33f8-d4a0-7230-bb6f-85e12d123f1d","slug":"audit-chat-and-build-are-core-free","step":"implement","title":"Audit chat and build are core-free","ts":"2026-07-05T20:37:54.568328Z","usage_status":"ok"}
