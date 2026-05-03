The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: codex/unit-test-dream-worker
pr: https://github.com/FastJVM/relay/pull/91

## Plan

- Follow the merged `dev/stale-branches` Dream worker template shape.
- Add a project-specific `tasks/dev/unit-tests/SKILL.md` worker template.
- Document a per-repo test-command convention instead of hard-coding Relay's Python command.
- Keep this scoped to dev/code task surfaces only; Dream may bootstrap the worker, but non-engineering Dream work must not inherit a unit-test requirement.
- Extend `tests/test_dream_worker_templates.py` with assertions for the new template contract.

## Notes

- Added `src/relay/resources/templates/relay-os/skills/bootstrap/dream/tasks/dev/unit-tests/SKILL.md`.
- The worker is explicitly dev/code-only and requires `[dream.dev.unit_tests].command` in `relay.toml`.
- Missing command configuration is a loud `human-needed` result; the worker must not guess from project files or use Relay's `python -m pytest` as a default.
- Failure output must include exact command, exit code, failing test names/headings, and `known` / `new` / `unknown` classification evidence.
- Passing runs write a concise no-op and do not open PRs just to report success.
- Verification: `/home/n/Code/relay/.venv/bin/python -m pytest tests/test_dream_worker_templates.py` -> 2 passed.
- Verification: `PYTHONPATH=src /home/n/Code/relay/.venv/bin/python -m pytest` -> 216 passed.
- GitHub checks: `gh pr checks 91 --watch=false` -> no checks reported on the branch.
- `relay bump add-dev-unit-test-dream-worker --message "PR opened: https://github.com/FastJVM/relay/pull/91"` advanced the ticket to review. The first Slack post failed under sandbox DNS; `relay slack --task add-dev-unit-test-dream-worker --message "Advanced to review. PR opened: https://github.com/FastJVM/relay/pull/91"` posted successfully with network escalation.
