---
name: human-only
description: Triage routes a task here when a machine can't do it reliably. The human performs it end to end; the agent only supports read-only and never touches the live system.
steps:
  - name: brief-and-hand-off
    assignee: agent
  - name: human-executes
    assignee: human
  - name: verify-read-only
    assignee: agent
---

## brief-and-hand-off

Using read-only, provide the human with — goal, ordered steps, the irreversible action, what done looks like — then hand off. Take no live action; feasibility was already settled at triage, so don't re-assess it.

## human-executes

The human does the whole task end to end and reports the result. The agent does not act.

## verify-read-only

Read the result back and confirm it matches the initial task, or flag the gap. No action. If the result can't be observed, the human's report stands.
