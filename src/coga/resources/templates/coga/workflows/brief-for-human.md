---
name: brief-for-human
description: Human performs a task the machine cannot safely own; agent only provides read-only support.
steps:
  - name: brief-and-hand-off
    assignee: agent
  - name: human-executes
    assignee: human
  - name: verify-read-only
    assignee: agent
---

## brief-and-hand-off

Using read-only access, brief the human on the goal, ordered steps, irreversible
action, and done check. Then hand off. Take no live action.

## human-executes

The human does the whole task end to end and reports the result. The agent does
not act.

## verify-read-only

Read the result back and confirm it matches the initial task, or flag the gap.
No action. If the result can't be observed, the human's report stands.
