---
slug: audit-chat-and-build-are-core-free
title: Audit chat and build are core-free
status: in_progress
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
step: 1 (implement)
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
