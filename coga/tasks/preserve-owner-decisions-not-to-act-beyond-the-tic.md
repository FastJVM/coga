---
title: Preserve owner decisions not to act beyond the ticket that recorded them
status: draft
owner: nicktoper
agent: claude
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
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

Dream 2026-W35 knowledge-scan finding G2.

Owner decisions *not* to act survive only in the body of the ticket that
recorded them, and the lifecycle retires those tickets. The live example is
`decide-whether-to-keep-imported-google-agents-cli`: it was canceled without
its outcome landing in any context, so the same question is being re-raised
now (see `decide-the-fate-of-the-imported-google-agents-cli`).

A canceled ticket is not a Retro candidate -- Phase 4 only processes `done`
tickets -- so a "we looked at this and chose not to act" decision has no path
into durable knowledge at all today.

## Context

Decide where a no-action decision should land (a decision-register context,
a `## Decision` section the cancel path preserves, or a Retro rule that also
reads canceled tickets), then implement it. Relates to the existing draft
`add-decision-register-authoring-style-context`.
<!-- coga:blackboard -->

## Production notes

Moved from FastJVM/multiply on 2026-09-24: filed there by Dream/autofix against coga itself (status there was `draft`; canceled in multiply as moved). Reset to `draft` for re-triage here. Paths, branches, worktrees and ticket slugs in the notes below refer to the multiply repo unless they say otherwise.


The blackboard is a notepad to be written to often as the human and agent works through a task.
