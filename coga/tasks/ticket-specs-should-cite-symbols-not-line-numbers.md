---
slug: ticket-specs-should-cite-symbols-not-line-numbers
title: Ticket specs should cite symbols, not line numbers
status: in_progress
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

Source citations in a ticket body rot before the ticket is implemented, and three independent
tickets each hand-wrote their own warning about it because no skill carries the rule.
`launch-ignores-the-recorded-worktree-stranding-bla` opens its `## Context` with "Citations here
name **symbols, not line numbers**. An earlier draft pinned line numbers twice; both sets had
drifted within days."

Add the rule to `coga/skills/code/design/SKILL.md` and its packaged twin
`src/coga/resources/templates/coga/bootstrap/skills/code/design/SKILL.md` (edit both — they are a
synchronized pair).

## Context

Found by Dream 2026-08-24, Phase 2 knowledge scan — shard-03 and shard-05 reported this
independently from different evidence and were merged at reconciliation.

This run produced fresh evidence for it: Phase 3 shard ca-07 found `docs/cli-extension-audit.md`
citing a stale `cli.py:74-93` range for command registration, which had drifted exactly as
predicted.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
