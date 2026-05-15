---
name: extract-and-slim-blackboard
description: Promote durable knowledge from a finished task's blackboard into the right home (skill / context / workflow), then slim the blackboard to status + pointers + pinned next-task items.
steps:
  - name: extract-and-slim-blackboard
    assignee: agent
---

## extract-and-slim-blackboard

Read the task's `blackboard.md`. For each section, decide whether the
content is durable knowledge that another task could reuse:

- **Facts about the world** (URLs, schemas, observed behaviors, auth
  flows, DOM anatomy) → promote to a context under
  `relay-os/contexts/<ns>/<name>/SKILL.md`.
- **A reusable recipe / protocol / output contract** → promote to a
  skill under `relay-os/skills/<ns>/<name>/SKILL.md`.
- **A reusable process the agent runs across tasks** → promote to a
  workflow under `workflows/<name>.md`.

After each promotion, remove the corresponding content from the
blackboard and replace it with a pointer to the new home (e.g.,
`see [[xero/dom]]`).

When the extract pass is done, slim the blackboard a second time
asking "what does the *next task on this thread* need from this
blackboard?" Keep that. Drop the rest. The blackboard's surviving
sections should typically be:

- a short status / outcome line,
- a "what lives where" pointer list,
- pinned-for-next-task items (open questions, unverified
  assumptions, known gotchas).
