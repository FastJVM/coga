---
slug: give-a-ticket-s-superseded-design-one-documented-h
title: Give a ticket's superseded design one documented home
status: active
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

When a ticket pivots, its `## Description` is rewritten and the abandoned direction is preserved
somewhere — but nothing documents where, so each author picks a different shape and later readers
cannot tell a live plan from a dead one. Three independent tickets in one Dream shard used three
different headings for the same thing.

Pick one convention and write it into `coga/contexts/dev/code/SKILL.md` or a new
blackboard-conventions context.

## Context

Found by Dream 2026-08-24, Phase 2 knowledge scan (shard-12), classified `gap`.

Related: `v2/document-design-pivot-in-blackboard-convention` is a parked draft on the same subject —
check it for premise before starting, and fold it in or cancel it.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
