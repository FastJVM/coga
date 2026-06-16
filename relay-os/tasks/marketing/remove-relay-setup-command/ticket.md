---
title: Remove relay setup command
status: in_progress
mode: interactive
owner: nick
human: zach
agent: claude
assignee: claude
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

Remove the `relay setup` command, but keep `relay init` auto-creating the
active `relay-setup` ticket. The first-run flow becomes: `relay init` → the
user sees `relay-setup` as their first task → launches it → the existing
interview gathers their contexts, skills, and workflows. Fewer commands to
learn, so new users reach value faster.

## Context

- `relay setup` lives in `src/relay/commands/setup.py`, registered at
  `src/relay/cli.py:74`. It was added together with the `relay-setup` ticket
  template and the `init/setup` workflow in PR #348 (`ba6ca2a3`) — only the
  **command** is being removed; the ticket and workflow stay.
- `relay init`'s next-steps output (`init.py:264–270`) points users at
  `relay setup`; redirect it to launching the relay-setup ticket. Note
  `relay setup` also captures the user's name (→ `user` in `relay.local.toml`),
  which the interview step expects already set — the design step should decide
  where that capture moves.
- Out of scope: shortening the interview itself (separate ticket).

