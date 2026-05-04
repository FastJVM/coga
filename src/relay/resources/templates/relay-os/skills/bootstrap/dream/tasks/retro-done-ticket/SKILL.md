---
name: bootstrap/dream/tasks/retro-done-ticket
description: Extract warranted context and rare skill artifacts from one done ticket, then publish the extraction as a PR.
script: run.py
---

# Retro Done Ticket

This worker is Dream's done-ticket extraction unit. It accepts exactly one Relay
task slug. It reads that task's `ticket.md`, `blackboard.md`, and `log.md`,
extracts warranted durable lessons into concrete context blocks or new context
files, rarely creates a skill file when the ticket shows a repeatable process,
and publishes those artifacts as a PR. It does not delete the source ticket or
clean up task branches; those are separate Dream skills.

## Known Skill Contract

- Purpose: extract durable knowledge from one done ticket into contexts, and
  rarely into a skill when process evidence explicitly warrants it.
- Runs:
  `python relay-os/skills/bootstrap/dream/tasks/retro-done-ticket/run.py <done-task-slug> --commit-and-push --create-pr --blackboard relay-os/tasks/<dream-run-task>/blackboard.md --slack-task <dream-run-task>`
- Inputs: one exact done task slug; that task's `ticket.md`, `blackboard.md`,
  and `log.md`; existing context files referenced by the ticket.
- May change: `relay-os/contexts/**/SKILL.md`,
  `relay-os/skills/retro/**/SKILL.md`, the Dream run blackboard, the current
  non-main git branch, a GitHub PR for that branch, and one Slack FYI.
- Action: `pr-required`.
- Idempotency: extracted blocks include a `relay-retro:<task-slug>` marker;
  reruns skip files that already contain that marker.
- Stop and ask: the target task is not `done`; required task files are missing;
  the current branch is `main`/`master` and `--commit-and-push` was requested;
  PR creation or push fails.
- Output: append `## Dream Worker: retro-done-ticket` to the Dream run
  blackboard, optionally commit/push/create a PR, and post a one-line Slack
  summary when `--slack-task` is provided.

## How to Run

From the host repo root, on a Dream extraction branch:

```
python relay-os/skills/bootstrap/dream/tasks/retro-done-ticket/run.py <done-task-slug> --commit-and-push --create-pr --blackboard relay-os/tasks/<dream-run-task>/blackboard.md --slack-task <dream-run-task>
```

Replace `<done-task-slug>` with one done ticket. Do not pass a list of tasks;
Dream should run one retro per ticket so each extraction PR stays reviewable.

The worker writes artifacts directly; there is no `--apply` flag. Use
`--dry-run` only to preview the report without writing context or skill files.
With `--commit-and-push`, it stages only written extraction artifacts and the
Dream run blackboard report, commits them, and pushes the current branch. With
`--create-pr`, it creates or reuses the PR for that branch.

## Output

The worker appends a concise section to the Dream run blackboard:

```
## Dream Worker: retro-done-ticket
```

The section includes:

- `Source ref`, a source task slug and git ref, for example
  `abc123def456:relay-os/tasks/<done-task-slug>/`;
- concrete context or skill artifacts written from ticket evidence;
- `ticket.md`, `blackboard.md`, and `log.md` evidence counts/highlights;
- explicit notes that the ticket directory and task branches are untouched;
- a PR body snippet that links back to the source ticket archive.

When `--slack-task` is provided, it posts a one-line summary against the Dream
run task.

## Safety

- Non-`done` tickets are a no-op. The worker reports the status and changes no
  files.
- Missing `ticket.md`, `blackboard.md`, or `log.md` is an error.
- Non-`done` tickets are a no-op. The worker reports the status and changes no
  files.
- The source task directory is never deleted by this worker.
- Task branch cleanup belongs to separate Dream branch-cleanup skills.
- If a ticket has attached contexts, warranted context blocks are appended
  there. If it has no contexts, the worker creates a focused
  `relay-os/contexts/retro/<done-task-slug>/SKILL.md`.
- Skill files are generated only when process evidence explicitly warrants
  them.
