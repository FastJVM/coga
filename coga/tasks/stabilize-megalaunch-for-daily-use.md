---
slug: stabilize-megalaunch-for-daily-use
title: Stabilize megalaunch for daily use
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
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
secrets: null
script: null
step: 1 (implement)
---

## Description

Make `coga megalaunch` reliable enough to be the default daily work mode for
two consecutive weeks — the hard prerequisite for the
`marketing/launch-20-minutes-a-day` experiment.

**Acceptance criterion:** megalaunch drains the real backlog daily for two
weeks without wedging, silently stalling, or corrupting task state; a wedged
REPL never starves the queue (liveness backstops verified in practice, not
just configured).

Scope:

1. **Enumerate the known instabilities** (owner: nick knows the current
   failure modes from the July 1–2 burst — capture them on this blackboard
   first, then fix in order of frequency).
2. Verify the idle-timeout / max-session backstops actually tear down a
   stalled REPL mid-sweep and the sweep moves on.
3. Verify blocker flow under sweep: a `coga block` mid-sweep parks the task,
   notifies, and the sweep continues; the blocker appears in
   `coga status --blocked` with an answerable reason.
4. Verify state sync under repeated sequential launches (the control-branch
   race class: see prior tickets `prevent-autostash-spool-conflicts-on-control-branc`,
   `fix-stale-relay-sync-context-git-failures-swallowe`).
5. Run summary must be accurate (launched / completed / blocked / skipped /
   failed) — it feeds the experiment's intention-to-treat reporting.

Related in-flight work to reconcile rather than duplicate:
`make-megalaunch-user-specific` (review), `drain-pending-auto-tickets-with-leftover-session-b`
(step 5), `nightly-auto-drain-run-for-ready-tickets` (step 2).

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
