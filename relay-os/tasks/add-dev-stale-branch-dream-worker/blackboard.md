The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: codex/stale-branch-dream-worker
pr: https://github.com/FastJVM/relay/pull/90

## Notes

- Added a shipped Dream worker template at `src/relay/resources/templates/relay-os/skills/bootstrap/dream/tasks/dev/stale-branches/SKILL.md`.
- Kept the worker proposal-only: it records exact git evidence and proposed commands but does not delete local branches, remote-tracking refs, or remote branches.
- Categories are separated as merged local branches, stale remote-tracking refs, and old topic branches.
- Full test suite passed with `PYTHONPATH=src /home/n/Code/relay/.venv/bin/python -m pytest` (215 passed).
- GitHub checks: `gh pr checks 90 --watch=false` -> no checks reported on the branch.
- `relay bump ... --message "PR opened: ..."` advanced the ticket to review but the Slack post failed under sandbox DNS; sent an equivalent `relay slack` FYI with network access.

## Retro

status: processed
skill: retro/done-ticket
result: no-new-durable-knowledge
title: No new durable knowledge for add-dev-stale-branch-dream-worker
