---
title: Keep agent edits to contexts and skills off the control branch without a merge
status: draft
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (design)
---

## Description

coga/principles §4 (memory via PR) forbids the system editing its own behaviour on main without a human merge gate, and the pitch now claims 'what agents learn reaches your team only through a pull request you merge'. The runtime does not enforce it: the end-of-command catch-all state sweep (git.py::sync_coga_state, pathspecs from git.py::_coga_state_pathspecs) commits everything dirty under coga/ — including coga/contexts/, coga/skills/, and coga/workflows/ — straight to the control branch. An agent that edits a context during a launched session and then runs coga bump has changed what every future agent is told, on main, with no PR. Today the gate is conduct only (Dream's proposal-PR procedure, the code/* branch discipline). Design, then implement, the smallest change that makes the principle true in code without breaking the sweep's other job — committing a human's hand-edits so they are not left dirty forever (the exact gap coga/sync already records for bootstrap/ in root layouts). Candidate designs to weigh in the design step: (a) exclude the knowledge directories from the catch-all sweep entirely and require an explicit commit or PR; (b) sweep them only when no COGA_TASK_* metadata is present, i.e. the actor is a human at the CLI, not a launched agent; (c) keep the sweep but make coga bump / mark done / block refuse in a launched session while knowledge directories are dirty, pointing the agent at branch + PR. Whichever wins, update coga/sync and the principle-4 receipt in coga/principles in the same PR, and add a test that a launched-session context edit cannot reach the control branch via the sweep.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
