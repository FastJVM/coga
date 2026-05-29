---
title: 'Scratch: verify autorelaunch chain'
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow:
  name: scratch/autorelaunch
  steps:
  - name: step-one
    skills: []
    assignee: agent
  - name: step-two
    skills: []
    assignee: agent
  - name: review
    skills: []
    assignee: owner
---

## Description

Smoke test for the autorelaunch chain. No code, no PR. The point is to
prove that a single `relay launch` invocation drives the agent through
two consecutive agent-owned workflow steps, with one REPL torn down and
a fresh one spawned between them, and then stops cleanly when the
workflow hits a human-assigned step.

Instructions for the agent each turn:

1. Read the current `step:` from the ticket frontmatter
   (`relay show scratch-verify-autorelaunch-chain` or just look).
2. Append one line to the blackboard: "<step name> ran at <UTC
   timestamp>".
3. Run `relay bump scratch-verify-autorelaunch-chain`.
4. Stop. Do not type `/exit`. Do not emit any marker yourself.

If the supervisor + chain are wired up:

- After step 1's bump, the REPL is SIGTERMed by the supervisor.
- `relay launch` re-reads the ticket, sees step 2 is still the agent's
  (assignee resolves to `claude`), composes a fresh prompt, spawns a
  new REPL.
- After step 2's bump, the REPL is SIGTERMed again.
- `relay launch` sees step 3 (`review`) is the owner's — stops the
  loop, returns control to your shell.

Expected blackboard at the end: two lines, one per step. Expected
ticket: `status: in_progress`, `step: 3 (review)`, `assignee: nick`.

If after step 1's bump no new REPL spawns, autorelaunch isn't engaging.
If the loop continues past step 3, the handoff check isn't firing.
Either is a regression — report and stop.

## Context

Relevant code:

- `src/relay/commands/launch.py` — the chain loop and `_harness_stop_reason`.
- `src/relay/commands/bump.py` — emits the supervisor signal and
  advances `step:` / `assignee:`.
- `src/relay/repl_supervisor.py` — sentinel-file teardown channel.
