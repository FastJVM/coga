---
name: bootstrap/delete-task
description: Remove a task directory from the working tree — the implementation behind `coga delete`, also runnable as a standalone script-mode skill.
script: run.py
---

# Delete Task

Remove a Coga task — its `ticket.md` (and, in directory form, the task
directory and any siblings) — from the working tree. Recovery is via `git restore`; git
history is the audit trail, so deletion posts no Slack broadcast.

This is the single implementation of task deletion. `coga delete <slug>`
resolves the slug to a task, then runs this skill's `run.py` directly with the
task-metadata environment variables a `mode: script` launch injects. The skill
is equally a normal `mode: script` skill: a workflow step that references
`bootstrap/delete-task` deletes its own task directory on `coga launch`.

The script keys off `COGA_TASK_TICKET`: a `<dir>/ticket.md` means a
directory-form task, so it removes that one task directory; a `tasks/<slug>.md`
means a file-form task, so it removes that single file only and never touches
the shared parent. It refuses a target that is unset or not a file, so it can
never be pointed at an arbitrary directory.

## Known Skill Contract

- Purpose: remove a single task (file or directory) from the working tree.
- Runs: `run.py` — invoked by `coga delete <slug>`, or as the script of a
  workflow step that references `bootstrap/delete-task`.
- Inputs: the `COGA_TASK_TICKET` and `COGA_TASK_SLUG` environment variables.
  The ticket path's name discriminates the form (`ticket.md` → directory form;
  `<slug>.md` → file form).
- May change: deletes exactly the one task named by `COGA_TASK_TICKET` — its
  directory (directory form) or its single `.md` file (file form). No other
  file, ref, or lifecycle state, and never a shared parent directory.
- Action: `direct-fix`
- Idempotency: existence is checked before the single delete; there is no
  partial state to reconcile. The caller (`coga delete`, or a Dream worker) is
  responsible for not dispatching a target twice.
- Stop and ask: `COGA_TASK_TICKET` is unset or not a file — the script exits
  non-zero without deleting anything.
- Output: prints `<slug>: deleted <path>` to stdout. No Slack broadcast, no
  blackboard write.
