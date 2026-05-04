The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: codex/dream-worker-contract

## Findings

- The current clean branch still ships Dream as the upstream-managed template
  `src/relay/resources/templates/relay-os/skills/bootstrap/dream/SKILL.md`.
  The actual project `relay-os/skills/bootstrap/` path is ignored user
  scaffolding, so the durable source edit belongs in `src/relay/resources/`
  and docs/tests, not in the ignored project copy.
- `move-dream-out-of-bootstrap` is a separate active ticket. For this ticket,
  the least risky contract path is to define discovery/dispatch in the current
  Dream template and document the future `skills/dream/orchestrate` naming in
  the spec without moving files here.

## Proposed Plan

1. Update the shipped Dream template so orchestration discovers enabled workers
   by walking `tasks/**/SKILL.md`, reads a small metadata convention, dispatches
   workers independently, and writes one run-level summary.
2. Add a durable spec section for the worker SKILL.md contract: metadata,
   body sections, output, idempotency, and destructive-action safety.
3. Tighten existing worker templates and tests so `validate-drift` and
   `dev/stale-branches` match the new contract language.

## Implementation

- Updated the shipped Dream template to define worker discovery by
  `tasks/**/SKILL.md`, a required `## Worker Contract` body section, independent
  dispatch, run-level summary shape, and destructive-action review defaults.
- Documented the durable contract in `docs/spec.md`, including the current
  `bootstrap/dream` location and the intended
  `skills/dream/orchestrate/SKILL.md` target for the namespace-move ticket.
- Added concrete `## Worker Contract` sections to the existing
  `validate-drift` and `dev/stale-branches` worker templates.
- Added focused tests in `tests/test_dream_worker_templates.py`.

## Verification

- `python -m pytest tests/test_dream_worker_templates.py` failed because the
  system Python has no `pytest` installed.
- `/home/n/Code/relay/.venv/bin/python -m pytest tests/test_dream_worker_templates.py`
  passed: 3 tests.
- `/home/n/Code/relay/.venv/bin/python -m pytest` passed: 217 tests.
