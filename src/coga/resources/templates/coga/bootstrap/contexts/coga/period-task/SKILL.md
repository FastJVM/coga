---
name: coga/period-task
description: For whoever runs one firing of a recurring task — an agent session or the template's deterministic `ticket.py`. Persistent state lives in the parent recurring task's blackboard, not this period's blackboard. Auto-attached to every period task by the creator.
---

# You are a period task

You were created by `coga recurring` from a recurring task. Your
task directory under `coga/tasks/recurring/<name>/` is the scratch space
for this run. The path is stable for the template. A completed run remains
there as an ordinary `status: done` task until Dream's retro pass disposes of
it — normally a direct delete, but when your blackboard records something
durable (a reusable gotcha under `## Gotchas`) that is extracted into a
knowledge PR first, so write anything worth keeping down; if it survives, a
later recurring scan deletes it before recreating the path for a new period. The composed prompt header gives your exact task directory. Your
own blackboard (the region of your `ticket.md`, below the
`<!-- coga:blackboard -->` fence) disappears when that cleanup happens.

## Who runs this period: an agent, or the template's `ticket.py`

The creator attaches this context to every period task unconditionally
(`_create_at_slug` in `src/coga/recurring.py` appends `coga/period-task`;
`_template_frontmatter` strips a copy a promoted template already carries),
but who reads it depends on the template's dispatch, which is deduced from one
file:

- **No `ticket.py` beside the template: an agent runs the period.** `coga
  launch` composes this context into the prompt, and "you" below is that
  agent.
- **A `ticket.py` sibling: the recipe runs first, headless.** Launch copies
  the script into the period task and runs it as a subprocess with no prompt
  composed. When it closes its last step itself — the shape every shipped
  `ticket.py` template is written for, ending in a shell-out to `coga bump`
  or `coga mark done` — no agent starts and **nobody reads this context for
  that firing**. Each step of the shape below is then performed in code: the
  recipe reads any cursor it needs from the parent blackboard, does the
  period's work, writes the cursor back, and closes the step. Dispatch is not
  binary, though: a script that exits 0 leaving its step open — on its first
  run, or when the chain re-runs it on a later agent-owned step its bump
  reached — hands the *same* period to an agent phase that does get this
  prompt. In that case "you" is that agent, the
  period is already `in_progress`, and the parent blackboard is where the
  script left anything it wants you to have. The three outcomes are specified
  by the dispatch bullet and the completion contract in `coga/recurring`.

So read the rest of this context as addressed to *whoever runs this period*:
the recipe author when the reader is code, the agent otherwise. The state
contract does not change with the reader — persistent state lives in the
parent's blackboard, this period's blackboard is scratch, code goes through
the fence-aware API, and the `state_keys` check runs on the `coga bump` /
`coga mark done` a script shells out to exactly as it does on an agent's.

One consequence for anyone reading a finished period: a completed
deterministic run whose period blackboard still holds nothing but the seeded
placeholder is the normal signature of a `ticket.py` firing, not evidence
that the run skipped its bookkeeping. Nothing in the `ticket.py` contract asks
a recipe to write a run report there (see the analyst-channel note in
`coga/recurring`); its cross-run state, if it has any, is in the parent's
blackboard, and the period it serviced is in `coga/log.md`.

## Your task ref names your parent

Your task ref is `recurring/<parent-name>`. The `recurring/` directory is the
identity marker; the period is **not** encoded in the slug.

Your parent recurring task lives at
`coga/recurring/<parent-name>/`. Its blackboard region (in `ticket.md`,
below the `<!-- coga:blackboard -->` fence) persists across
every run — but only for *your* state. The period being serviced is recorded
in the repo-global `coga/log.md`, as a `created|reused <task-ref> for
<period>` line tagged `recurring/<parent-name>`, where the period key
buckets the firing: hourly → `YYYY-MM-DD-HH`, daily → `YYYY-MM-DD`, weekly →
`YYYY-Www`, monthly → `YYYY-MM`, and schedules outside those four buckets →
`YYYYMMDDTHHMM`. Read the newest such line when this run needs to know
which period it is servicing; do not parse the period from your slug.

The ledger is kept out of the parent blackboard on purpose: that region is
shared with whatever cursors you write, and a run that rewrites a section of
it would otherwise be able to erase the scheduler's own record and make the
period fire again.

## Persistent state lives in the parent's blackboard

If this run needs to remember anything for the next run — a
last-processed commit SHA, a high-water mark, a cursor, a "posted /
skipped" flag — read and write the blackboard region (below the fence) of
`coga/recurring/<parent-name>/ticket.md`.

Every period-task run that carries state follows the same shape:

1. At the start, read the blackboard region of
   `coga/recurring/<parent-name>/ticket.md` to find where the previous run
   stopped (and `coga/log.md` for the period being serviced).
2. Do this period's work.
3. Before finishing, update that same file with whatever the next run
   needs. Then finish the current workflow step with `coga bump` — or
   `coga mark done` when your workflow's only step is `direct/body`. A
   `ticket.py` does the same by shelling out to the CLI; it is never
   advanced on its behalf.

The recurring task's `ticket.md` body names *which* keys it persists
(e.g. `last_commit`, a cursor section). That's the contract; this
context covers *where* the state lives.

When the writer is code rather than you — a `ticket.py` phase, a helper
beside the template, a reminder engine — it must go through the fence-aware
API: `coga.taskfile.read_blackboard` / `replace_blackboard` to rewrite the
region, or `coga.blackboard.append_blackboard_report` / `append_to_section`
to append to it. Never `open(path, "a")` and never search or rewrite the whole
file. The fence matches only on a line of its own, so a bare append onto a
file whose last line is the fence glues the new text to the marker and every
reader of that ticket fails at once; a whole-file search mistakes body prose
for state. Pass captured `expected_bytes` to `read_blackboard` and
`replace_blackboard` (or `append_to_section`) to detect changed input;
`append_blackboard_report(cfg, ticket_path, report)` checks its own captured
bytes internally. Preserve the region's leading newline when replacing it.
For a file ending at the fence with no newline, begin the replacement or
report with the file's newline convention: `replace_blackboard` and
`append_blackboard_report` currently do not add that missing separator.

If the recurring task declares `state_keys:` in its frontmatter, those
keys are checked: when the run completes — `coga mark done`, or the `coga
bump` that closes the last step, whether an agent or a `ticket.py` ran it —
any declared key still
holding the value it had when this period started is flagged (a local
warning, an important Slack alert, and a `coga validate` issue) — the
signal that you did the work but forgot to record the new high-water mark,
so the next firing would redo the same range. Advance the key (the run's
record-state step) before finishing.

## Do not write last-run state to your own blackboard

Your own task blackboard (the region of your `ticket.md`) is fresh this period and gone next. Notes for
yourself within this run are fine there; cross-run state is not — nothing in
your task directory survives to the next firing.
