---
slug: v2/document-interactive-recurring-sweep-hazard-in-rel
title: Document interactive-recurring sweep hazard in coga/recurring context
status: draft
mode: llm
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
step: 1 (implement)
---

## Description

Surfaced by Dream (dream-dbg-20260608T120715) Phase 2 knowledge scan as a `gap`.

**The gap.** A `mode: interactive` recurring template breaks the headless
`relay recurring` sweep: the sweep runs with no human at the keyboard, so an
interactive agent stalls on free-form questions, and the
`_stop_if_unfinished_after_launch` guard then bails before the next due
template ("the interactive task never exits, the sweep never advances"). This
hard-won operational fact is documented across three tickets
(`enforce-mode-auto-for-recurring-templates`,
`stream-agent-progress-in-auto-mode-and-recurring-l`,
`debug-surface-for-recurring-tasks-streamed-output`) and is actively
reproduced by Dream's own shipped `relay-os/recurring/dream/ticket.md`
(`mode: interactive`). Yet no context carries the constraint:
`relay-os/contexts/relay/recurring/SKILL.md` documents the `mode` field as
"`script`, `auto`, or `interactive`. Defaults to `auto`" with no warning.

**Why a ticket, not an immediate context PR.** The resolution is in flux and
contested between two open tickets, so the documentation shouldn't be written
until the mode story lands:
- `enforce-mode-auto-for-recurring-templates` proposes rejecting `interactive`
  at load time (which would moot a "don't use interactive" warning).
- `debug-surface-for-recurring-tasks-streamed-output` proposes a future third
  mode for recurring tasks.

**Suggested resolution.** Once those land, add one short note to
`relay/recurring`'s `mode` field doc capturing the constraint (and reconcile
Dream's own template if `interactive` is rejected at load). If the
maintainers decide `enforce-mode-auto-for-recurring-templates` fully covers
this, close as a duplicate — this ticket is a tracked home for the constraint,
not a mandate to add prose that the enforcement work would contradict.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
