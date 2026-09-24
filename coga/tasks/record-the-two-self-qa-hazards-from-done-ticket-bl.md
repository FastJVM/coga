---
title: Record the two self-QA hazards from done-ticket blackboards
status: draft
owner: nicktoper
agent: claude
contexts: []
skills: []
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: owner
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: report-to-coga
    skills: []
    assignee: agent
secrets: null
step: 1 (agent-produces)
---

## Description

Two self-QA hazards are recorded only in done-ticket blackboards, which Dream
deletes:

1. Stale worktree tickets — a ticket whose recorded checkout no longer exists
   or no longer matches the branch it names.
2. Simplifier coga side effects — the simplifier pass causing unintended coga
   state changes.

Give both a durable carrier, most likely a `code/self-qa` skill.

## Context

Raised by the Dream 2026-W36 knowledge scan (Phase 2, shard-01) as a `gap`.

Time pressure is real here: the source blackboards are on done tickets, and
Dream deletes an eligible done ticket in the same run that extracts from it.
Both source tickets currently carry a recorded feature checkout, so they are
retirement debt and survive until someone runs `coga retire` — but they will
not survive it. Capture the hazards before that happens.

<!-- coga:blackboard -->

## Production notes

Moved from FastJVM/multiply on 2026-09-24: filed there by Dream/autofix against coga itself (status there was `draft`; canceled in multiply as moved). Reset to `draft` for re-triage here. Paths, branches, worktrees and ticket slugs in the notes below refer to the multiply repo unless they say otherwise.


The blackboard is a notepad to be written to often as the human and agent works through a task.
