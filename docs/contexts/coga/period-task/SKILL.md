---
name: coga/period-task
description: For whoever runs one firing of a recurring task — agent or the template's `ticket.py`: cross-run state lives in the parent template's blackboard, this period's blackboard is per-run scratch. Auto-attached to every period task.
---

# You are a period task

`coga recurring` created this task from the template at
`coga/recurring/<parent-name>/`. The creator attaches this context to every
period task (`recurring._create_at_slug`); promotion strips it back out. Your
ref is `recurring/<parent-name>` and your directory
`coga/tasks/recurring/<parent-name>/` is scratch for this run only: when the
next period comes, Dream's retro pass or the scanner deletes it.

**Who reads this.** An agent on an agent-owned step reads it in its prompt. A
`delegate:` target does not receive it. A copied `ticket.py` runs first,
headless; if it closes its step nobody reads this, and if it exits 0 with the
step open, the same `in_progress` period passes to an agent that does. The rules
below bind code and agent alike. A finished `ticket.py` period whose blackboard
holds only the seeded placeholder is normal, not skipped bookkeeping.

## Which period you are servicing

The period is not in your slug. The newest `created|reused recurring/<parent-name>
for <period>` line tagged `recurring/<parent-name>` in `coga/log.md` names it.
That ledger is kept out of the parent blackboard so a run rewriting its cursors
cannot erase it.

## Persistent state lives in the parent's blackboard

Anything the next run needs — a last-processed SHA, a cursor, a posted flag —
goes below the `<!-- coga:blackboard -->` fence of
`coga/recurring/<parent-name>/ticket.md`. The template body names *which* keys;
this context says *where*.

1. Read the parent blackboard (and the log line) to find where the last run
   stopped.
2. Do this period's work.
3. Write back what the next run needs, then close the step: `coga bump`, or
   `coga mark done` for a one-step `direct/body` workflow. A `ticket.py` shells
   out to the same commands; nothing advances it on its behalf.

Code writes through the fence-aware API only: `coga.taskfile.read_blackboard` /
`replace_blackboard`, or `coga.blackboard.append_blackboard_report` /
`append_to_section` — never `open(path, "a")` or a whole-file rewrite. Pass the
captured `expected_bytes` to detect concurrent change, preserve the region's
leading newline, and if the file ends at the fence with no newline, start your
text with one (those helpers do not add it).

If the template declares `state_keys:`, completion (`coga mark done` or the
final `coga bump`, by agent or script) flags any key still equal to its value
at period start — a local warning, an important alert and a `coga validate`
issue — because the next firing would redo the same range.

## Your own blackboard is per-run scratch

Notes for yourself within this run are fine in your own blackboard; it feeds
this run's report and is deleted with the task. Put anything worth keeping —
a reusable gotcha under `## Gotchas` — where Dream's retro pass will extract it
before the delete. Never store cross-run state there, and never a secret.

Template authoring rules: [coga/recurring/templates](../recurring/templates/SKILL.md).
