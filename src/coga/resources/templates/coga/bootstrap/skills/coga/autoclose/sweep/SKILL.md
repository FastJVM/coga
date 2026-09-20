---
name: coga/autoclose/sweep
description: Close final-step Coga tickets whose linked GitHub PR has merged.
---

# Autoclose Merged Tickets

This skill documents the merged-ticket auto-close sweep behind the
`recurring/autoclose-merged/` ticket. That ticket's `ticket.py` runs the
registered `autoclose` recipe (`coga.autoclose.run_autoclose_recipe`)
through `coga.runner.run_recipe` — no agent, no composed prompt — and the
same sweep is available as `coga run autoclose`. It is the
sole trigger for closing tickets whose PR has merged:

1. scan active and in-progress tickets,
2. read each ticket blackboard's `## Dev` `pr:` link,
3. check the linked PR state with `gh pr view`, and
4. mark the ticket `done` only when it is on its final workflow step, or has no
   workflow, and the PR is merged, and
5. report the `coga retire` follow-up for every ticket it closed that still
   records a `branch:`, or a `worktree:` retire could actually remove, under
   `## Dev`, and — under a recurring period task — record it in the template's
   durable `retires.md` worklist.

The scope is defined by `coga.autoclose.sweep_merged`.
Mid-workflow merges stay untouched because they are suspicious and need a human
to finish the ticket explicitly.

## The retire follow-up

Closing a ticket does not dispose of its feature checkout — `coga retire` does,
and it owns the safety proofs (same-repo linked worktree, no other live ticket
sharing it, no open PR for the head, branch landed at the recorded merged head).
Autoclose stays non-destructive and only *names* that follow-up, because
implicit destruction cuts against the principle that destructive behavior is
never implicit. Dream likewise leaves a checkout-bearing done ticket in place,
so the named command and the `## Dev` evidence it consumes remain valid until a
human retires it — the *evidence* is durable on the ticket, and the list of
follow-ups is durable in the worklist (see below).

Three surfaces. The first two are per-run and silent when the sweep stranded
nothing; the third is the durable worklist:

- a `## Autoclose Sweep: retire follow-ups` section listing the exact
  `coga retire <slug>` per ticket — appended to the task blackboard when run
  under a task, written to stdout otherwise. **That surface is per-run, not a
  worklist.** Autoclose's only recurring caller is `recurring/autoclose-merged`,
  and the `coga/recurring` context is explicit that a period task's blackboard
  is scratch space for one firing, deleted with the task the next period. The
  sweep only rediscovers tickets it closes in the *current* run, so a stranded
  checkout is never re-listed there; the section exists so the run record and
  the autofix analyst see what the run did, and under a period task it names
  the worklist below;
- one trailing Slack line for the whole sweep. The per-ticket `🎉 ... merged`
  line is left alone: it announces a lifecycle event, while a retire hint is
  an operational to-do;
- **the durable worklist `retires.md` beside the recurring template's
  `ticket.md`** — `coga/recurring/<name>/retires.md`, the template being the
  one the period task under `coga/tasks/recurring/<name>/` was minted from,
  never a hardcoded `autoclose-merged`. `coga.retire_worklist` owns the file;
  the sweep reconciles it on **every** recurring run, closures or not: it
  records each new follow-up keyed by task slug (re-recording one refreshes
  the branch and worktree it names and keeps the first sighting's date), and
  drops every entry that is **discharged** — its recorded worktree is no longer
  outstanding *and* its recorded branch is no longer a local branch. Either
  half still to dispose of keeps the entry, and a branch list that cannot be
  read keeps every entry: the failure mode is one listing too many, never a
  forgotten checkout. `coga retire <slug>` drops its own line by the same rule
  once its cleanup has really disposed of the checkout; a retire that
  *preserved* the checkout (the worktree is the invoking checkout, another
  ticket claims it, cleanup failed) keeps the line even though it goes on to
  delete the ticket, so that entry's `coga retire <slug>` no longer resolves —
  dispose of the recorded worktree and branch by hand, or let the weekly
  branch sweep take the branch, and the entry clears by the same rule. A
  worklist the sweep cannot safely rewrite, including a filesystem or text
  encoding failure, fails the run (exit 2) only after
  the per-run report and Slack line are emitted. If the task blackboard also
  fails with an I/O or encoding error, the report falls back to stdout and
  the run still fails, so a refused durable record never hides the follow-up
  on every surface. The reconcile is a
  barrier-held, compare-and-swap, atomic rewrite; the file is `merge=union`
  like `log.md`, and a line union merge resurrects or duplicates is healed by
  the next reconcile. A run that recorded, refreshed, or dropped nothing, and
  has no open entries, prints nothing about the file; otherwise stdout carries
  one `[autoclose] retire worklist <path>: N open, ...` line. Outside a
  recurring period task — a hand-run `coga run autoclose`, or a task that is
  not `tasks/recurring/<name>/` — no worklist is touched. Each line reads
  ``- `<slug>` — branch `<branch>`, worktree `<path>`, recorded `<YYYY-MM-DD>` ``
  under a `## Follow-ups (open)` heading. Field values use UTF-8 percent
  encoding, retaining `/` and `:`: for example, a backtick is `%60`, a literal
  percent is `%25`, and a space is `%20`. Decode the fields before using the
  recorded path or branch; use the same encoding when hand-editing or
  backfilling. A malformed line fails the sweep loudly rather than growing a
  second section nobody would find.

### Only a checkout retire can remove counts

A recorded `worktree:` is outstanding while it is a directory that is — or
still might be — a **linked worktree of this repository**. That is the one
shape `coga retire` removes; it preserves the primary checkout, an independent
fallback clone, and another repository's worktree by design. So a ticket worked
in the single-checkout layout records the primary checkout as its own
`worktree:`, and naming that as retire debt asks for a disposal that can never
happen: before this rule such an entry stayed listed forever, because the
primary checkout is always a directory.

Both halves apply it, through one probe, so they cannot disagree: the sweep
declines to record such a path at all (a ticket with a live branch still gets a
branch-only follow-up; one with neither gets none), and an entry already on
disk stops counting its worktree half and clears as soon as its branch is gone
— no hand edit of `retires.md`. Unknowns keep counting, as everywhere else
here: a relative path with no git root to anchor it, or a checkout `git` cannot
answer for.

Autoclose still never removes a worktree or branch. Recording a follow-up and
destroying a checkout stay separate: the worklist names the retire, and
`coga retire` runs the safety proofs when a human types it.

Run it directly with `coga run autoclose`. Live notification configuration is
preflighted before each affected ticket closes. Later `gh` or task-validation
failures remain hard failures, but any earlier closures are still reported.
After the report exists, a transiently undeliverable retire summary is
non-fatal and is recorded against the period task in the repo-global log.
