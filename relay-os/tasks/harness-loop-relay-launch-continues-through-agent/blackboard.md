The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: codex/harness-launch-loop
pr: https://github.com/FastJVM/relay/pull/86

## 2026-05-02 Plan

Workspace started dirty on `rewire-with-review-three-steps`; existing changes include the prerequisite workflow/assignee work plus an unrelated-looking `--agent` normal-task override change in `src/relay/commands/launch.py`, docs, and tests. I am preserving those edits and layering the harness-loop implementation on top.

Implementation shape:

- Keep bootstrap and `mode: script` launches single-shot.
- For normal `interactive` / `auto` tasks, hold the task lock across a loop of fresh agent subprocesses.
- Before each subprocess, re-read ticket state, re-compose the prompt, write a fresh temp prompt file, and print a short entering-step banner.
- After each clean subprocess exit, re-read the ticket and continue only if the task is still active, the step changed, the next current step has `skill:`, and the ticket assignee did not change.
- Stop without error on done/paused/no-skill/handoff/no-progress; stop with the agent exit code on panic/nonzero.

## 2026-05-02 Verification

- `.venv/bin/python -m pytest tests/test_launch.py tests/test_launch_script.py` -> 26 passed
- `.venv/bin/python -m pytest` -> 212 passed
- `.venv/bin/relay validate --json` -> ok_count 30, no issues
- clean worktree `/home/n/Code/relay/.codex-worktrees/harness-loop`: `PYTHONPATH=/home/n/Code/relay/.codex-worktrees/harness-loop/src /home/n/Code/relay/.venv/bin/python -m pytest` -> 212 passed
- clean worktree `/home/n/Code/relay/.codex-worktrees/harness-loop`: `PYTHONPATH=/home/n/Code/relay/.codex-worktrees/harness-loop/src /home/n/Code/relay/.venv/bin/python -m relay.cli validate --json` -> ok_count 30, no issues
- GitHub checks for PR #86: no checks reported on branch at PR creation time
- `relay bump ... --message "PR opened: https://github.com/FastJVM/relay/pull/86"` advanced the ticket to step 2 (review), but the Slack transition post failed under sandboxed DNS after the state write. Sent a manual `relay slack` FYI with network escalation: posted.

Git note: refreshed `origin/main`; current branch HEAD is already merged into `origin/main`. The intended PR diff against `origin/main` is limited to `src/relay/commands/launch.py`, `tests/test_launch.py`, `README.md`, `docs/spec.md`, and `src/relay/resources/templates/relay-os/contexts/relay/cli/SKILL.md`. Existing live `relay-os/tasks/*` edits remain unrelated local state and should not be staged for the code PR.

## Retro

status: processed
skill: retro/done-ticket
result: no-new-durable-knowledge
title: No new durable knowledge for harness-loop-relay-launch-continues-through-agent
