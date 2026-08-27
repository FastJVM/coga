---
slug: recurring-sweep-wedges-on-the-ticket-py-it-copies
title: Recurring sweep wedges on the ticket.py it copies, then reports a clean run
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- coga/recurring
- coga/codebase
skills: []
workflow: null
secrets: null
---

## Description

A `coga recurring` sweep can create a due period task, fail to land it on the
control branch, silently restore the *previous* period's completed ticket over
it, and then report `tasks run: 0`, `problems: 0`, "No recurring tasks due" —
while the jobs that were due never ran.

Observed in `FastJVM/admin` on 2026-08-26: `autoclose-merged` (`0 8 * * *`) and
`digest` (`0 9 * * *`) were both shown `ready` in the scan table and neither
fired. It recurs every sweep until a human cleans up by hand.

## The mechanism

Four shipped behaviours compose into it. Each is individually reasonable.

**1. Every firing manufactures an untracked file.**
`recurring.py:985` — `shutil.copyfile(entry, out_ref.task_dir / SCRIPT_ENTRY_POINT)`
copies the template's reserved `ticket.py` into the period task directory,
exactly as `recurring.py:88` documents ("copied into every period task"). Until
something commits it, that file is untracked inside a task directory.

**2. The control-branch landing restores, then rebases.**
`recurring_runner.py:1416-1417`:

```python
_restore_selected_paths_from_ref(root, "HEAD", rels)
_rebase_checked_out_branch_onto(root, base)
```

The same pair appears again at `1731-1732`.

**3. The rebase cannot detach past an untracked file.**
`recurring_runner.py:2038` runs the rebase with `-c rebase.autoStash=true`.
Autostash covers *tracked* modifications only; an untracked file that checkout
would overwrite aborts the detach. So step 1's own artifact defeats step 2:

```
[git] sync failed: could not rebase checked-out control branch onto <sha>:
error: The following untracked working tree files would be overwritten by
checkout:; error: could not detach HEAD
```

The restore has already run at that point, so the tree is left holding the
*prior* period's `done` ticket, with no unwind.

**4. The failure is non-fatal by design, and the skip line believes the
resurrected state.** `recurring_runner.py:1315` and `:1519` catch the
`GitError`, write it to stderr, call `_append_sync_failure`, and continue. The
comment at `:1310-1313` states the rationale explicitly — the created task on
disk is the source of truth, so a sync miss should not abort the caller. That
tradeoff is defensible; what it does not anticipate is the restore having
already replaced the task the reasoning depends on. Nothing increments a
problem counter, so the sweep still exits `problems: 0`.

`_print_table` at `:2633` then renders `skip ({task.status})` from the restored
ticket, printing `skip (done)` for a period the same sweep created seconds
earlier.

## Why the state is provably wrong, not just unlucky

After the failed sweep, `git diff HEAD -- coga/tasks/recurring/` is empty and
the tickets carry `status: done` with a blackboard whose newest entry is the
*previous* day's run. A task a sweep just created for today's period cannot
already be `done` for that period. That contradiction is the cheapest available
detector.

## What a fix has to do

1. **Stop the wedge.** The `ticket.py` a period task materializes should be
   part of the same tracked pathspec set as its `ticket.md`, or be excluded
   from the paths the restore and rebase touch — so a sweep cannot collide with
   the artifact a previous sweep left behind.
2. **Make the failure loud.** A `[git] sync failed` raised while servicing a due
   template should increment the sweep's `problems` count and reach the run
   record. `problems: 0` alongside two logged sync failures is why this went
   unnoticed for a day.
3. **Refuse the contradictory skip.** When a sweep creates a period task and
   then observes it `done` for that same period, report an error rather than
   `skip (done)`.
4. **Unwind cleanly.** If the landing cannot complete, the restore should not
   leave the prior period's completed ticket standing in for the current one.

(1) and (3) are independent — (3) alone converts a silent skip into a visible
failure even if the wedge remains possible.

## Reproducing

Leave an untracked file inside a recurring period task directory and run a
sweep with a due daily template. The sweep must either land the create or
report a problem, and must never print `skip (done)` for a period it just
created.

## Provenance

Diagnosed in `FastJVM/admin` by its `coga recurring` autofix loop
(`autofix/unwedge-recurring-sync-so-digest-and-autoclose-sto`, now canceled
there as an upstream defect), then re-verified line-by-line against this tree
before filing — every reference above was confirmed in the current source, and
the second restore/rebase pair at `1731-1732` was found during that check
rather than in the original report. Filed as a draft per
`FastJVM/admin`'s `admin/carry-three-verified-coga-bugs-upstream` precedent;
activate with `coga mark active` and pick a workflow.

## Context

The local symptom in `FastJVM/admin` was cleared by hand (the shims are tracked
there now), so there is no live outage driving this. The structural exposure
remains: every shimmed template copies a fresh `ticket.py` on every firing, so
any template whose shim is not yet committed reopens the same window.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
