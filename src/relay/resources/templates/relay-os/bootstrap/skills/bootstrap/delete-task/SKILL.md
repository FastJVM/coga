---
name: bootstrap/delete-task
description: Remove a task directory from the working tree — the implementation behind `relay delete`, also runnable as a standalone script-mode skill.
script: run.py
---

# Delete Task

Remove a Relay task — its `ticket.md` (and, in directory form, the task
directory and any siblings) — from the working tree. Recovery is via `git restore`; git
history is the audit trail, so deletion posts no Slack broadcast.

This is the single implementation of task deletion. `relay delete <slug>`
resolves the slug to a task, then runs this skill's `run.py` directly with the
task-metadata environment variables a `mode: script` launch injects. The skill
is equally a normal `mode: script` skill: a workflow step that references
`bootstrap/delete-task` deletes its own task directory on `relay launch`.

The script deletes the directory named by `RELAY_TASK_DIR` and nothing else. It
refuses a target that is unset, is not a directory, or has no `ticket.md`, so
it can never be pointed at an arbitrary directory.

## Known Skill Contract

- Purpose: remove a single task directory from the working tree.
- Runs: `run.py` — invoked by `relay delete <slug>`, or as the script of a
  `mode: script` workflow step that references `bootstrap/delete-task`.
- Inputs: the `RELAY_TASK_DIR` and `RELAY_TASK_SLUG` environment variables;
  the target's `ticket.md` (its presence is checked to confirm the directory
  is a task directory).
- May change: deletes the one task directory named by `RELAY_TASK_DIR`. No
  other file, ref, or lifecycle state.
- Action: `direct-fix`
- Idempotency: existence and shape are checked before the single `rmtree`;
  there is no partial state to reconcile. The caller (`relay delete`, or a
  Dream worker) is responsible for not dispatching a target twice.
- Stop and ask: `RELAY_TASK_DIR` is unset, the target is not a directory, or
  it has no `ticket.md` — the script exits non-zero without deleting anything.
- Output: prints `<slug>: deleted` to stdout. No Slack broadcast, no
  blackboard write.
