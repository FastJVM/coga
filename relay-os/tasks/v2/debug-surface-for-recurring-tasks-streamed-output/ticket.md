---
title: 'Debug surface for recurring tasks: streamed output + step-through'
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
  - name: open-pr
    skills:
    - code/open-pr
  - name: review
    skills: []
    assignee: owner
step: 1 (design)
---

## Description

Once recurring tasks are forced to `mode: auto`
(`enforce-mode-auto-for-recurring-templates`), the debug story is broken.
Today's modes force a tradeoff that does not work for iterating on Dream:

- `mode: auto` runs headless (`claude -p` / `codex exec`) and stdout buffers
  until completion (per `relay/cli`), so the human cannot watch the agent
  work in real time.
- `mode: interactive` streams, but the agent stalls on every free-form
  question — and it's now also banned on recurring templates.

We need a third operating mode for on-demand recurring runs (Dream first;
other recurring loops next). Requirements:

1. **Live console output.** Subprocess stdout streams to the human's terminal
   as the agent works. No buffering.
2. **Genuine interactivity.** The agent CAN still ask questions when it
   really needs human judgment (Dream's phases are not all deterministic —
   knowledge scan classification, contract audit, retro batching).
3. **Manual step-through.** Between Dream's six phases (and, more generally,
   between any well-defined agent checkpoints), the agent pauses and waits
   for the human to say "next" / "skip" / "abort" before continuing. This
   replaces the current behavior where the agent either barrels through or
   stalls on an ad-hoc question.

This is a `design-then-implement` ticket: settle the surface before coding.

### Open design questions

- **CLI shape.** `relay recurring launch <name> --debug`? `relay dream
  --debug`? A standalone `relay debug <slug>`? Should `--debug` also work on
  bare `relay launch` for non-recurring tasks?
- **Mode override.** Debug runs override the ticket's `mode: auto` for that
  one launch. Confirm this never touches `ticket.md` (precedent:
  `recurring --interactive` already promises "ticket files are not
  modified").
- **"Next" mechanism.** Three plausible shapes:
  1. **Agent-prompt convention.** The composed prompt teaches the agent to
     pause at phase boundaries and wait for the human to type a literal
     advance keyword (`/next`, `next`, etc.). Pure prompt change, no CLI
     surface, but relies on the agent following directions reliably.
  2. **Out-of-band signal.** A `relay next <slug>` (or SIGUSR1) command
     that the debug session listens for. Stronger separation but requires
     IPC plumbing.
  3. **Per-phase relaunch.** Each Dream phase is a separate `relay launch`
     invocation (script-mode child tasks already work this way for Phases
     1 and 5). The "step-through" is just the human running the next
     launch when ready. Simplest, but only fits Dream specifically.
- **Sweep interaction.** A debug launch from inside `relay recurring`
  probably should NOT continue the sweep on exit — debug is for one task at
  a time. Bare `relay recurring --debug` may be out of scope.
- **Output streaming for plain auto mode.** Is "stream stdout in auto mode"
  a separate concern worth doing unconditionally (not gated on `--debug`)?
  Buffered auto launches are a footgun for any operator running them
  in-terminal.

### Likely-touched files (post-design)

- `src/relay/commands/launch.py` — stdout streaming for the subprocess
  invocation; new `--debug` flag plumbing.
- `src/relay/commands/recurring.py` — `--debug` flag on `recurring launch`;
  remove or repurpose the existing `--interactive` flag on bare `recurring`.
- `relay-os/recurring/dream/ticket.md` and its packaged copy — explicit
  phase-pause markers if we go with shape (1).
- `relay-os/contexts/relay/cli/SKILL.md` and `relay/architecture/SKILL.md` —
  document the new surface and mode-override rule.
- Tests in `tests/` per the design choice.

## Context

Depends on `enforce-mode-auto-for-recurring-templates` landing first so the
problem space is well-defined (no live recurring templates running
`interactive` to muddy the design).
