---
slug: cli-extension-model/fail-loud-on-step-regressions-in-bump-and-state-sy
title: fail loud on step regressions in bump and state sync
status: in_progress
mode: agent
owner: nicktoper
human: nicktoper
agent: codex
assignee: claude
contexts:
- coga/architecture
- coga/sync
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
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 2 (peer-review)
---

## Description

Make step-state writes fail loud when they would move a ticket backward,
instead of silently clobbering newer state (principle 6: fail loud).

Two guards:

1. **Compare-and-swap in `coga bump`.** A launched session knows which step it
   was composed for. If the on-disk `step:` no longer matches when the bump
   runs (another chain already advanced it), refuse with an error naming both
   steps instead of advancing from stale state.
2. **Regression check in the git ticket-state sync.** Before committing a
   "Sync coga state" that changes a ticket's `step:`/`status:`, compare against
   the committed version. If the write would move `step:` *backward* (or
   resurrect a pre-bump blackboard, i.e. the file shrinks around the fence
   while step regresses), refuse and report instead of committing — the
   on-disk regression stays visible and the log names it, rather than a quiet
   "Sync coga state" burying it.

Out of scope: a filesystem mutex or lock. The no-mutex design stands; this
ticket only makes divergence loud at the write, not impossible.

## Context

Motivating incident (2026-07-02, ticket
`cli-extension-model/move-the-recurring-scan-into-a-dream-shaped-task`):

- Two supervisor chains ran the same `in_progress` ticket concurrently. Each
  independently ran peer-review → open-pr → review, opening duplicate PRs
  (#506 and #507) and bumping to step 6 twice.
- At 22:56 a stale session's "Sync coga state" commit (`bdb16681`) rewound the
  ticket from `step: 6 (review)` back to `step: 4 (peer-review)`, flipped
  `assignee:` back to the agent, and deleted 64 blackboard lines including the
  peer-review verdict and the PR link. The task then looked "never bumped".
- Restored by hand from `f1bd3e61` (commit `89ec9458`).
- Aggravating factor: sandboxed sessions hit `git add` failures ("Read-only
  file system", non-fatal by design), so one chain's progress was invisible to
  git and fed the stale-copy interleaving.

Both guards are one-comparison-shaped checks on existing write paths
(`commands/bump.py` and the shared task-state sync), not new machinery.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: codex/step-regression-guards
worktree: /tmp/coga-step-regression-guards

## Implementation plan

- Add a supervised-launch expected-step env value scoped to the launched task path; `coga bump` will refuse when the live ticket step no longer matches the step the session was composed for.
- Add a `sync_coga_state` preflight that compares dirty task tickets against the committed control-branch version and skips/logs any catch-all sweep that would regress a ticket's step/status state.
- Cover both with focused regressions in the existing command/git test style before running the focused tests and full pytest.

## Implementation notes

- Launch now passes `COGA_EXPECTED_TASK` and `COGA_EXPECTED_STEP` into each supervised agent process; `coga bump` checks those against the resolved task path and current `step:` before advancing.
- `sync_coga_state` now scans changed task ticket files before staging, compares their `status:` / `step:` against the committed control-branch copy, and refuses stale backward writes with a task-scoped `git` log line.
- Added regressions for stale supervised bumps, launch env propagation, detached stale step rewinds, and status regressions.

## Verification

- `python -m pytest tests/test_commands.py::test_bump_supervised_refuses_stale_composed_step tests/test_launch.py::test_launch_marks_llm_session_supervised tests/test_git.py::test_sync_coga_state_refuses_detached_step_regression tests/test_git.py::test_sync_coga_state_refuses_status_regression` — 4 passed.
- `python -m pytest tests/test_commands.py tests/test_launch.py tests/test_git.py` — 214 passed.
- `git diff --check` — passed.
- `python -m pytest` — 1035 passed, 1 skipped.
