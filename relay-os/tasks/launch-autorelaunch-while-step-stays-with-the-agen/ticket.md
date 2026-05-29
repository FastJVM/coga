---
title: 'launch: autorelaunch while step stays with the agent'
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: dev/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

Pair to the autoquit ticket. With autoquit working, an interactive
`relay launch` cleanly tears down the agent's REPL after `relay bump` /
`relay mark done` / `relay panic`. But the launch loop then exits to the
human's shell unconditionally (`src/relay/commands/launch.py` has an
`if mode == "interactive": break`). For workflows where the next step
is also the agent's, this means the human has to manually re-run
`relay launch <slug>` to continue — every step boundary becomes a
context-loss seam.

Goal: in interactive mode, after the agent exits, re-read the ticket
and decide:

- If status flipped to `done` / `paused` / anything not `in_progress` →
  stop, return to the caller.
- If the ticket directory was deleted → stop.
- If the agent exited without advancing the workflow (no bump, no mark
  done) → stop. Don't spin.
- If the next step's assignee resolves to a human (role `owner` or
  `human`, or a different nickname than the launching agent) → stop.
  Print a clear handoff line.
- Otherwise (next step is still the agent's) → loop. Re-compose the
  prompt for the new step, spawn a fresh REPL.

This is exactly what `_harness_stop_reason` already computes for auto
mode in `src/relay/commands/launch.py`. The minimal change is to drop
the `if mode == "interactive": break` line and let interactive runs go
through the same gate. Re-enable the `RELAY_SUPERVISED=1` env var so
`relay bump`'s existing hint about supervised chaining becomes accurate
again.

Out of scope:

- Re-enabling `mode: auto` (still disabled until the streaming consumer
  lands).
- Any change to `mode: script`.
- Cross-ticket chaining (that's `relay recurring --interactive`).

Done looks like: a multi-step interactive workflow where the agent
owns step 1 and step 2 advances from step 1 to step 2 in a single
`relay launch` invocation, with one REPL torn down and a fresh one
spawned for step 2. When the workflow reaches a human-assigned step
(`assignee: owner` review), the launch loop stops and returns to the
caller's shell.

## Context

Relevant code:

- `src/relay/commands/launch.py:262-369` — the loop. Drop the
  interactive-only `break`, set `RELAY_SUPERVISED=1` in the child env,
  update the comment block at lines 262-266 (currently says "no respawn
  on bump" — that's exactly what this ticket changes).
- `src/relay/commands/launch.py:_harness_stop_reason` — already
  computes the right answer; reuse as-is.
- `src/relay/commands/bump.py:131-149` — `RELAY_SUPERVISED` hint
  logic. With this ticket the env var is set, so the hint fires for
  real. With autoquit + autorelaunch the agent doesn't need to be
  told to exit; tighten or drop the hint.
- `tests/test_launch.py:test_launch_does_not_mark_interactive_session_supervised`
  — assertion needs to flip.

Design notes:

- The agent's `assignee` after bump is rewritten in
  `relay.bump.advance_step` only when the new step's role token
  resolves to a different nickname than the current `assignee`. So
  comparing `updated_ticket.assignee` against `launch_assignee` is
  sufficient to detect a handoff.

Tests:

- Flip the existing `test_launch_does_not_mark_interactive_session_supervised`.
- Add an interactive chain test: scaffold a 2-step workflow where
  step 1 advances to step 2 (same agent), assert the agent process
  was spawned twice.
- Add a handoff test: scaffold a 2-step workflow where step 2's
  assignee is `owner`, assert the agent process was spawned once and
  the loop stopped with the handoff message.

Verification:

- `python -m pytest tests/test_launch.py tests/test_repl_supervisor.py`
- Manual: launch a scratch ticket with two agent-owned steps; confirm
  one REPL ends and another comes up cleanly after `relay bump`.
