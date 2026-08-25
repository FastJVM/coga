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
to the *peer* agent, the configured `[agents.*]` type that is not the
ticket's `agent:`, which is how the shipped `code/*` workflows hand a
review step to the agent that did not write the change. That resolution
needs **exactly two** configured `[agents.*]` types, with the ticket's
`agent:` as one of them — the peer is only unambiguous when exactly one
candidate remains. With one type, or three or more, the bump fails loud
rather than guessing; fix `coga.toml` or the ticket's `agent:` if you hit
that. Steps that omit `assignee:` leave the assignee unchanged.
