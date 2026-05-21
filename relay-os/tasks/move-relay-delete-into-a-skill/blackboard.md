The blackboard is a notepad to be written to often as the human and agent works through a task.

## Origin

Split out of `relay-os/tasks/dream-5/` on 2026-05-08 by nick. dream-5
combined three concerns; this ticket is concern #1 — make `relay delete`
dispatch into a skill so deletion is no longer Relay-private Python.

Sibling tickets:
- `make-dream-workers-skills-only` (dream-5 concern #2)
- `compose-dream-as-recurring-plus-alias` (dream-5 concern #3)

## Dev

branch: delete-task-skill
worktree: ../relay-delete-task-skill
PR: https://github.com/FastJVM/relay/pull/186

## Decisions (2026-05-20, nick + claude)

- **Skill name** — `bootstrap/delete-task`. Not actually open: the sibling
  `cleanup-orphan-markers` skill already hardcodes this ref
  (`DELETE_SKILL = "bootstrap/delete-task"`). Keeping it.
- **Dispatch** — `relay delete` runs the skill's script *directly*, not via
  a scaffolded ephemeral task. nick chose this. Reasoning: scaffolding a
  throwaway `mode: script` task for every delete litters `tasks/` with a
  directory that itself needs deleting; the `mode: script` env contract is
  cheap to reproduce. `relay delete` resolves the target slug, builds the
  same `RELAY_TASK_*` env `relay launch` injects (pointed at the *target*
  task), and runs `bootstrap/delete-task`'s `run.py` directly. The skill is
  still a genuine, independently-launchable `mode: script` skill — a test
  proves a `mode: script` task whose step references it self-deletes via
  `relay launch` — so the "scripts are skills" architecture story holds.

## Skill contract

`bootstrap/delete-task` deletes the task directory identified by
`RELAY_TASK_DIR`. One input, one effect. Two callers produce that env:
- `relay delete <slug>` — resolves `<slug>` to the target, sets env for it.
- `relay launch` on a `mode: script` task — sets env to that task's own dir
  (the task deletes itself).
The skill sanity-checks the dir contains `ticket.md` before `rmtree` so it
can never be pointed at an arbitrary directory.

## Implementation notes

- `delete.py` keeps `resolve_task` (prefix matching + unknown→exit 2 +
  implicit bootstrap-shim refusal — shims aren't `TaskRef`s).
- `launch_script.py`: extracted `build_script_env()` so the `RELAY_TASK_*`
  contract has one definition shared by `relay launch` and `relay delete`;
  guarded the post-script `append_log` against a task dir the script
  legitimately deleted (self-delete via `relay launch`).

## Implemented (2026-05-20, implement step)

Changed files (branch `delete-task-skill`):
- NEW `src/relay/resources/templates/relay-os/bootstrap/skills/bootstrap/delete-task/{SKILL.md,run.py}`
  — the deletion skill. `run.py` deletes `RELAY_TASK_DIR` after confirming it
  contains `ticket.md`; self-contained, no relay imports (like dream workers).
  Force-added: the templates tree's own `.gitignore` ignores `bootstrap/`.
- `src/relay/commands/delete.py` — thin: resolve task → resolve skill →
  run its script directly with the `build_script_env` contract. Fails loud
  if the skill is missing (no private rmtree fallback).
- `src/relay/commands/launch_script.py` — extracted `script_repo_root`,
  `build_script_env`, `build_script_command` (shared with `relay delete`);
  guarded the post-script `append_log` against a self-deleted task dir.
- `relay/cli` context (local override + packaged bootstrap copy) — one
  sentence on the `relay delete` entry.
- `tests/test_commands.py` — delete tests install the skill; added
  `test_delete_missing_skill_exits_nonzero` and
  `test_delete_skill_runs_as_script_step` (proves the skill self-deletes a
  `mode: script` task via `relay launch`).

Verification: `python -m pytest` → 370 passed, 1 skipped (with
`RELAY_SUPERVISED` unset). The one failure seen otherwise,
`test_bump_unsupervised_prints_no_hint`, is pre-existing on `main` and
unrelated — the test does not clear `RELAY_SUPERVISED`, so it trips when the
suite is run from inside a supervised `relay launch` session (as here). Worth
a separate test-isolation fix; not in scope.

## Adjacent issue (not fixed here — for a follow-up / Dream validate-drift)

- `relay-os/contexts/relay/cli/SKILL.md` (project-local override) has
  drifted badly from the bundled `bootstrap/contexts/relay/cli/SKILL.md`
  (stale `relay dream`/`relay ticket`/`relay draft` entries). Out of scope
  for this ticket; only the `relay delete` paragraph was touched, and it
  was identical across all three copies.
- `cleanup-orphan-markers`'s hand-rolled `delete_skill_path()` only checks
  project-local `skills/bootstrap/delete-task/`, not the bundled
  `bootstrap/skills/` location where this ticket installs the skill. Today
  that worker only *reports* (never calls delete-task), so nothing breaks,
  but the sibling `compose-dream-as-recurring-plus-alias` should switch it
  to the standard local-then-bootstrap resolution before wiring delete-task
  in.
