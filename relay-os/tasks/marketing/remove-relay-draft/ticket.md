---
title: Remove the relay draft command
status: in_progress
mode: interactive
owner: zach
human: zach
agent: claude
assignee: codex
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
step: 2 (peer-review)
---

## Description

Remove the redundant `relay draft` command. `relay draft` and `relay create`
are parallel thin wrappers over the same `create_draft`/`create_task` path —
two names for "make a bare draft stub." Per the command-surface direction,
`relay draft` goes and `relay create` stays as the quick-stub path (with
`relay ticket` as the create-or-edit authoring entry point). Split out of
`marketing/relay-ticket-creates` so the relay-ticket authoring flow isn't held
up by this — it's a small, independent removal.

## Context

- `draft` and `create` are independent wrappers, both calling `create_draft` —
  `src/relay/commands/create.py` (`def draft` ~L24, `def create` ~L45, both →
  `create_draft` ~L66 → `create_task` in `src/relay/create.py`). So removing
  `draft` does not touch `create`.
- To remove: drop `app.command("draft")(create_cmd.draft)` (`src/relay/cli.py`
  ~L78) and `"draft"` from `_BUILTIN_COMMANDS` (~L104), and delete the `draft`
  function in `create.py`. Leave `create` and the soft-skipped legacy
  `create → launch bootstrap/ticket` entry in `_LEGACY_ALIASES` alone.
- Update the few references to `relay draft` while removing it — the
  `bootstrap/ticket` SKILL Step 1 ("Raw draft") and any README mention.
- nick owns these primitives.

