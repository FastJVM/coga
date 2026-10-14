---
title: Triage inbound email
status: draft
owner: marc
agent: claude
contexts:
  - email/payment-flow
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - infra/testing-conventions
    assignee: agent
  - name: pr
    skills: []
    assignee: agent
  - name: approve
    skills: []
    assignee: owner
  - name: merge
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

Seeded example of a task nested one level inside a group directory
(`tasks/auto/`). Task discovery finds it by its bare leaf slug
(`triage-inbound-email`) exactly like a top-level task; the group
directory is organizational only.

## Context

Group a task by moving its directory under `tasks/<group>/` with
`git mv`. Slugs must stay unique across all groups — `coga validate`
reports a duplicate leaf name as an error.

<!-- coga:blackboard -->

# Triage inbound email

The blackboard is a notepad to be written to often as the human and agent
works through a task.

## Superseded designs

### 2026-09-18 — Flat task layout

Superseded by: Group inbound-email work under `tasks/auto/`.

Reason: Keep related tasks together without changing their lifecycle.

#### Prior shape

Place every inbound-email ticket directly in the top-level tasks directory.

## Handoff

Keep the grouped task layout described in the current body.
