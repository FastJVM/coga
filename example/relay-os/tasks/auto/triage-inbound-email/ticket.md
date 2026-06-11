---
title: Triage inbound email
status: draft
mode: interactive
owner: marc
human: marc
agent: claude
assignee: claude
contexts:
  - email/payment-flow
skills: []
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
    assignee: human
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
`git mv`. Slugs must stay unique across all groups — `relay validate`
reports a duplicate leaf name as an error.
