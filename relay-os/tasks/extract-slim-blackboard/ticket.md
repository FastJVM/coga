---
title: extract-slim-blackboard
status: draft
mode: interactive
owner: nick
human: nick
assignee: nick
---

## Description

Proposal to add a new workflow `extract-and-slim-blackboard` to
`relay-os/workflows/`. It promotes durable knowledge from a finished
task's blackboard into the right home (skill / context / workflow),
then slims the blackboard to status + pointers + pinned next-task
items. Goal of this ticket: Nick reads the proposed workflow file and
approves or denies.

## Context

- Workflow under review: `relay-os/workflows/extract-and-slim-blackboard.md` (added in this PR).
- Workflow shape conventions: `relay-os/workflows/_template.md` and the workflows section of `relay-os/contexts/relay/architecture/SKILL.md`.
- Single step, `assignee: agent` — intended to be attached at the end of other tickets' workflows, not run standalone.
