---
name: your-namespace/your-workflow
description: One sentence — the create-suggest skill reads this to decide whether to attach this workflow to a new task.
steps:
  - name: first-step
    skill: your-namespace/some-skill   # optional — omit for inline-instruction steps
  - name: second-step
  - name: last-step
---

## first-step
(Optional — only needed if this step has no `skill:` ref. The body
heading must match the step name. One paragraph is plenty.)

## second-step
Inline instruction for the agent at this step. Use this for self-explanatory
work that doesn't justify a full skill file.

## last-step
Wrap-up. `relay step` past this step marks the task `done` and notifies
Slack — there's no need for an explicit "close" step.
