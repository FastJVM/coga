---
name: eval/ticket-diagnostic
description: Cold-read diagnostic for a Relay ticket. A fresh subagent reads the ticket and its full prompt payload, scores it against six Relay-native axes (objective, done, scope, knowledge, workflow fit, safety), and prints a gap report with concrete recommendations. Silent on pass. Never writes to disk — the human decides what to apply.
---

# Ticket diagnostic

Cold-read second opinion on a freshly-bootstrapped ticket. The point is
to spot blindspots before launch without changing anything — the human
decides what (if any) of the recommendations to apply.

## Invocation

Always run via a fresh subagent so the diagnostic isn't biased by the
session that created the ticket. Claude Code: `Agent` tool,
`subagent_type: general-purpose`. Codex: `codex exec`. Prompt:

> Execute the `eval/ticket-diagnostic` skill against
> `relay-os/tasks/<slug>/ticket.md`.

## Process

Read the ticket and every file its frontmatter references — that's
the full prompt payload the implementer will receive: paths under
`contexts:`, the workflow file under `workflow:`, and sibling
`blackboard.md` / `log.md` if present. Then score that payload against
the six axes below. PASS = an implementer can act without fabricating.
GAP = they'd have to guess, ask, or risk a wrong-direction commit.

## Axes

| Axis | What it checks |
| --- | --- |
| Objective | What this ticket is trying to do, stated plainly. |
| Done | Would two agents independently agree it's done? Implicit-but-unambiguous is fine. |
| Scope | What's in, what's out, what's adjacent-but-not. |
| Knowledge | Will the agent have what it needs — right contexts attached (and not bloated), key facts inlined in `## Context` when no context fits? |
| Workflow fit | Workflow matches the shape of the work — or absent when none is right. |
| Safety | For destructive / migration / rollout work: blast radius + rollback are clear. |

## Output

If every axis passes, output nothing. Silent = PASS.

For each axis that gaps: a `### <Axis> — GAP` header, one or two
sentences naming the gap concretely, then one line starting
`Recommendation:` with one concrete edit the human could paste (body
line, context to attach, workflow swap, etc.). Axis order matches the
table above.

## Rules

- Cold read. The output is the only artifact — don't ask the human anything.
- Never write to disk. The human decides whether to apply any recommendation.
- A Relay ticket body is what + why only. If the body contains phase
  plans, command syntax, output contracts, or implementation-step
  checklists, flag it under the most relevant axis and recommend
  moving it to `blackboard.md`, the workflow, or a skill. A short
  success-criteria list is fine — that's the spec, not a plan.
- Recommendations must respect Relay tooling. Do not recommend
  hand-editing `status:` or `step:` — those are CLI-managed via
  `relay mark` and `relay bump`. Prefer body edits, context
  attachments, workflow swaps, or running a specific `relay`
  command (`relay mark <state>`, `relay bump`, `relay launch`, etc.).
- Recommendations must be grounded. Name only files, workflows,
  contexts, or commands that actually exist. Before suggesting
  `--workflow X` or `contexts: [X]`, verify `X` is in
  `relay-os/workflows/` or `relay-os/contexts/`. If nothing existing
  fits, recommend creating a new one and name the path it would live
  at (e.g. `relay-os/workflows/code/<name>.md`). Never invent
  plausible-sounding names from memory.
