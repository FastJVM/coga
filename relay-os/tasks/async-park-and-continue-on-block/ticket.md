---
title: Async park-and-continue on block
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
  - relay/architecture
  - relay/cli
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

When an unattended (overnight/auto) ticket hits a blocker, it should **park the
question and let the sweep keep going** — not stall the whole run waiting on a
human who is asleep. The motivation is token utilization: one blocked ticket
must not idle the rest of the night.

The chosen model is **clean async park**, not a live waiting terminal (owner
decision). It leans on Relay's existing stateless-session property: the prompt
is a pure function of the files on disk, so a parked ticket can be reconstructed
and resumed later with no live process held open.

Behavior:

1. **Park** — on a blocker, the agent writes the specific question/blocker to
   the blackboard (working section) and calls `relay panic` so it posts to
   Slack naming the owner with the blocker reason and the action needed. (Today
   panic already leaves the ticket `in_progress` and writes a `PANIC` marker —
   build on that, don't reinvent it.)
2. **Keep sweeping** — the recurring/drain sweep advances to the next ready
   ticket instead of aborting the remaining queue when a ticket parks. Confirm
   and, if needed, fix that a panic/non-zero exit from one task does not bail
   the rest of the sweep.
3. **Resume on answer** — define the handshake: once the human answers (edits
   the blackboard / clears the block), the next `relay launch` / sweep resumes
   the parked ticket from its current step, reading the answer out of the
   blackboard. No live terminal, no nested session.

Pairs with `issue-inbox-slack` (panics carrying the blocker reason + required
action + a link to the next command) — the park message should be readable and
actionable straight from Slack.

## Context

This refines the panic/escalation model, so respect its current invariants
(see the base prompt + `relay/cli`): panic is the blocker channel (not routine
handoff), and agents do not launch nested sessions. The change is "park cleanly
and let the sweep continue + resume statelessly," **not** "keep trying after a
panic." Read `relay/architecture` on stateless sessions and the recurring
sweep's sequential, one-live-task-per-template behavior before changing the
sweep loop (`src/relay/commands/recurring.py`).
