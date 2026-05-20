The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: codex/testing-skill-split
pr: https://github.com/FastJVM/relay/pull/92

## Outcome

This ticket is being closed as a design pivot, not shipped as originally
described.

The original ask was a Dream worker for unit tests. During review we decided
that boundary was wrong: unit-test execution belongs in generic dev workflows,
not in Dream. Dream can later discover missing testing skills or stale imported
skills, but it should not own normal dev test execution.

PR https://github.com/FastJVM/relay/pull/91 is cancelled. Replacement PR
https://github.com/FastJVM/relay/pull/92 splits follow-up work into draft
tickets:

- `add-bootstrap-skill-for-importing-external-skills`
- `add-imported-skill-update-check`
- `add-dev-testing-setup-skill`
- `add-dev-test-run-skill`
- `add-dev-unit-test-writing-skill`

## Retro

status: processed
skill: retro/done-ticket
result: no-new-durable-knowledge
title: No new durable knowledge for add-dev-unit-test-dream-worker
