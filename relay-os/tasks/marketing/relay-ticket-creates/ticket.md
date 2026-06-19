---
title: relay-ticket-creates
status: active
mode: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (design)
---

## Description

`relay ticket` is the create-or-edit authoring entry point; `relay create` is
the quick placeholder; `relay draft` is removed. `relay ticket <title>` creates
a draft and immediately runs the `bootstrap/ticket` authoring interview — no
yes/no prompt: running `relay ticket` *is* the signal you're ready to author (if
you only want a bare stub, run `relay create`). `relay ticket <slug>` on an
existing ticket re-enters authoring (edit).

## Context

`relay ticket <title>` already creates a draft and launches the
`bootstrap/ticket` interview (`src/relay/commands/ticket.py`), and re-running it
on an existing slug already re-enters authoring — so the create-or-edit behavior
largely exists today, with no yes/no gate (running `relay ticket` is the intent
signal). The remaining work is removing `relay draft` — a thin wrapper over
`create_task` (`src/relay/commands/create.py`, `src/relay/create.py`);
`relay create` stays as the quick stub (owner decision). nick owns these
primitives. Open for the design step: whether `relay create` shares the creation
code path with `relay ticket`, and the exact re-run/edit UX.

