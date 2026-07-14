---
schedule: "0 9 * * 1"
schedule_comment: "Every Monday at 9am"
title: "Replace with the recurring task title"
# Step 1 runs as a script when its single skill declares `script:`;
# otherwise the run opens an attended agent session and requires a TTY.
workflow: namespace/your-workflow
owner: replace-with-human-name
assignee: replace-with-human-or-agent-nickname
# If each run carries a cursor / high-water mark in this recurring task's
# blackboard (a `last_commit: <SHA>` line, a cursor), list those keys here.
# `coga recurring` snapshots them when it scaffolds a period task, and a run
# that finishes without advancing one is flagged at `coga mark done` and in
# `coga validate` — so a forgotten state write can't silently re-do a range.
# state_keys:
#   - last_commit
---

## Description

What this recurring task does and why it runs on this cadence.

A recurring task is a ticket-format directory under `coga/recurring/`:
`ticket.md` (this file) carries the schedule, the run body, and a blackboard
region (below the `<!-- coga:blackboard -->` fence) that persists state across
runs; append-only run history goes to the repo-global `coga/log.md`. To
create a real recurring task, copy this whole `_template/` directory to a
non-underscore name.

`coga recurring` (called from `scripts/cron.sh`) get-or-creates the current
period's task when this template's schedule is due. Directories in
`recurring/` whose name starts with `_` are skipped — that's how this
template stays inert.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
