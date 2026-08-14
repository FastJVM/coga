---
slug: megalaunch-does-not-set-coga-expected-task
title: Megalaunch does not set COGA_EXPECTED_TASK
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
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

## Dev

pr: https://github.com/FastJVM/coga/pull/689
branch: `fix/megalaunch-step-witnesses`
worktree: `/tmp/coga-megalaunch-step-witnesses`

## Implementation notes

- Centralize `COGA_SUPERVISED`, `COGA_EXPECTED_TASK`, and
  `COGA_EXPECTED_STEP` construction beside the launch-wide contract in
  `repl_supervisor.py`, then use it from both launch supervisors.
- Exercise the actual `open-pr` ownership predicate and stale-step bump guard
  from megalaunch's captured child environment.
- The primary checkout is currently on unrelated branch
  `drop-important-recipient`; preserve its commits and pending append-only
  `coga/log.md` line.

## Progress

- Regression-first check: both new megalaunch consumer tests failed because
  `COGA_EXPECTED_TASK` was absent; the nested environment test passed.
- Added `build_supervised_step_env` in `repl_supervisor.py` and routed both
  ordinary launch and megalaunch through it.
- Focused verification: 4 tests passed, covering megalaunch open-PR ownership,
  stale-step bump refusal, ordinary launch witnesses, and nested metadata
  re-derivation without witness retargeting.
- Broader affected suites: 319 tests passed.
- Full suite: 1,711 passed, 1 skipped.
- Updated both live and packaged `coga/architecture` copies to make the shared
  launch/megalaunch witness contract durable; packaging checks passed (4
  passed, 1 skipped), and the two copies are byte-identical.
- Committed as `1a73983c` (`Pin megalaunch step ownership witnesses`).
- Fetched `origin/main` at `6dc00fe3`; the final rebase reported the feature
  branch already up to date. The feature worktree is clean.
- No example fixture update: this changes the child environment contract, not
  task layout, prompt composition, or workflow semantics.
- Peer review: `codex review --base main` found no actionable issues and
  independently passed the then-current full suite (1,711 passed, 1 skipped).
- Refetched `origin/main` at `4ab373ed` and rebased unconditionally; the commit
  is now `a149ba76`, the feature worktree is clean and one commit ahead, and the
  live/packaged architecture copies remain byte-identical.
- Post-rebase full suite: 1,734 passed, 1 skipped.
- open-pr step: the primary control checkout was parked on the unrelated
  branch `drop-important-recipient`, so it was borrowed per `code/open-pr` —
  its drift was stashed (never committed), the checkout switched to `main`,
  `coga open-pr` run there, then the branch and stash restored exactly as
  found. `coga open-pr` reported PR
  https://github.com/FastJVM/coga/pull/689 (open, not a draft, head
  `fix/megalaunch-step-witnesses`) and recorded `pr:` under `## Dev`.
- Because the control checkout sits on a feature branch, only `main` carried
  the command's generated `pr:` write; that same ticket state was restored
  into the working tree so this step's bump publishes identical bytes from
  both branches.

## PR

Centralize the supervised-step child environment so both `coga launch` and
`coga megalaunch` pin `COGA_SUPERVISED`, `COGA_EXPECTED_TASK`, and
`COGA_EXPECTED_STEP` to the task and frozen step that composed each session.
Add regressions for megalaunch's single-checkout open-PR ownership proof,
stale-step bump refusal, and nested metadata isolation, and document the shared
contract in both shipped architecture copies.

Test plan: `python -m pytest` (1,734 passed, 1 skipped).
