---
title: Implement retro done-ticket Dream worker
status: active
mode: interactive
owner: nick
human: nick
agent: claude1
assignee: nick
contexts:
- relay/architecture
- relay/principles
- relay/codebase
- relay/current-direction
- relay/project-stage
workflow:
  name: code/with-review
  steps:
  - name: implement
    skill: code/implement-and-pr
  - name: review
step: 2 (review)
---

## Description

Implement the first Dream worker: retro extraction for one done ticket.

The worker should read a done ticket's `ticket.md`, `blackboard.md`, and
`log.md`, extract durable lessons into contexts, skills, or workflows, and
delete the task directory in the same reviewable PR. Git history is the archive
after useful knowledge has been lifted out.

## Context

Parent ticket: `relay-os/tasks/add-bootstrap-retro-skill-for-knowledge-extraction/`.

This is the core cleanup story for done tickets. The deletion is not the point;
the point is preserving useful knowledge before the directory disappears.

## Acceptance criteria

- [ ] A `dream/tasks/retro-done-ticket` worker exists.
- [ ] The worker accepts exactly one done ticket as its unit of work.
- [ ] The worker proposes or applies context/skill/workflow updates based on
      ticket evidence.
- [ ] The worker deletes `relay-os/tasks/<slug>/` in the same PR as any
      extracted knowledge.
- [ ] The PR body links back to the source ticket through a git ref or other
      durable identifier.
- [ ] The worker no-ops on non-done tickets.
- [ ] The worker leaves enough blackboard/Slack summary for a human to review
      what was extracted and what was intentionally dropped.
