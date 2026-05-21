The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: validate-drift-dream-worker
pr: https://github.com/FastJVM/relay/pull/82

Plan:

- Add a first-class validate-drift Dream worker under the shipped Dream skill resources.
- Keep `relay validate --json` as the deterministic checker and have the worker classify/remediate from that JSON.
- Treat stale lock deletion conservatively: report it as human-needed unless a human verifies no live worker owns the lock.
- Add focused tests for classification and blackboard reporting.

Implemented:

- Added `relay.dream_validate_drift` as the worker implementation.
- Added shipped worker resources under `skills/bootstrap/dream/tasks/validate-drift/`.
- Updated the bootstrap Dream skill to run the worker and document stale-lock handling.
- Updated the spec's repo consistency section to make validate-drift the independent worker.

Verification:

- `.venv/bin/python -m pytest` -> 202 passed.
- `../.venv/bin/relay validate --json` from `example/` -> no issues.
- `.venv/bin/python src/relay/resources/templates/relay-os/skills/bootstrap/dream/tasks/validate-drift/run.py --cwd example` -> no validation drift found.
- GitHub checks: `gh pr checks 82 --watch=false` -> no checks reported for the branch.

Note: `relay validate --json` against this worktree's live dogfood `relay-os/` cannot run without creating `relay-os/relay.local.toml`, which this task prompt explicitly says not to edit.

## Retro

status: processed
skill: retro/done-ticket
result: no-new-durable-knowledge
title: No new durable knowledge for implement-validate-drift-dream-worker
