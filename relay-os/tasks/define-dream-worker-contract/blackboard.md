The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: codex/dream-worker-contract
pr: https://github.com/FastJVM/relay/pull/93

## Findings

- The current clean branch still ships Dream as the upstream-managed template
  `src/relay/resources/templates/relay-os/skills/bootstrap/dream/SKILL.md`.
  The actual project `relay-os/skills/bootstrap/` path is ignored user
  scaffolding, so the durable source edit belongs in `src/relay/resources/`
  and docs/tests, not in the ignored project copy.
- Human review rejected the project-extension shape. Dream should stay a
  bootstrap feature and execute only a known list of shipped skills.

## Proposed Plan

1. Keep Dream at `bootstrap/dream`.
2. Make `bootstrap/dream/SKILL.md` the explicit known-skill dispatcher.
3. Drop recursive `tasks/**/SKILL.md` discovery and user/plugin API language.
4. Keep per-known-skill contracts for allowed changes, output, idempotency, and
   safety.

## Design-First Reset

The human clarified that we are designing from the ticket first, not continuing
implementation yet. The ticket body now carries the intended design:

- Dream is a bootstrap feature at `bootstrap/dream`.
- Dream runs a set of known shipped skills named in `bootstrap/dream/SKILL.md`.
- Files under `tasks/` are inert unless the bootstrap Dream skill explicitly
  names them.
- The contract is `## Known Skill Contract`, not a user-extension API.
- User space can still define a separate maintenance loop directly, e.g. `rem`
  or another normal skill/workflow/recurring task, with its own state and
  conventions.
- User confirmed updating the existing PR is acceptable, so the PR now carries
  this design instead of the recursive-discovery design.

## Implementation

- Replaced recursive worker discovery with an explicit known-skill dispatch
  table for `validate-drift` and `dev/stale-branches`.
- Renamed the body convention to `## Known Skill Contract` and reduced it to
  purpose, run instructions, allowed changes, action mode, idempotency, stop
  conditions, and output.
- Updated `docs/spec.md`, the task ticket body, and template tests to make
  bootstrap Dream the canonical shape.
- Added the explicit user-space escape hatch: repos may define `rem`,
  `ops/dream`, or another normal skill/workflow/recurring task with its own
  state and conventions, separate from bootstrap Dream.
- Opened PR https://github.com/FastJVM/relay/pull/93. GitHub connector PR
  creation returned 404, so the PR was created with `gh pr create`.

## Verification

- `python -m pytest tests/test_dream_worker_templates.py` failed because the
  system Python has no `pytest` installed.
- `/home/n/Code/relay/.venv/bin/python -m pytest tests/test_dream_worker_templates.py`
  passed: 3 tests.
- `/home/n/Code/relay/.venv/bin/python -m pytest` passed: 217 tests.
- After the bootstrap/user-space boundary rewrite,
  `/home/n/Code/relay/.venv/bin/python -m pytest tests/test_dream_worker_templates.py`
  passed: 3 tests.
- After the bootstrap/user-space boundary rewrite,
  `/home/n/Code/relay/.venv/bin/python -m pytest` passed: 217 tests.
- `gh pr checks 93` reported no checks on the branch.
- `relay bump define-dream-worker-contract --message "PR opened: ..."` advanced
  the ticket to review, then failed only on Slack DNS inside the sandbox. A
  follow-up `relay slack` was run with network approval and posted the handoff.
  The failed Slack log entry was redacted to remove the webhook path before
  staging.
