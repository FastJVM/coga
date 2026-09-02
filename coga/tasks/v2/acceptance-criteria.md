---
slug: v2/acceptance-criteria
title: acceptance-criteria
status: paused
owner: zach
human: zach
agent: claude
assignee: nicktoper
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

Create an acceptance criteria spot on relay tickets. The relay ticket interviewer should also have a question regarding the acceptance criteria (or the definition of done)

Possibly have a way to set acceptance criteria on relay create (ie relay create make-ticket -ac1 "create the ticket" --ac2 "commit the ticket" 

## Context

**Superseded by `the-ticket-interview-never-asks-what-done-means` (2026-09-01).**
That ticket now owns the whole acceptance-criteria question — the interview
question, the `## Acceptance Criteria` body section, whether `coga validate`
checks it, and the `coga create --ac1/--ac2` flag proposed above (it must decide
that flag explicitly, in or out). Everything here was folded into its
`## Context`. Do not work this ticket; close or cancel it once the successor
lands.

**Taken over by nicktoper on 2026-09-01** (was zach's). The `--ac1/--ac2` flag
call moves with it and is now decided in the successor ticket. Note the
`owner:`/`human:` frontmatter still reads `zach` — there is no CLI command to
reassign it, and those fields are not agent-editable, so a human needs to change
them by hand if the record should match.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
