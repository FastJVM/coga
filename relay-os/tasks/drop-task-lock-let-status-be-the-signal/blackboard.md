# Blackboard — drop-task-lock-let-status-be-the-signal

Scratch space for the agent picking up this ticket. The ticket body
has the design; this file is for findings, decisions, and blockers
that surface during implementation.

## Pre-implementation survey (orient session, 2026-05-11)

Quick grep of the lock surface, captured here so the implementing
agent doesn't repeat the scan:

### Source

- `src/relay/lock.py` — the module itself (~94 lines).
- `src/relay/commands/launch.py` — imports `LockHeldError`, `TaskLock`.
- `src/relay/commands/launch_script.py` — same.
- `src/relay/commands/delete.py` — `--force`, "task.lock held" error.
- `src/relay/commands/panic.py` — imports `TaskLock` (releases on panic).
- `src/relay/bump.py` — imports `TaskLock`.
- `src/relay/validate.py` — imports `TaskLock`.
- `src/relay/commands/init.py` line ~96 — scaffolded rules.md mentions
  `task.lock`.
- `src/relay/resources/prompt.md` lines 23, 137 — base prompt rules.
- `src/relay/resources/dream.md` line 66 — stale-lock rule.
- `src/relay/resources/templates/relay-os/.gitignore` line 5 —
  `**/task.lock`.

### Tests touching the lock

- `tests/test_primitives.py` — direct `TaskLock` tests.
- `tests/test_launch.py:14, 930`
- `tests/test_launch_auto.py:83`
- `tests/test_launch_script.py:113`
- `tests/test_commands.py:126, 168, 174, 179`
- `tests/test_validate.py:13`
- `tests/test_init.py:38, 326` — `.gitignore` content expectations.

### Docs

- `relay-os/contexts/relay/architecture/SKILL.md` — "Locking" section.
- `relay-os/contexts/relay/cli/SKILL.md` — `--force` flags on `launch`
  and `delete`.
- `relay-os/contexts/relay/project-stage/SKILL.md` line 21 — example
  mentions renaming `task.lock`.
- `docs/spec.md` lines 184, 404, 407, 425, 593, 802, 1033 — deepest
  surface (lock file format, staleness, script-mode rules).
- `docs/design.md` line 85, 93 — design notes on acquisition + signal
  handlers.
- `docs/spec-audit.md` lines 59, 149, 485, 654 — audit refs.
- `README.md` lines 160, 275.
- `relay-os/.gitignore` line 9.

### Existing tickets that reference task.lock (informational)

- `move-relay-delete-into-a-skill` — touches `--force` semantics.
- `fail-loud-when-relay-launch-starts-an-interactive` — asserts no
  `task.lock` is created.
- `dream/ticket.md` — stale-lock rule.

These don't need to be edited as part of this ticket, but if any
ship around the same time the implementing agent should reconcile.

## Decisions made before scaffolding

- Keep the workflow short: `code/with-review` (implement → review).
  This is one PR. Don't split docs and code.
- No `--force` flags survive. The whole `--force` family was a
  lock-only escape hatch.
- Existing on-disk `task.lock` files stay until naturally cleared.
  No migration script in the PR.

## Dev

branch: drop-task-lock
worktree: /home/n/Code/relay-drop-task-lock
pr: https://github.com/FastJVM/relay/pull/132

## Implementation log

- Deleted `src/relay/lock.py` (94 lines) and removed all imports
  (`TaskLock`, `LockHeldError`, `LockInfo`) from `launch.py`,
  `launch_script.py`, `delete.py`, `panic.py`, `bump.py`, `validate.py`.
- Added soft-warn-on-active in `launch.py` (`_warn_already_active`):
  interactive launches against `status: active` print
  `⚠ <slug> is already active (assignee: <name>, last log <Nm> ago)`
  and prompt to confirm. Auto/script launches log and proceed.
  No-TTY interactive (CliRunner, CI) skips the confirm so test fixtures
  with `status="active"` still pass cleanly.
- Dropped `--force` flag from `relay launch` and `relay delete`. Both
  existed only to break stale locks.
- Removed `**/task.lock` from both the template `.gitignore` and the
  live `relay-os/.gitignore`. Updated `init.py`'s scaffolded `rules.md`
  agent instructions to drop the "don't touch task.lock" line.
- Removed three task.lock references from `resources/prompt.md` (base
  agent prompt).
- Updated `validate.py`: dropped `max_lock_hours` param, the
  stale-lock check, and the `--max-lock-hours` CLI flag.
- Updated Dream's `validate-drift` SKILL.md and run.py: removed
  stale-lock classification, dropped `max_lock_hours` from
  `build_validate_command`, dropped the Safety section.
- Updated `resources/dream.md`: removed the stale-lock human-needed
  rule and adjusted the Slack summary example.
- Tests: removed 5 lock-related tests in `test_primitives.py`,
  `test_delete_refuses_when_locked` + `test_delete_force_overrides_lock`
  in `test_commands.py`, `test_stale_lock_flagged` in `test_validate.py`,
  `test_classifies_stale_lock_as_human_needed` in
  `test_dream_validate_drift.py`, and the various `assert not
  task.lock exists` lines sprinkled through launch tests. Also dropped
  `**/task.lock` from the `.gitignore` content fixture in
  `test_init.py`. Added `test_launch_active_task_emits_soft_warning`
  to lock in the new behavior.
- Docs: rewrote the Locking section of `architecture/SKILL.md` as
  "Status is the signal"; deleted the lock-file-format section and
  the lock-can't-be-acquired row in `spec.md`; removed `--force`
  references in `cli/SKILL.md` and `README.md`; rewrote the
  Lock-lifecycle section of `design.md` as a "Status is the signal"
  postmortem; updated `spec-audit.md` to mark §B.7 resolved by removal.
- `python -m pytest`: 281 passed.
- `python -m relay.validate --json` on the live repo: clean except
  for pre-existing `stuck-active` warnings on other tickets.

## Retro

status: processed
skill: retro/done-ticket
result: no-new-durable-knowledge
title: Retro processed: no new durable knowledge for drop-task-lock-let-status-be-the-signal
