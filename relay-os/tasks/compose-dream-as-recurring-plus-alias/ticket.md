---
title: Compose Dream as a recurring task plus an alias
status: active
mode: interactive
owner: nick
human: nick
agent: claude1
assignee: claude1
contexts:
- relay/architecture
- relay/principles
- relay/cli
- relay/codebase
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
  - name: open-pr
    skills:
    - code/open-pr
  - name: review
    assignee: owner
step: 1 (implement)
---

## Description

Replace the standalone `relay dream` Typer command with a Dream
*recurring task definition* plus a `dream` alias in `relay.toml`.
Dream becomes a thing Relay scaffolds and launches like any other
recurring task — orchestrating skill-shaped child workers — not a
side-channel Python entrypoint.

Why: per the dream-5 architectural correction, Dream is a parent
task whose job is to scaffold and bump child `mode: script` tasks
over the worker skills. Once those workers are skills (sibling
ticket `make-dream-workers-skills-only`) and `relay delete` is a
skill (sibling ticket `move-relay-delete-into-a-skill`), there is
nothing left in `src/relay/commands/dream.py` worth keeping —
everything it does should be expressible as a recurring task body
plus an alias.

This also restores the earlier shape (commit `7cf06b6` — "Use
recurring system for manual Dream triggering") which `ce67296`
("Add ad-hoc Dream command") replaced. The right answer is
recurring + alias, not a dedicated command.

## Proposed Shape

- New recurring template at `relay-os/recurring/dream.md` (name TBD).
  Body composes the worker skills as the orchestration plan: for
  each known worker, scaffold a child `mode: script` task, launch
  it, summarize its blackboard back into the parent's blackboard.
  Final parent step is the agent-judgment phase.
- `[aliases] dream = "..."` in `relay.toml` — expansion TBD during
  implement. Likely `recurring scaffold dream` or equivalent;
  depends on the recurring CLI surface and whether ad-hoc manual
  triggering needs a different verb than the cron path. Decide and
  document.
- Remove `src/relay/commands/dream.py` and the `relay dream`
  registration. The alias is the only entrypoint.
- `relay-os/scripts/cron.sh` (if present) and `relay recurring check`
  pick up `dream.md` like any other recurring template — same code
  path that already scaffolds REM and others.

## Acceptance Criteria

- No `src/relay/commands/dream.py` (and no `relay dream` Typer
  registration). Grep proves it.
- `relay-os/recurring/dream.md` exists and scaffolds correctly via
  `relay recurring check`.
- `[aliases].dream` resolves to the same scaffold path that the
  recurring scheduler uses, so a manual `relay dream` and a cron
  `relay recurring check` produce equivalent task directories.
- One end-to-end test: invoke `relay dream` (the alias), confirm a
  parent task is scaffolded, confirm child `mode: script` tasks
  for each known worker skill are scaffolded and launched, confirm
  the parent blackboard receives summaries before the parent agent
  phase.
- `relay/cli` context updated: `relay dream` description points at
  the alias + recurring template, not a built-in command. The
  "manual cleanup runs" sentence in the existing context is
  rewritten to match.
- `relay/architecture` context picks up: "Dream is a recurring task
  template plus an alias; the parent task orchestrates child
  `mode: script` tasks over worker skills."
- `docs/spec.md` updated where it documents the `dream` surface.

## Out Of Scope

- Building or rewriting the worker skills themselves — that's
  `make-dream-workers-skills-only`. This ticket assumes the skills
  exist.
- Building the delete skill — that's
  `move-relay-delete-into-a-skill`. Workers that need to delete go
  through whatever public surface that ticket lands.
- Inventing a new recurring CLI verb. Use what exists; if a gap
  appears, write it up here and either extend scope explicitly or
  carve a follow-up — don't grow scope silently.

## Sequencing

This ticket lands *after* the other two in the split. It's the
composition step:

1. `move-relay-delete-into-a-skill` — public delete surface lands.
2. `make-dream-workers-skills-only` — workers become skills,
   consume the delete surface from #1.
3. *this ticket* — Dream becomes a recurring template + alias that
   composes #2's skills.

Don't merge this ticket's PR ahead of #2 — the recurring template
references skills that #2 ships.

## Context

Sibling tickets:

- `move-relay-delete-into-a-skill`
- `make-dream-workers-skills-only`

Background: `relay-os/tasks/dream-5/ticket.md` is the combined
parent. The `## Correct Model` section there is the most
authoritative description of Dream-as-orchestrator; read it
before coding.
