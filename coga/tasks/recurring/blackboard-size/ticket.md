---
title: Blackboard size
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
workflow:
  name: blackboard-size/run
  steps:
  - name: report
    skills: []
    assignee: agent
    checkout: manual
---

## Description

Report ticket blackboards that have grown past the prompt-size threshold.

Once a week this recurring task's `ticket.py` runs `coga validate --json` and
keeps only its `large-blackboard` findings. Each finding names a ticket ref
and the measured size of the live notes that launch composes into prompts.
The threshold is the validator's current one, 32 KiB by default. The job runs
independently of Dream.

The run writes a `## Oversized blackboards` report to the period blackboard,
which reaches the sweep's run record. It lists each flagged ref with its size
and the threshold. When something is flagged, it also posts one ordinary
notification FYI naming the same refs and sizes. A delivery miss only warns.

### Informational only

The alert creates no ticket, review, blocker or edit, and the period closes
with `coga bump` either way. An oversized blackboard can be exceptional and
may stay as it is. When its owner wants it smaller, `coga/blackboard` ("Size
and its remedy") owns the procedure. Agents also remove stale notes as they
read a blackboard during ordinary ticket work ("Stale-note cleanup" in the
same topic).

A non-zero exit means `coga validate` itself could not run or its finding
could not be read. The runner then records a `## Recipe Failure` section on
the period blackboard and the period stays `in_progress`.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Oversized blackboards

Threshold: 32.0 KiB of live notes (`coga validate` `large-blackboard`). Informational: no review or block follows; `coga/blackboard` owns the optional remedy.

- `recurring/dream` — 39.5 KiB
