---
title: Represent autonomy tier in ticket mode field
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

Give the autonomy tier a structured, first-class home in the ticket `mode`
field. Today `mode` is `interactive` / `auto` / `script` and describes how the
agent CLI process launches. The autonomy triage tier (conceptually `autonomous`
/ `human` / `human+ai`, sorting into the four `autonomy/` tier workflows) wants
to live here too. This ticket defines how the tier is represented in/alongside
`mode` and reconciles the two vocabularies.

Split out of `wire-autonomy-triage-into-impl-ready-workflows`, which wires
`autonomy/triage` into `bootstrap/ticket` at authoring time but deliberately
records the tier only advisorily (via the chosen workflow/assignees + the step-7
summary), with no structured field — because the structured representation is
this ticket.

## Context

Owner's taxonomy note (to design against, not yet documented elsewhere):
`script` = a launch; `auto` = script + `claude -p`. Verify the current live
state of `mode` handling in `src/relay/` before designing — an older note in the
`automation-triage` ticket claimed `mode: auto` was disabled/hard-bails, which
may be stale.

Touchpoints: `mode` parsing/validation in `src/relay/` (validate.py, launch.py,
task model), the `autonomy/triage` context and the four `autonomy/` tier
workflows, and the triage step added to
`relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md` by the predecessor ticket.

Needs a `bootstrap/ticket` interview to flesh out scope and pick a workflow
before it can be activated.
