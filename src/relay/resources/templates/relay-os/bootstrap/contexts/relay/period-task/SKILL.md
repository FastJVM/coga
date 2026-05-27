---
name: relay/period-task
description: For the agent running one firing of a recurring task. Persistent state lives in the parent recurring task's blackboard, not this period's blackboard. Auto-attached to every period task by the scaffolder.
---

# You are a period task

You were scaffolded by `relay recurring` from a recurring task. Your
ticket directory under `relay-os/tasks/<slug>/` exists for one period
only — next period scaffolds a fresh one. Your own `blackboard.md` is
gone with you when this run ends.

## Your slug names your parent

Your slug is `<parent-name>-<period_key>`, where `period_key` is the
firing's bucket: `YYYY-MM-DD-HH` (hourly), `YYYY-MM-DD` (daily),
`YYYY-Www` (weekly), or `YYYY-MM` (monthly). Strip the trailing period
suffix from your own slug to get the parent name.

Your parent recurring task lives at
`relay-os/recurring/<parent-name>/`. Its `blackboard.md` persists across
every run — that is where last-run state belongs.

## Persistent state lives in the parent's blackboard

If this run needs to remember anything for the next run — a
last-processed commit SHA, a high-water mark, a cursor, a "posted /
skipped" flag — read and write
`relay-os/recurring/<parent-name>/blackboard.md`.

Every period-task run that carries state follows the same shape:

1. At the start, read `relay-os/recurring/<parent-name>/blackboard.md`
   to find where the previous run stopped.
2. Do this period's work.
3. Before finishing, update that same file with whatever the next run
   needs. Then `relay mark done` (or, for a workflowed period task,
   `relay bump` the final step).

The recurring task's `ticket.md` body names *which* keys it persists
(e.g. `last_commit`, a cursor section). That's the contract; this
context covers *where* the state lives.

## Do not write last-run state to your own blackboard

Your own `relay-os/tasks/<slug>/blackboard.md` is fresh this period and
gone next. Notes for yourself within this run are fine there;
cross-run state is not — nothing in `relay-os/tasks/<slug>/` survives
to the next firing.
