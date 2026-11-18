---
title: Trim retained audit history
status: in_progress
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: 620dec34-2487-4bc5-9fe1-3467112d875c
workflow:
  name: trim-log/run
  steps:
  - name: trim
    skills: []
    assignee: agent
    checkout: manual
step: 1 (trim)
---

## Description

Run the reserved `ticket.py` headlessly every Monday at 04:00 in the sweeping
process's local timezone, including inactive repos. It invokes the installed
`coga_edge.trim_log` and completes disabled, empty and unchanged periods too.

### Retention

Trimming is on by default: shared `[log].retention_days = 30`; `0` disables it.
Delete only complete events strictly before local midnight on today minus the
window, capturing today once per attempt. Git history is the archive; no
archive file is created. This is a soft age bound. Keep the exact boundary,
future events, and these exceptions:

- Complete history of every discovered ticket still on disk, in every status.
- All occurrences of each recurring ref's greatest valid serviced period,
  including absent or parked templates; its latest creation/pause evidence
  also survives, ordered by timestamp and physical order for same-minute ties.
- Movement still unread by an installed phone-home cursor with an identity.
- Opaque, malformed, invalid-encoding and incomplete data, and the event
  boundary needed to keep task-history attribution unchanged.

Legacy continuations travel with their event. Surviving bytes, order,
duplicates and v1 escaping stay intact. A malformed ledger, inventory or
incompatible cursor refuses and records a prerequisite. Local calendar days
match the timezone-free log envelope; this is not an elapsed-hour guarantee
across DST or writers in different zones. Usage still filters by JSON `ts`.
Reports before the window can be incomplete and do not read Git automatically.

### Transaction and completion

Publish pending events before deleting any; every removal must already be
recoverable from reachable control history. Disabled Git and confirmed non-Git
runs report a non-destructive skip. A remote-less repo can use verified local
control history. The state lock covers snapshot, cursor migration and local
replacement. Exact guards pin the log, config, inventory and phone-home parent
on every publication attempt. Cursor migration and deletion commit together.
Never hold the parent lock while invoking the CLI bump subprocess.

A checkout-local Git receipt prevents an interrupted deletion from becoming an
ordinary append publication. Exit 75 retains uncertain output for recovery;
no successful completion or agent fallthrough occurs. Successful maintenance
uses `Log: recurring/trim-log — ...`, which does not count as repo activity.
The run report includes removed and retained counts/bytes; no-change needs no
maintenance commit. See the persistent
[operations guide](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/recurring/trim-log/operations.md)
for explicit adoption, native Git conflict recovery and interrupted runs.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
