---
name: _template
description: Starter workflow. Copy this file to workflows/<namespace>/<your-workflow>.md and edit the steps to match your process.
steps:
  - name: first-step
    skill: namespace/some-skill
    assignee: agent
  - name: second-step
    assignee: agent
  - name: last-step
    assignee: human
---

## second-step

Inline instruction for steps without a `skill:` ref. Body heading must
match the step name. One paragraph is plenty for inline instructions.

## last-step

Wrap-up. `relay bump` stops at the last step; finish with
`relay mark done <slug>` when the work is complete.

## On `assignee:`

Each step's `assignee:` is a *role token* (`owner` | `human` | `agent`),
not a literal nickname. On bump, relay reads the ticket's matching role
field (`owner:`, `human:`, `agent:`) and rewrites `assignee:` to that
nickname. Steps that omit `assignee:` leave the assignee unchanged.
