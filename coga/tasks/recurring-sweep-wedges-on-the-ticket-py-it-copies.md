---
slug: recurring-sweep-wedges-on-the-ticket-py-it-copies
title: Recurring sweep wedges on the ticket.py it copies, then reports a clean run
status: active
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/codebase
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (design)
---

## Description

A `coga recurring` sweep can create a due period task, fail to land it on the
control branch, silently restore the *previous* period's completed ticket over
it, and then report `tasks run: 0`, `problems: 0`, "No recurring tasks due" —
while the jobs that were due never ran.

Observed in `FastJVM/admin` on 2026-08-26: `autoclose-merged` (`0 8 * * *`) and
`digest` (`0 9 * * *`) were both shown `ready` in the scan table and neither
fired. It recurs every sweep until a human cleans up by hand.

Everything below is `###` on purpose. `compose._extract_section` inlines only
the `## Description` and `## Context` sections and stops at the next `##`, so a
top-level heading here would drop the rest of this ticket out of the launched
prompt. Keep new sections at `###`.

### The mechanism

Four shipped behaviours compose into it. Each is individually reasonable.

Symbol names, not line numbers: every one of the eight line citations in the
original filing rotted within six commits, and the two restore/rebase sites
moved another ~106 lines in the merge after that. Do not reintroduce numbers.

**1. Every firing manufactures an untracked file.** `_create_at_slug` in
`src/coga/recurring.py` runs
`shutil.copyfile(entry, out_ref.task_dir / SCRIPT_ENTRY_POINT)`, copying the
template's reserved `ticket.py` into the period task directory. Until something
commits it, that file is untracked inside a task directory.

**2. The control-branch landing restores, then rebases.**
`_sync_recurring_create_on_checked_out_control_branch` in
`src/coga/recurring_runner.py` ends with:

```python
_restore_selected_paths_from_ref(root, "HEAD", rels)
_rebase_checked_out_branch_onto(root, landed)
```

`rels` is `[ref.path, template_ticket]`, where `ref.path` is the *task
directory*. A near-identical pair also sits in the `_control_already_has_period`
short-circuit — but **the post-landing pair above is the one on the observed
path.** Fix that one first; the original filing had these two the wrong way
round.

**3. The rebase cannot detach past an untracked file.**
`_rebase_checked_out_branch_onto` runs with `-c rebase.autoStash=true`.
Autostash covers *tracked* modifications only; an untracked file that checkout
would overwrite aborts the detach, so step 1's own artifact defeats step 2:

```
[git] sync failed: could not rebase checked-out control branch onto <sha>:
error: The following untracked working tree files would be overwritten by
checkout:; error: could not detach HEAD
```

The restore has already run at that point, so the tree is left holding the
*prior* period's `done` ticket, with no unwind.

**4. The failure is non-fatal by design, and the skip line believes the
resurrected state.** `_sync_recurring_create_paths` catches `git.GitError`,
writes it to stderr, calls `_append_sync_failure`, and continues. The tradeoff
is defensible — the created task on disk is the source of truth, so a sync miss
should not abort the caller — but it does not anticipate the restore having
already replaced the task that reasoning depends on.

Note the neighbouring handler is **not** a second copy of this behaviour: it
catches `Exception` while *specifically excluding* the GitError case, and its
own comment says `_sync_recurring_create_paths` "already degrades on GitError."
Its backstop is for subprocess, OS, and racing-push failures. Treat them as two
different handlers when sizing a change.

Nothing increments a problem counter. `_append_sync_failure` only appends a
line to the repo-global `coga/log.md` — its docstring is literally
`"""Best-effort global-log note for non-fatal git sync failures."""` — while
`RunRecord.problems` in `src/coga/recurring_autofix.py` is
`[o for o in self.outcomes if o.is_problem]`, and outcomes are appended only for
tasks that were actually *launched*. **There is no channel of any kind from a
swallowed sync failure into the run record.**

The scan table then renders `skip ({task.status})` from the restored ticket,
printing `skip (done)` for a period the same sweep created seconds earlier.

### Why the state is provably wrong, not just unlucky

After the failed sweep, `git diff HEAD -- coga/tasks/recurring/` is empty and
the tickets carry `status: done` with a blackboard whose newest entry is the
*previous* day's run. A task a sweep just created for today's period cannot
already be `done` for that period. That contradiction is the cheapest available
detector.

There is a proven in-tree precedent for exactly this detector shape:
`_template_damage` in `recurring_runner.py`, added to catch a firing that
overwrites its own recurring template. Its docstring describes the identical
failure pattern — the run "still reached `done`, so the sweep called it
`completed` and reported `problems: 0`" — and states the remedy to copy here:
*"Compare the bytes instead of trusting the lifecycle status."*

### What a fix has to do

1. **Stop the wedge.** The `ticket.py` a period task materializes should be
   part of the same tracked pathspec set as its `ticket.md`, or be excluded
   from the paths the restore and rebase touch — so a sweep cannot collide with
   the artifact a previous sweep left behind. Note this interacts with three
   distinct branches of `_restore_selected_paths_from_ref`, one of which
   `shutil.rmtree`s a directory; see the precondition analysis in `## Context`.
2. **Make the failure loud.** A `[git] sync failed` raised while servicing a due
   template should increment the sweep's `problems` count and reach the run
   record. `problems: 0` alongside two logged sync failures is why this went
   unnoticed for a day. This is **not** a counter bump: it needs a new channel
   from the sync layer into `RunRecord`, plus a decision about whether a sync
   failure is a `TaskOutcome` (it carries no task result) or a new record field.
   Budget a design decision.
3. **Refuse the contradictory skip.** When a sweep creates a period task and
   then observes it `done` for that same period, report an error rather than
   `skip (done)`. There are **two independent render sites** — see
   `## Context` — and fixing only the console one leaves the run record, which
   is what the analyst agent actually reads, still asserting `skip (done)`.
4. **Unwind cleanly.** If the landing cannot complete, the restore should not
   leave the prior period's completed ticket standing in for the current one.
   Consider whether (1) subsumes this: if the collision cannot happen there is
   nothing to unwind, and if it still can, this needs its own design rather
   than a sentence.

### Sequencing

**Ship (3) first**, as a self-contained change. It is small, carries no design
risk, and — unlike (1) — is testable in this tree today, because the
contradiction it detects can be constructed directly without reproducing the
git collision. It converts a silent skip into a visible failure even if the
wedge remains possible.

Then take (1) + (4) together as the structural fix, with (2) as its
observability half. Splitting this ticket is a reasonable outcome of the design
step; it was kept whole because the mechanism above is shared by all four.

## Context

### Preconditions — when this actually fires

The precondition is narrower than "any template whose shim is not yet
committed", which is what the original filing claimed and is **wrong**. Working
through `_restore_selected_paths_from_ref`, there are three cases:

1. **HEAD has neither the period task dir nor its `ticket.py`** — `_ref_has_path`
   returns False, so the restore takes the `git rm --cached` + `shutil.rmtree`
   branch and deletes the whole freshly-created task directory, untracked
   `ticket.py` included. The rebase has nothing to collide with. **No wedge.**
2. **HEAD has the dir and a tracked `ticket.py` inside it** — the copy
   overwrote a tracked file, so it is an ordinary tracked modification. Restore
   reverts it; nothing is untracked. **No wedge.**
3. **HEAD has the dir but *not* `ticket.py` inside it** — restore rewrites the
   dir's tracked files and leaves the untracked `ticket.py` alone (restore only
   writes paths present in the source ref), while the rebase target *does*
   contain `ticket.py`. The detach refuses to overwrite an untracked working
   tree file. **Wedge.**

Case 3 is precisely the shim-migration window: a period task dir already
tracked from before `df1d0602` (#705, "Migrate recurring templates to
`ticket.py` shims and delete `recipe:`") whose first post-migration firing drops
an untracked `ticket.py` into it. That matches the `FastJVM/admin` report
exactly, including its reported remedy ("the shims are tracked there now").

**No template in this tree is currently in case 3.** `autoclose-merged`,
`blocker-reminders` and `digest` are case 2 (tracked period `ticket.py`);
`branch-sweep` and `skill-update` have no tracked period dir at all, so they are
case 1 and are the two nearest the window. `dream` and `resolve-conflicts` are
agent-backed with no `ticket.py`, so they never copy a script and cannot wedge.

Treat this as a **latent defect with a specific, nameable trigger**, not an
ambient one-firing-away hazard. It reopens at the next shim migration, or if
someone commits a period `ticket.md` without its sibling `ticket.py`.

### Reproducing

The original recipe ("leave an untracked file inside a recurring period task
directory") is insufficient and will mislead you into concluding the bug is
already fixed. An arbitrary untracked filename does **not** trigger it: the
collision requires the untracked path to also exist in the rebase target, which
only happens for the reserved name `ticket.py` that the landing itself just
committed.

Construct case 3 deliberately: commit a period `ticket.md` on control **without**
its sibling `ticket.py`, then run a sweep with that template due. The sweep must
either land the create or report a problem, and must never print `skip (done)`
for a period it just created.

### Where the code lives

- `src/coga/recurring.py` — `_create_at_slug` copies the template `ticket.py`.
- `src/coga/recurring_runner.py` —
  `_sync_recurring_create_on_checked_out_control_branch` (the post-landing
  restore/rebase pair on the observed path),
  `_restore_selected_paths_from_ref`, `_rebase_checked_out_branch_onto`,
  `_sync_recurring_create_paths`, `_append_sync_failure`, `_template_damage`
  (the precedent detector), and the console scan table's `skip ({task.status})`.
- `src/coga/recurring_autofix.py` — **the second edit site, and the one the
  original filing missed entirely.** It owns `RunRecord`, the `problems`
  property, and `scan_lines_for_record`, which has its own separate
  `skip ({task.status})` rendering. The split is deliberate: the console gets
  colour, the record gets stable greppable text because an agent reads it.
  Outcomes (2) and (3) both need changes here as well as in the runner.

### What you need from the `coga/recurring` context

That context is deliberately **not** attached — this fix will almost certainly
edit it, and attaching it would cost ~58.7 KiB (~15k tokens, 56% of the composed
prompt) on every step to inline a file the agent opens anyway. Read it directly
at `coga/contexts/coga/recurring/SKILL.md`. The load-bearing facts:

- A template carrying the reserved sibling `ticket.py` is deterministic and runs
  headlessly; one without it is agent-backed. This is deduced from the file, not
  configured.
- That `ticket.py` is copied into **every** period task on every firing. This is
  the artifact at the centre of the bug.
- Every firing uses the stable path `coga/tasks/recurring/<name>/`; there is one
  instantiated task per template.
- The repo-global `coga/log.md` is the serviced-period high-water mark, not the
  template blackboard — deliberately, because every other writer of that region
  can clobber a mark placed there.
- Dream is the janitor that reaps completed period tasks; the scheduler deletes
  a stale prior-period task before creating the fresh one.

Update that context in the same PR if any of the four outcomes changes what it
asserts — the repo rule is that behaviour changes and their contexts land
together. Check the packaged twin under
`src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/SKILL.md`
too; `tests/test_packaging.py` requires byte-identity.

### Provenance

Diagnosed in `FastJVM/admin` by its `coga recurring` autofix loop
(`autofix/unwedge-recurring-sync-so-digest-and-autoclose-sto`, canceled there as
an upstream defect), then filed here as a draft per that repo's
`admin/carry-three-verified-coga-bugs-upstream` precedent.

Re-verified against this tree at `6224faf0` (#777). The mechanism holds end to
end; #777 did not overlap it despite touching the same modules under a
closely-related title. One unverified link remains in the chain: the report
never established **which** of the two scan renderers produced the observed
`skip (done)` line. Not load-bearing for the diagnosis, but worth closing.

The local symptom in `FastJVM/admin` was cleared by hand, so there is no live
outage driving this and no reproduction in this tree — see the precondition
analysis above before concluding the report is stale.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
