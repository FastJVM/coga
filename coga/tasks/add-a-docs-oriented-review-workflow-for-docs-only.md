---
slug: add-a-docs-oriented-review-workflow-for-docs-only
title: Add a docs-oriented review workflow for docs-only tickets
status: active
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

Found by the Dream run on 2026-06-18 (knowledge scan, gap finding G-NEW-3,
lower confidence).

Across multiple docs-only tickets (`improve-readme-and-doc`, `retire-mark-active`,
`v2/automerge-ticket`, and others), evaluators repeatedly flag that
`code/with-review`'s peer-review step (code diff review + `python -m pytest`) is
value-light for markdown/docs-only changes, yet no lighter docs-oriented review
workflow exists. The mismatch has recurred 3+ times.

This is a judgment call, hence a draft ticket rather than an auto-built
workflow: the team has tolerated the mismatch each time, so a human should
decide whether a dedicated `docs/with-review` (or similar) workflow is worth
adding, or whether the status quo is fine.

## Context

<!-- coga:blackboard -->
## Production notes

This blackboard is for active-work handoff notes. Authoring scratch was cleared at activation; durable requirements belong in the ticket body.
