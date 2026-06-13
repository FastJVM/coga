---
name: relay/period-task
description: For the agent running one firing of a recurring task. Persistent state lives in the parent recurring task's blackboard, not this period's blackboard. Auto-attached to every period task by the scaffolder.
---

# You are a period task

You were scaffolded by `relay recurring` from a recurring task. Your
task directory under `relay-os/tasks/recurring/<name>/` is the scratch space
for this run. The path is stable for the template, but the directory is deleted
after a completed run and recreated for a later period. Your own
`blackboard.md` is gone with you when this run ends.

## Your task ref names your parent

Your task ref is `recurring/<parent-name>`. The `recurring/` group is the
identity marker; the period is **not** encoded in the slug.

Your parent recurring task lives at
`relay-os/recurring/<parent-name>/`. Its `blackboard.md` persists across
every run. The scaffolder records the period currently being serviced there as
`last_serviced_period: <period_key>`, where the bucket is `YYYY-MM-DD-HH`
(hourly), `YYYY-MM-DD` (daily), `YYYY-Www` (weekly), or `YYYY-MM` (monthly).
Read that line when this run needs to know which period it is servicing; do
not parse the period from your slug.

## Persistent state lives in the parent's blackboard

If this run needs to remember anything for the next run — a
last-processed commit SHA, a high-water mark, a cursor, a "posted /
skipped" flag — read and write
`relay-os/recurring/<parent-name>/blackboard.md`.

Every period-task run that carries state follows the same shape:

1. At the start, read `relay-os/recurring/<parent-name>/blackboard.md`
   to find the current `last_serviced_period` and where the previous run
   stopped.
2. Do this period's work.
3. Before finishing, update that same file with whatever the next run
   needs. Then `relay mark done` (or `relay bump` to the next non-final
   workflow step, if the run is not complete yet).

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

Your own `relay-os/tasks/recurring/<parent-name>/blackboard.md` is fresh for
this run and gone after cleanup. Notes for yourself within this run are fine
there; cross-run state is not — nothing in the instantiated task directory
survives to the next firing.
