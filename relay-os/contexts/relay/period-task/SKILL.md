---
name: relay/period-task
description: For the agent running one firing of a recurring task. Persistent state lives in the parent recurring task's blackboard, not this period's blackboard. Auto-attached to every period task by the scaffolder.
---

# You are a period task

You were scaffolded by `relay recurring` from a recurring task. Your
ticket directory under `relay-os/tasks/` exists for one period only — next
period scaffolds a fresh one. The composed prompt header gives your exact task
directory. Your own `blackboard.md` is gone with you when this run ends.

## Your slug names your parent

Your slug is `recurring-<parent-name>-<period_key>`, where the leading
`recurring-` is a fixed identity prefix and `period_key` is the firing's
bucket: `YYYY-MM-DD-HH` (hourly), `YYYY-MM-DD` (daily), `YYYY-Www`
(weekly), or `YYYY-MM` (monthly). Strip the leading `recurring-` prefix
**and** the trailing period suffix from your own slug to get the parent
name.

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

If the recurring task declares `state_keys:` in its frontmatter, those
keys are checked: when you `relay mark done`, any declared key still
holding the value it had when this period started is flagged (a local
warning, a Slack FYI, and a `relay validate` issue) — the signal that you
did the work but forgot to record the new high-water mark, so the next
firing would redo the same range. Advance the key (the run's record-state
step) before finishing.

## Do not write last-run state to your own blackboard

Your own task `blackboard.md` is fresh this period and gone next. Notes for
yourself within this run are fine there; cross-run state is not — nothing in
your task directory survives to the next firing.
