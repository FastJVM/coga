---
schedule: "0 9 * * 1"
schedule_comment: "Every Monday at 9am"
title: "Replace with the recurring task title"
# Pick a mode: `script` runs a skill script directly with no agent;
# `auto` is a one-shot headless agent run whose output is buffered to the
# task log; `interactive` drops into a human terminal with live output.
mode: script
workflow: namespace/your-workflow
owner: replace-with-human-name
assignee: replace-with-human-or-agent-nickname
# If each run carries a cursor / high-water mark in this recurring task's
# blackboard (a `last_commit: <SHA>` line, a cursor), list those keys here.
# `relay recurring` snapshots them when it scaffolds a period task, and a run
# that finishes without advancing one is flagged at `relay mark done` and in
# `relay validate` — so a forgotten state write can't silently re-do a range.
# state_keys:
#   - last_commit
---

## Description

What this recurring task does and why it runs on this cadence.

A recurring task is a ticket-format directory under `relay-os/recurring/`:
`ticket.md` (this file) carries the schedule and run body, `blackboard.md`
persists state across runs, and `log.md` is the append-only run history. To
create a real recurring task, copy this whole `_template/` directory to a
non-underscore name.

`relay recurring` (called from `scripts/cron.sh`) get-or-creates the current
period's task when this template's schedule is due. Directories in
`recurring/` whose name starts with `_` are skipped — that's how this
template stays inert.
