---
name: _template
description: Starter workflow. Copy this file to workflows/<namespace>/<your-workflow>.md and edit the steps to match your process.
steps:
  - name: first-step
    skills:
      - namespace/some-skill
    assignee: agent
  - name: second-step
    assignee: agent
  - name: last-step
    assignee: human
---

## second-step

Inline instruction for steps without a `skills:` ref. Body heading must
match the step name. One paragraph is plenty for inline instructions.

## last-step

Wrap-up. Run `coga bump <slug>` when the work is complete; because this is the
final step, the bump marks the ticket `done`.

## On `assignee:`

Each step's `assignee:` is a *role token* — `owner` | `human` | `agent` |
`other-agent` — not a literal nickname. On bump, coga reads the ticket's
matching role field (`owner:`, `human:`, `agent:`) and rewrites `assignee:`
to that nickname. `other-agent` has no ticket field of its own: it resolves
to the ticket agent's explicit `[agents.<type>].peer` when set, otherwise to
the only other configured agent type. Two-agent repos need no extra config;
three-agent repos declare the peer on each agent that uses this role. The
mapping is one-directional, and an absent or ambiguous peer fails loud rather
than guessing. Steps that omit `assignee:` leave the assignee unchanged.
