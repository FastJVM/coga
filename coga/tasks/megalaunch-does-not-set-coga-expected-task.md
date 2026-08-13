---
slug: megalaunch-does-not-set-coga-expected-task
title: Megalaunch does not set COGA_EXPECTED_TASK
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/architecture
- coga/codebase
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
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

`coga megalaunch` marks the child as supervised but does not set the
session-scoped ownership witnesses that an ordinary `coga launch` sets for
each step.

The ordinary launch loop builds a fresh `step_env` and writes both
`COGA_EXPECTED_TASK` and `COGA_EXPECTED_STEP` before calling
`spawn_agent_session`. The megalaunch path builds a launch environment, sets
only `COGA_SUPERVISED=1`, and calls the same spawn helper directly.

This breaks two launch-wide contracts:

1. `coga open-pr` reads `COGA_EXPECTED_TASK` to prove that a single-checkout
   feature branch owns the live ticket. A megalaunch-run task reaching the
   `open-pr` step cannot provide that proof and is refused even though it is the
   real supervised session.
2. `coga bump` uses the task/step pair as its compare-and-swap guard against a
   stale supervised session advancing a ticket that another session already
   moved. Megalaunch sessions silently lack that guard.

The defect was first diagnosed while running Magicator through megalaunch on
2026-07-27. The safe one-off workaround was to set the expected task only after
verifying that the checkout owned the live ticket; the workaround was never a
substitute for fixing the shared launch contract.

### Scope

- Give every megalaunch-spawned step the same expected-task and expected-step
  witnesses as the ordinary launch supervisor.
- Keep those witnesses pinned to the outer session; nested task metadata
  re-derivation must not retarget them.
- Prefer one shared helper for constructing a supervised step environment so
  the launch and megalaunch paths cannot drift again.
- Add regressions for both the single-checkout `open-pr` ownership proof and
  the stale-step bump guard under megalaunch.

### Acceptance criteria

- A megalaunch-run task can publish from the supported single-checkout layout
  without manually exporting `COGA_EXPECTED_TASK`.
- A megalaunch child receives the exact task path and frozen current step that
  composed its prompt.
- The existing ordinary-launch behavior and nested-launch isolation tests stay
  green.


## Context

- `src/coga/megalaunch.py` — constructs the child environment immediately
  before `spawn_agent_session`.
- `src/coga/commands/launch.py` — ordinary supervisor path that sets both
  witnesses.
- `src/coga/repl_supervisor.py` — names and documents the launch-wide env
  contract.
- `src/coga/open_pr.py` and `src/coga/commands/bump.py` — the two consumers.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
