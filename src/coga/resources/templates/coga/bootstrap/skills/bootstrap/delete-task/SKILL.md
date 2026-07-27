---
name: bootstrap/delete-task
description: Remove a task directory from the working tree — the contract behind `coga delete` and the `delete-task` registered recipe.
---

# Delete Task

Remove a Coga task — its `ticket.md` (and, in directory form, the task
directory and any siblings) — from the working tree. Recovery is via `git restore`; git
history is the audit trail, so deletion posts no Slack broadcast.

There is one implementation of task deletion, `coga.delete_task`, reached by
two spellings. `coga delete <task>` resolves the task, removes it, and syncs
the removal to the control branch. `coga run delete-task <task>` is the bare
working-tree removal with no sync — the spelling to use from inside another
task's session, where the caller owns when the deletion lands.

Deletion keys off the resolved ticket path: a `<dir>/ticket.md` means a
directory-form task, so it removes that one task directory; a `tasks/<slug>.md`
means a file-form task, so it removes that single file only and never touches
the shared parent. It refuses a target that is not a file, so it can never be
pointed at an arbitrary directory.

## Known Skill Contract

- Purpose: remove a single task (file or directory) from the working tree.
- Runs: `coga run delete-task <task>`, or `coga delete <task>` when the
  removal should also land on the control branch.
- Inputs: the task ref, resolved the same way every other Coga command
  resolves one. The ticket path's name discriminates the form (`ticket.md` →
  directory form; `<slug>.md` → file form).
- May change: deletes exactly the one named task — its directory (directory
  form) or its single `.md` file (file form). No other file, ref, or lifecycle
  state, and never a shared parent directory.
- Action: `direct-fix`
- Idempotency: existence is checked before the single delete; there is no
  partial state to reconcile. The caller (`coga delete`, or a Dream worker) is
  responsible for not dispatching a target twice.
- Stop and ask: the task ref does not resolve, or the resolved ticket is not a
  file — the recipe exits non-zero without deleting anything.
- Output: prints `<slug>: deleted <path>` to stdout. No Slack broadcast, no
  blackboard write.
