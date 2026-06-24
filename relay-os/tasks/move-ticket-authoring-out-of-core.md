---
slug: move-ticket-authoring-out-of-core
title: Move ticket authoring out of core
status: draft
autonomy: interactive
owner: zach
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
secrets: null
step: 1 (design)
---

## Description

Move the `relay ticket` authoring logic out of the kernel so ticket-authoring
is itself a **ticket** (a stateless bootstrap ticket launched like any other),
not a built-in command. This is the real version of what the now-deleted
"tier-2 shim" gestured at, and the redo of closed PR 425. Shrinks the kernel
home, grows the tickets home.

## Context

Depends on the shim-concept removal landing first (`remove-the-shim-concept`)
so the model is clean. PR 425 attempted this and is being closed — redo from
scratch. Today `relay ticket` is a built-in (`src/relay/cli.py`,
`src/relay/commands/`), and the authoring interview is the `bootstrap/ticket`
skill. The `design` step decides the mechanism for collapsing a logic-bearing
built-in into a ticket (+ alias). The reasons `ticket` was a built-in rather
than a pure alias — draft-on-the-fly, post-exit validate, git-sync, TTY guard
(see `docs/cli-extension-audit.md`) — must be preserved in whatever shape the
design lands on. Keep `python -m pytest` green.

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
