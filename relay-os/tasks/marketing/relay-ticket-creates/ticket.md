---
title: relay-ticket-creates
status: active
mode: interactive
owner: zach
human: zach
agent: claude
assignee: nick
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

Make `relay ticket` the single entry point for ticket creation: it creates
the draft and then runs the `bootstrap/ticket` authoring prompt, replacing
`relay draft` and `relay create` (both removed). After creating a draft it
asks a simple yes/no — "Add description to ticket now?" — launching the
authoring interview on yes and leaving a bare draft on no. Running
`relay ticket <slug>` again on an existing draft re-enters the description
process for that ticket.

## Context

`relay ticket <title>` already creates a draft and launches the
`bootstrap/ticket` interview (`src/relay/commands/ticket.py`), and re-running
it on an existing draft slug already re-enters authoring. The new work is
(a) the yes/no gate so creation-without-interview is first-class, and
(b) removing `relay draft` and `relay create` — thin wrappers over
`create_task` (`src/relay/commands/create.py`, `src/relay/create.py`) — so
`relay ticket` is the sole creation path. Prior direction kept `relay create`
as the survivor; nick owns these primitives, so the design step should settle
removal-vs-deprecation and the exact defer/re-run UX. No y/n confirm helper
exists yet (CLI uses `typer.prompt`).

