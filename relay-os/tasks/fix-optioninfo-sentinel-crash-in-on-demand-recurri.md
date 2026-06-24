---
slug: fix-optioninfo-sentinel-crash-in-on-demand-recurri
title: Fix OptionInfo sentinel crash in on-demand recurring launchers
status: draft
autonomy: interactive
owner: nick
human: nick
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

Found by the Dream run on 2026-06-18 (knowledge scan, gap finding G-NEW-2).
Reproduced in the `marketing/relay-build-command` blackboard but never filed.

`recurring._launch_created` (`src/relay/commands/recurring.py`, ~line 498) omits
`idle_timeout`/`max_session` when launching, so those arrive as Typer
`OptionInfo` sentinel objects. `repl_supervisor` (`src/relay/repl_supervisor.py`,
~line 286) then evaluates `float >= OptionInfo` → `TypeError`, crashing the
**on-demand** TTY launchers: `relay dream` (= `relay recurring launch dream`)
and `relay recurring launch <x>`.

The scheduled bare `relay recurring` sweep sets the timeouts explicitly, so only
the on-demand paths break. This directly threatens the `relay dream` entry point
that Dream itself documents.

Fix direction: pass concrete `idle_timeout`/`max_session` defaults (or resolve
the sentinels) in `_launch_created` so on-demand launches match the swept path.
Confirm the exact line numbers/signature before implementing — they were
reported by a scan, not yet verified against current source.

## Context

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
