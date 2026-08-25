---
slug: document-the-ticket-blackboard-writer-s-contract
title: Document the ticket-blackboard writer's contract
status: draft
owner: nicktoper
human: nicktoper
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
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

Nothing in `coga/contexts/` or `coga/skills/` states the contract for *writing* to a ticket
blackboard. `coga/contexts/coga/architecture/SKILL.md` defines what the `<!-- coga:blackboard -->`
fence is, and stops there. Three tickets in the recurring area each hit a different way of
corrupting a blackboard while writing to it, and each had to re-derive the rules.

Decide whether this belongs in `coga/architecture` (next to the fence definition) or in a new
context, then write the rules down: append vs rewrite, what may edit the region above the fence,
how concurrent writers interact, and what happens to a section a later pass rewrites.

## Context

Found by Dream 2026-08-24, Phase 2 knowledge scan (shard-09), classified `gap`.

This run hit the failure itself: an operator dedup of a duplicated recipe section matched a
mention of the same heading in the ticket *body* and truncated 258 lines of the body. It was
recoverable only because the recipe auto-commits. That is exactly the class of mistake a written
writer's contract prevents.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
