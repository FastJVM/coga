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

Make `relay ticket` the primary create-or-edit entry point: `relay ticket
<title>` creates a draft and then asks a simple yes/no — "Add description to
ticket now?" — launching the `bootstrap/ticket` authoring interview on yes and
leaving a bare draft on no. Running `relay ticket <slug>` again on an existing
ticket re-enters the description process (edit). This replaces `relay draft`
(removed); `relay create` stays as the quick-stub creation path (owner
decision — not removed).

## Context

`relay ticket <title>` already creates a draft and launches the
`bootstrap/ticket` interview (`src/relay/commands/ticket.py`), and re-running
it on an existing draft slug already re-enters authoring. The new work is
(a) the yes/no gate so creation-without-interview is first-class, and
(b) removing `relay draft` — a thin wrapper over `create_task`
(`src/relay/commands/create.py`, `src/relay/create.py`). `relay create` stays
(owner decision): `relay ticket` is the primary create-or-edit path, `relay
create` the quick stub. nick owns these primitives. Open for the design step:
the exact defer/re-run UX and whether `relay create` shares the creation code
path with `relay ticket`. No y/n confirm helper exists yet (CLI uses
`typer.prompt`).

