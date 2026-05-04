---
name: bootstrap/dream/tasks/retro-done-ticket
description: Extract reviewable knowledge proposals from one done ticket and delete that task directory in the same cleanup PR.
script: run.py
---

# Retro Done Ticket

This worker is Dream's done-ticket cleanup unit. It accepts exactly one Relay
task slug. It reads that task's `ticket.md`, `blackboard.md`, and `log.md`,
turns the evidence into reviewable context/skill/workflow update proposals, and
can delete the task directory in the same PR.

## How to Run

From the host repo root, on a Dream cleanup branch:

```
python relay-os/skills/bootstrap/dream/tasks/retro-done-ticket/run.py <done-task-slug> --apply --blackboard relay-os/tasks/<dream-run-task>/blackboard.md --slack-task <dream-run-task>
```

Replace `<done-task-slug>` with one done ticket. Do not pass a list of tasks;
Dream should run one retro per ticket so each deletion stays reviewable.

Without `--apply`, the worker writes the retro report but leaves the task
directory in place. With `--apply`, it deletes only
`relay-os/tasks/<done-task-slug>/`.

If the Dream run is already on a cleanup branch and the deletion/report should
be published immediately, add `--commit-and-push`. That mode stages only the
deleted task directory and the Dream run blackboard report, commits them, and
pushes the current branch. It refuses `main`/`master` unless a human explicitly
passes `--allow-main-push`.

## Output

The worker appends a concise section to the Dream run blackboard:

```
## Dream Worker: retro-done-ticket
```

The section includes:

- `Source ref`, a source task slug and git ref, for example
  `abc123def456:relay-os/tasks/<done-task-slug>/`;
- context, skill, and workflow update proposals based on ticket evidence;
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
- The worker does not pretend heuristic Python can choose final knowledge edits.
  It creates reviewable context/skill/workflow proposals; the Dream agent or
  human reviewer applies the actual durable edits in the same PR when warranted.
