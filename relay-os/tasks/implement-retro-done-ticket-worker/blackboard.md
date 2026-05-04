The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: codex/retro-done-ticket-worker
pr: https://github.com/FastJVM/relay/pull/94

## Plan

Implement the first retro done-ticket Dream worker as a deterministic,
one-ticket worker. It will no-op unless the target ticket is `status: done`,
read `ticket.md`, `blackboard.md`, and `log.md`, render reviewable extraction
proposals/draft artifacts from that evidence, delete only the target task
directory, and optionally commit/push from a non-main Dream branch. Final
judgment about context/skill/workflow text stays in the review loop rather
than heuristic Python.

## Implementation Notes

- Added `relay.dream_retro_done_ticket`, a one-ticket worker that requires an
  exact task slug, no-ops for non-`done` tickets, refuses deletion when the
  task directory has uncommitted changes, and emits a report with context,
  skill, workflow, evidence, intentionally-dropped, and PR-body sections.
- Added the shipped `bootstrap/dream/tasks/retro-done-ticket` worker template
  and wrapper script, plus Dream skill instructions for when to run it.
- Verification: `PYTHONPATH=src /home/n/Code/relay/.venv/bin/python -m pytest`
  passed in `.codex-worktrees/retro-done-ticket-worker` with 222 tests.
- GitHub checks: `gh pr checks 94 --watch --interval 10` reported no checks on
  `codex/retro-done-ticket-worker`; there is no CI result to wait for.
