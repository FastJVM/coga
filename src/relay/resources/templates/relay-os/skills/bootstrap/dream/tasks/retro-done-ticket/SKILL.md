---
name: bootstrap/dream/tasks/retro-done-ticket
description: Extract warranted context blocks from one done ticket, delete the ticket, and clean up its merged branch.
script: run.py
---

# Retro Done Ticket

This worker is Dream's done-ticket cleanup unit. It accepts exactly one Relay
task slug. It reads that task's `ticket.md`, `blackboard.md`, and `log.md`,
extracts warranted durable lessons into concrete context blocks, deletes the
task directory, and cleans up the task branch when git can prove it is merged.
Skill extraction is intentionally rare; use it only when the ticket shows a
repeatable process that is not already covered by the workflow skill.

## How to Run

From the host repo root, on a Dream cleanup branch:

```
python relay-os/skills/bootstrap/dream/tasks/retro-done-ticket/run.py <done-task-slug> --apply --delete-remote-branch --blackboard relay-os/tasks/<dream-run-task>/blackboard.md --slack-task <dream-run-task>
```

Replace `<done-task-slug>` with one done ticket. Do not pass a list of tasks;
Dream should run one retro per ticket so each deletion stays reviewable.

Without `--apply`, the worker writes the retro report but leaves the task
directory in place. With `--apply`, it deletes only
`relay-os/tasks/<done-task-slug>/`, appends extracted context blocks to attached
context files when the ticket evidence warrants it, and deletes a merged local
branch named by the ticket's `## Dev` / `branch:` line. With
`--delete-remote-branch`, it also deletes `origin/<branch>` when that
remote-tracking branch is proven merged into `HEAD`.

If the Dream run is already on a cleanup branch and the deletion/report should
be published immediately, add `--commit-and-push`. That mode stages only the
deleted task directory, written context blocks, and the Dream run blackboard
report, commits them, and pushes the current branch. It refuses `main`/`master`
unless a human explicitly passes `--allow-main-push`.

## Output

The worker appends a concise section to the Dream run blackboard:

```
## Dream Worker: retro-done-ticket
```

The section includes:

- `Source ref`, a source task slug and git ref, for example
  `abc123def456:relay-os/tasks/<done-task-slug>/`;
- concrete context blocks written or drafted from ticket evidence;
- branch cleanup evidence and actions for the ticket's `branch:` / `pr:` lines;
- `ticket.md`, `blackboard.md`, and `log.md` evidence counts/highlights;
- what was intentionally dropped as routine task noise;
- a PR body snippet that links back to the source ticket archive.

When `--slack-task` is provided, it posts a one-line summary against the Dream
run task.

## Safety

- Non-`done` tickets are a no-op. The worker reports the status and changes no
  files.
- Missing `ticket.md`, `blackboard.md`, or `log.md` is an error. Do not delete
  a task if the evidence set is incomplete.
- `--apply` refuses to delete a task directory with uncommitted changes, because
  git history would not archive the current on-disk evidence.
- The blackboard report must be written outside the task directory being
  deleted.
- Branch cleanup only deletes branches that are not current and are proven
  merged into `HEAD`.
- If a ticket has attached contexts, warranted context blocks are appended there
  in `--apply` mode. If it has no contexts, the worker renders a draft context
  block in the Dream blackboard and leaves the target as review-needed.
