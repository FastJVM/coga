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
    assignee: owner
---

## second-step

Inline instruction for steps without a `skills:` ref. Body heading must
match the step name. One paragraph is plenty for inline instructions.

## last-step

Wrap-up. Run `coga bump <slug>` when the work is complete; because this is the
final step, the bump marks the ticket `done`.

## On `assignee:`

Each step's `assignee:` is a *role token* — `owner` | `agent` | `other-agent` —
not a literal nickname, and nothing is written to the ticket. The step's role is
what decides who holds the task; coga derives that operator on every read.

- `owner` is a human handoff, resolving to the ticket's `owner:`.
- `agent` is the ticket's own `agent:` — its main-agent choice.
- `other-agent` has no ticket field of its own: it resolves to the main agent's
  explicit `[agents.<type>].peer` when set, otherwise to the only other
  configured agent type. Two-agent repos need no extra config; three-agent repos
  declare the peer on each agent that uses this role. The mapping is
  one-directional, and an absent or ambiguous peer fails loud rather than
  guessing.

A step that omits `assignee:` inherits the nearest *preceding* declared role;
before any declaration the role is `owner`. That makes forward moves, restarts,
and human rewinds all derive the same answer from this frozen snapshot.
