---
name: eval/ticket-diagnostic
description: Ticket evaluation tool
---

# Ticket diagnostic

The point is to spot blindspots before launch without changing anything.
Output: a diagnosis; the original ticket is not altered.

## Invocation

Always run via a fresh subagent.

> Execute the `eval/ticket-diagnostic` skill against
> `relay-os/tasks/<slug>/ticket.md`.

## Process
- Launch a Subagent

- Compose the ticket calling relay launch without launching it <<YOU NEED TO BE MORE SPECIFIC HERE>>

## Eval

This is what you want to evaluate the prompt against:

| Axis | What it checks |
| --- | --- |
| Objective | What this ticket is trying to do, stated plainly. |
| Done | Would two agents independently agree it's done? Implicit-but-unambiguous is fine. |
| Scope | What's in, what's out, what's adjacent-but-not. |
| Knowledge | Will the agent have what it needs — right contexts attached (and not bloated), key facts inlined in `## Context` when no context fits? |
| Workflow fit | Workflow matches the shape of the work — or absent when none is right. |
| Safety | For destructive / migration / rollout work: blast radius + rollback are clear. |

## Output

For each axis that gaps: a `### <Axis> — GAP` header, one or two
sentences naming the gap concretely, then one line starting
`Recommendation:` with one concrete edit the human could paste (body
line, context to attach, workflow swap, etc.). Axis order matches the
table above.

## Rules


- Recommendations must respect Relay tooling. Do not recommend
  hand-editing `status:` or `step:` — those are CLI-managed via
  `relay mark` and `relay bump`. Prefer body edits, context
  attachments, workflow swaps, or running a specific `relay`
  command (`relay mark <state>`, `relay bump`, `relay launch`, etc.).
- Recommendations must be grounded. Name only files, workflows,
  contexts, or commands that actually exist. Before suggesting
  `--workflow X` or `contexts: [X]`, verify `X` is in
  `relay-os/workflows/` or `relay-os/bootstrap/workflows/` (bundled
  batteries like `code/with-review` live under the latter), or in
  `relay-os/contexts/` or `relay-os/bootstrap/contexts/`. If nothing
  existing fits, recommend creating a new one and name the path it would
  live at (e.g. `relay-os/workflows/code/<name>.md`). Never invent
  plausible-sounding names from memory.
