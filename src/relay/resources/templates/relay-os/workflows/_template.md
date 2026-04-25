---
name: _template
description: Starter workflow. Copy this file to workflows/<namespace>/<your-workflow>.md and edit the steps to match your process.
steps:
  - name: first-step
    skill: namespace/some-skill
  - name: second-step
  - name: last-step
---

## second-step

Inline instruction for steps without a `skill:` ref. Body heading must
match the step name. One paragraph is plenty for inline instructions.

## last-step

Wrap-up. `relay step` past the last step marks the task `done` and
notifies Slack — no explicit "close" step is needed.
