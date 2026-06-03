---
title: Verify relaunch chain terminal teardown
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: test/relaunch-chain
  steps:
  - name: draft
    skills: []
    assignee: agent
  - name: expand
    skills: []
    assignee: agent
  - name: peer-pass
    skills: []
    assignee: other-agent
  - name: human-check
    skills: []
    assignee: owner
  - name: finalize
    skills: []
    assignee: agent
step: 2 (expand)
---

## Description

Throwaway repro to confirm the `relay launch` auto-relaunch chain works
end-to-end **after the terminal-teardown fix (#274)** and the rotation-chain
behavior (#248). The deliverable is the observations in `## Relaunch test log`
on the blackboard, not `artifact.md` (that doc is just a vehicle so each step
has something to write).

The bug #274 fixed: when the supervisor SIGTERMs a TUI (claude/codex) on
`relay bump`, the killed TUI never restored its own terminal modes, leaving the
keyboard "dead" so the run looked hung. The fix emits a terminal reset after
teardown. **That symptom is human-observed** — the agent steps confirm the
chain relaunched; the human at the terminal confirms it stays usable.

## Context

### Current expected boundaries (resolved: agent→claude, other-agent→codex, owner→nick)

| boundary | transition | expected NOW |
| --- | --- | --- |
| draft → expand | claude → claude | **auto-relaunch** (same assignee) |
| expand → peer-pass | claude → codex | **auto-relaunch** (agent rotation — #248 chains rotations; the shared workflow file's table still says "stop", it is stale) |
| peer-pass → human-check | codex → nick | **stop** at the human gate — you `relay bump` then `relay launch` again |
| human-check → finalize | nick → claude | **stop** (resume after human) — you `relay launch` for finalize |

So one `relay launch verify-relaunch-chain-terminal-teardown` should
auto-chain **draft → expand → peer-pass** (claude → claude → codex, two
teardown+respawns) and stop at `human-check`. The human bumps + relaunches once
for `finalize`, which ends with `relay mark done`.

### Human watch (the #274 fix under test)

At every auto-relaunch (and the final `mark done`), the supervisor kills the
current TUI and you should see the next session — or your shell — come up with
a **working keyboard**: cursor visible, input echoes normally, no alt-screen
garble. A dead/garbled terminal after a bump is the regression. Note it in the
log if seen.

### Blackboard logging protocol

Each step appends a dated entry to `## Relaunch test log` on the blackboard
**before it bumps**, recording:

- which step/agent you are;
- whether you were **auto-relaunched by the supervisor or hand-launched by a
  human, and how you can tell** — anchor on ground truth (the process tree, and
  the `log.md` lines `started (active → in_progress) via relay launch` which
  fires only on a fresh human launch), not self-report;
- whether the previous step's REPL tore down cleanly;
- whether `assignee:` resolved to the expected agent;
- any errors / surprises.

`draft` is first, so its "previous teardown" item is N/A. `finalize` runs
`relay mark done` instead of `relay bump`.
