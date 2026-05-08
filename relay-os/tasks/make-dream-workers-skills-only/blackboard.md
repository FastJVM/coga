The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: codex/dream-workers-skills-only
worktree: /home/n/Code/relay
pr: https://github.com/FastJVM/relay/pull/125

## Origin

Split out of `relay-os/tasks/dream-5/` on 2026-05-08 by nick. dream-5
combined three concerns; this ticket is concern #2 — make every Dream
worker a plain skill, removing the side-channel "Dream worker" Python
shape.

Sibling tickets:
- `move-relay-delete-into-a-skill` (dream-5 concern #1)
- `compose-dream-as-recurring-plus-alias` (dream-5 concern #3)

## Inventory to do first

Before refactoring, list every place in the repo that imports or
references a Dream worker as Python (grep `from relay.commands.dream`,
`worker.main`, `validate-drift`, `cleanup-orphan-markers`, anything
under `src/relay/resources/dream/`). Write the list here so we know
what "done" means for the grep-proves-it acceptance criterion.

## Open question

Where do these skills live — `relay-os/skills/dream/...` or
`relay-os/bootstrap/dream/skills/...`? Probably the bootstrap tree
since they ship with Relay, but confirm by looking at where the
existing `bootstrap/dream/tasks/...` resources sit today.

## 2026-05-08 Inventory

Current checkout: `main` at `2e4da60` (`origin/main`). Existing unrelated
changes before this session:
- `relay-os/tasks/make-dream-workers-skills-only/log.md` contains the launch
  line for this session.
- `relay-os/tasks/plan-second-wave-dream-workers/ticket.md` is modified.
- `relay-os/recurring/_rem.md` and `relay-os/tasks/dream/` are untracked.

Parent ticket note: `relay-os/tasks/dream-5/ticket.md` is not present in this
checkout; the split sibling tickets are present.

Grep inventory for Dream-worker-as-Python / skill references:
- `src/relay/dream_validate_drift.py` is the current validate-drift Python
  worker module. Tests import it directly in `tests/test_dream_validate_drift.py`.
- `src/relay/resources/templates/relay-os/bootstrap/skills/bootstrap/dream/tasks/validate-drift/SKILL.md`
  and `run.py` are the shipped template for the validate-drift skill. `run.py`
  currently imports `relay.dream_validate_drift.main`.
- `relay-os/bootstrap/skills/bootstrap/dream/tasks/validate-drift/` mirrors the
  same template in the dogfood `relay-os/bootstrap/` tree, but that tree is
  ignored upstream-managed content.
- `src/relay/resources/dream.md` and `relay-os/tasks/dream/ticket.md` still
  describe direct manual execution:
  `python relay-os/skills/bootstrap/dream/tasks/validate-drift/run.py --fix --blackboard ...`.
- `src/relay/commands/dream.py` scaffolds/launches Dream tasks but does not
  import worker `main()` functions.
- No literal `from relay.commands.dream` or `worker.main` hits in tracked source.
- `cleanup-orphan-markers` exists today as prose in `src/relay/resources/dream.md`
  under `### Done-Ticket Cleanup`, not as a skill/script.

Skill location decision: Relay-owned shipped skills live under
`src/relay/resources/templates/relay-os/bootstrap/skills/...`; `relay init`
copies that to `relay-os/bootstrap/skills/...` and recreates symlinks like
`relay-os/skills/bootstrap -> ../bootstrap/skills/bootstrap`. A workflow step
therefore references `bootstrap/dream/tasks/<name>`, while the shipped source
of truth is the template tree under `bootstrap/skills`.

Dependency decision point: sibling `move-relay-delete-into-a-skill` is still
active and has not landed. Current code still has `src/relay/commands/delete.py`
doing deletion directly, and no `bootstrap/delete-task` skill exists yet. For
this ticket, either:
- make `cleanup-orphan-markers` target the proposed `bootstrap/delete-task`
  skill contract and refuse deletion with `human-needed` when that skill is
  absent; or
- pause this ticket until the sibling lands.

Decision from nick: proceed with the dependency-tolerant path. Implement
`cleanup-orphan-markers` as a real skill that detects eligible orphan markers
and writes `human-needed` until `bootstrap/delete-task` exists.

## 2026-05-08 Implementation

Implemented:
- Added script-mode task metadata env vars in `src/relay/commands/launch_script.py`:
  `RELAY_TASK_SLUG`, `RELAY_TASK_DIR`, `RELAY_TASK_TICKET`,
  `RELAY_TASK_BLACKBOARD`, `RELAY_TASK_LOG`, `RELAY_RELAY_OS_ROOT`,
  `RELAY_REPO_ROOT`, `RELAY_SKILL_NAME`, and `RELAY_SKILL_DIR`.
- Moved validate-drift executable logic into the shipped skill script:
  `src/relay/resources/templates/relay-os/bootstrap/skills/bootstrap/dream/tasks/validate-drift/run.py`.
  Removed the old side-channel module `src/relay/dream_validate_drift.py`.
- Added `bootstrap/dream/tasks/cleanup-orphan-markers` as a shipped script skill.
  It scans exact `status: done` task directories for a `## Retro` block with
  `skill: retro/done-ticket` and `status: processed`; if candidates exist and
  `bootstrap/delete-task` is missing, it writes `human-needed` and deletes
  nothing.
- Updated Dream docs/spec/context wording so Dream-owned scripts are skills
  attached to Relay tasks, never standalone execution units.
- Added tests for script-mode env injection, validate-drift as a mode-script
  skill, cleanup-orphan-markers as a mode-script skill, and template/docs
  contract wording.

Important handoff note: files under
`src/relay/resources/templates/relay-os/bootstrap/...` are ignored by the
template `.gitignore`. The new cleanup-orphan-markers skill files must be
force-added when committing:
`git add -f src/relay/resources/templates/relay-os/bootstrap/skills/bootstrap/dream/tasks/cleanup-orphan-markers/SKILL.md src/relay/resources/templates/relay-os/bootstrap/skills/bootstrap/dream/tasks/cleanup-orphan-markers/run.py`.

Verification:
- `.venv/bin/python -m pytest` -> 271 passed.
- `.venv/bin/python -m relay.validate --json` -> no errors; one existing
  warning: `plan-second-wave-dream-workers` is `stuck-active` after 140.1h.
- Grep for `dream_validate_drift`, `from relay.commands.dream`, `worker.main`,
  `Dream Worker:`, `--blackboard`, and `--slack-task` in source/tests/docs
  only finds the negative `--blackboard` assertions in tests.
