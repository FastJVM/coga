---
slug: v2/relay-design-repositories
title: relay-design-repositories
status: paused
mode: agent
owner: zach
human: zach
agent: claude
assignee: nick
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (design)
---

## Description

Build a `relay design` command that interviews the operator and creates a
new repository from their answers. The interview elicits what the repo is
for (the direction it advances, not a deliverable to finish), the gap it
closes ("what doesn't exist today that this is trying to create?"), and
which existing skills and workflows the repo should lean on. From those
answers it creates the repo, records the framing as the repo's seed
context, and generates the first tickets from the gap.

## Context

Acceptance criteria attach to the generated tickets, not to the repository
— the repo is a direction, not a deliverable. Nearest existing patterns to
lean on: `relay init` already creates repos, and `bootstrap/ticket` already
runs an interview-and-create flow; this is closer to the latter applied at
repo scope.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
