---
title: 'Scratch: verify autoquit marker'
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: scratch/autoquit
  steps:
  - name: run
    skills: []
---

## Description

Smoke test for the REPL autoquit machinery. No code to write, no PR to
open — the only point is to confirm that a supervised interactive launch
exits cleanly when the agent runs `relay mark done`.

Steps for the agent:

1. Write a single line to the blackboard saying "autoquit test ran at
   <UTC timestamp>".
2. Run `relay mark done scratch-verify-autoquit-marker`.
3. Stop. Do not type `/exit`. Do not emit the marker yourself — the
   commands do that.

If the supervisor is wired up correctly, the REPL will be SIGTERMed by
the `relay launch` parent shortly after `mark done` prints the marker,
and control will return to the human's shell without a manual `/exit`.

If after `mark done` the REPL just sits idle, the supervisor is not
running (or not matching the marker) — report that to the human and
stop.

## Context

Relevant code:

- `src/relay/repl_supervisor.py` — PTY watcher + `emit_done_marker`.
- `src/relay/commands/launch.py:335` — should now call
  `run_with_done_marker` for interactive launches.
- `src/relay/commands/mark.py:165` — calls `emit_done_marker` on
  `mark done` success.
