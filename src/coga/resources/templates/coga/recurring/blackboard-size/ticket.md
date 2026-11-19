---
schedule: "0 8 * * 1"
schedule_comment: "Every Monday at 8am - report ticket blackboards over the size threshold"
title: "Blackboard size"
# The reserved `ticket.py` sibling is this task's deterministic half: `coga
# launch` runs it directly, with no agent and no composed prompt. The one-step
# workflow keeps the period task's lifecycle legible.
workflow: blackboard-size/run
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

<!-- coga:blackboard -->

This blackboard persists across every run of this recurring task. The job
keeps no cross-run state: each run measures the current blackboards afresh.
