---
slug: recurring-sweep-wedges-on-the-ticket-py-it-copies
title: Recurring sweep wedges on the ticket.py it copies, then reports a clean run
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
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
step: 2 (evaluate-design)
launch_generation: f8fcec00-69d6-4909-9076-0f87cee19fc5
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

### Acceptance criteria

Objectively checkable by an implementer and a reviewer:

1. **No wedge in case 3.** A git-backed test constructs case 3 — a period task
   dir committed on control carrying `ticket.md` but *not* its sibling
   `ticket.py`, with a template that has one — and runs a sweep with that
   template due. The sweep lands the create: afterwards
   `coga/tasks/recurring/<name>/ticket.md` on disk is the current period's
   `active` ticket, `ticket.py` is present and tracked, and
   `git status --porcelain` is clean. No `[git] sync failed` is printed.
2. **The restore unwinds on a failed rebase.** A test that forces
   `_rebase_checked_out_branch_onto` to raise on the post-landing path asserts
   the working tree afterwards holds the *landed* period task, not the prior
   period's `done` ticket — i.e. the restore-to-`HEAD` is undone before the
   `GitError` propagates.
3. **A swallowed sync failure reaches the run record.** A sweep whose create
   sync raises `git.GitError` renders a `RunRecord` whose `- problems:` count is
   ≥ 1, whose `## Unresolved recurring failures` section names the period slug
   and the failure text, and whose process exit code is `2`. `problems: 0`
   alongside a `[git] sync failed` line is no longer reachable.
4. **The contradictory skip is refused at both render sites.** When a bare sweep
   creates (or replaces-done) a period task and the post-sync re-read observes
   it in `TERMINAL_STATUSES`, neither `_print_table` nor `scan_lines_for_record`
   prints `skip (done)` for that template. Both print an error action, the
   template is counted in `- problems:`, and the sweep exits non-zero.
   A test asserts the record text contains no `skip (done)` for a template the
   same record reports as created.
5. **`--force` is unaffected.** A forced sweep, which legitimately re-runs
   `done` period tasks, does not trip the contradiction detector. An existing
   `--force` test still passes unchanged.
6. **Context and twin updated.** If any of the above changes what
   `coga/contexts/coga/recurring/SKILL.md` asserts, it is updated in the same
   PR and its packaged twin under
   `src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/SKILL.md`
   is byte-identical (`tests/test_packaging.py` passes).
7. `PYTHONPATH=$PWD/src python3.12 -m pytest` is green.

### Proposed shape

**Sequencing decision: do not split.** The ticket offered a split and sequenced
(3) first. Design says ship all four together as one PR. The four edits touch
four functions between them, three of the four land in `_broadcast_scan` and the
two renderers, and the wedge fix (1) is ~15 lines once `_drop_untracked_paths_present_in`
exists. Shipping (3) alone would mean writing the contradiction detector, its
two render branches, and its `scan_problems` plumbing — then reopening all three
files a week later to add the sync-failure channel that uses the *same*
plumbing. The combined change is ~120 source lines plus tests. Order the work as
below; each stage is independently testable, so a stage that turns out harder
than budgeted can still be dropped at the last responsible moment.

#### Stage A — stop the wedge (outcome 1)

New helper in `src/coga/recurring_runner.py`, beside
`_restore_selected_paths_from_ref`:

```python
def _drop_untracked_paths_present_in(root: Path, ref: str, rels: list[str]) -> None:
```

For each `rel`, enumerate untracked files with
`git -C <root> ls-files --others --exclude-standard -- <rel>` and unlink each one
that `_ref_has_path(root, ref, <path>)` reports present in `ref`. Rationale: git
would happily overwrite the path if it were tracked; the refusal exists only to
protect untracked *user* files, and a path the adopted ref already owns is not
one. At both call sites `ref` is the commit the checkout is about to become, so
the deleted bytes are superseded, not lost.

Call it in the two restore/rebase pairs, between the restore and the rebase:

- `_sync_recurring_create_on_checked_out_control_branch` — the observed path.
  Target is `landed`.
- the `_control_already_has_period` short-circuit inside
  `_sync_recurring_create_paths` (`if branch == cfg.git_control_branch:`).
  Target is `base`.

#### Stage B — unwind a failed landing (outcome 4)

Only at the post-landing site. Stage A removes the observed collision; this
covers every *other* rebase failure, where the restore-to-`HEAD` has already
put the prior period's `done` ticket in place:

```python
_restore_selected_paths_from_ref(root, "HEAD", rels)
_drop_untracked_paths_present_in(root, landed, rels)
try:
    _rebase_checked_out_branch_onto(root, landed)
except git.GitError:
    # The rebase left the checkout on the pre-landing HEAD, whose create
    # paths are the *prior* period's completed task. Re-materialize them
    # from the commit that did land, so the sweep is not left running
    # against a resurrected ticket.
    _restore_selected_paths_from_ref(root, landed, rels)
    raise
```

`landed` is a local commit built by `_land_recurring_create_on_control_branch`,
so it always resolves. The short-circuit site gets no unwind: there the restore
*is* the intent (control already owns the period; the local create is being
discarded).

#### Stage C — a channel from a swallowed sync failure into the record (outcome 2)

**Design decision the ticket asked for: reuse `RunRecord.scan_problems`. Do not
add a `TaskOutcome` and do not add a new record field.** A `TaskOutcome` models a
launch (`result`, `exit_code`, `final_status`, `blackboard`); a sync failure has
none of those, and `is_problem` (`result != "completed"`) would be a lie about
something that never ran. A new field would need its own render section, its own
term in the `- problems:` sum, and its own exit-code wiring — three edits
duplicating what `scan_problems` already does today. Instead widen
`scan_problems`' docstring from "Failures inherited from earlier runs, not
launches in this sweep" to cover any failure observed outside the launch loop.
Its heading, "## Unresolved recurring failures", already reads correctly.

Plumbing, smallest to largest:

1. `_append_sync_failure(cfg, anchor_path, exc, *, sink: list[str] | None = None)`
   — appends `str(exc)` to `sink` when given. It is already the single funnel
   both handlers call, so this is the one place to widen.
2. `_sync_recurring_create_paths(..., sync_failures: list[str] | None = None)` —
   passed straight through to its `except git.GitError` handler's
   `_append_sync_failure` call.
3. `_sync_recurring_create(..., sync_failures: list[str] | None = None)` —
   forwards to the above and uses it in its own non-`GitError` backstop.
   Defaults to `None`, so the three call sites outside `_broadcast_scan`
   (`_run_delegated_task`, `_prepare_forced_launch`,
   `_record_forced_period_locally`) are unchanged.
4. New field on `DueScan` in `src/coga/recurring.py`, mirroring `errors`:
   `sync_problems: list[tuple[str, str]] = field(default_factory=list, repr=False)`
   — `(id_slug, detail)`, the exact shape `RunRecord.scan_problems` takes.
5. `_broadcast_scan` passes a fresh `list[str]` per task and, when it comes back
   non-empty, appends `(task.ref.id_slug, "; ".join(failures))` to
   `scan.sync_problems`.
6. `run_recurring_scan` seeds the record with it at construction, beside the
   existing `scan_errors=list(scan.errors)`:
   `scan_problems=list(scan.sync_problems)`. The watchdog loop below already
   appends to the same list, and both the `- problems:` sum and the two
   `return 2 if record.scan_problems` sites already read it — so outcomes 2's
   counting and exit code come free.

#### Stage D — refuse the contradictory skip (outcome 3)

The detector goes in `_broadcast_scan`, immediately after the existing post-sync
refresh `ticket = read_ticket(task.ref); task.status = ticket.status`. That line
is *why* the table lies: `task.created` is still `True` from `scan_due` while
`task.status` has just been re-read off the resurrected ticket. One site, ahead
of both renderers.

Condition — narrow on purpose:

```python
if (
    not sync_existing                      # --force/--all legitimately re-runs done tasks
    and (task.created or task.replaced_done)
    and ticket.status in TERMINAL_STATUSES
):
```

`TERMINAL_STATUSES` comes from `coga.lifecycle` (`{"done", "canceled"}`). Do not
extend it to `paused`: the watchdog path already owns that status and would
double-report.

Effects, all three:

- Set a new short field on `DueTask` (`src/coga/recurring.py`):
  `period_contradiction: str = ""`, e.g.
  `"created this period but ticket is {status}"`. The task stays in
  `scan.tasks` — it is not launchable (terminal status), so no launch-loop
  change is needed; it must stay so both renderers can print it.
- Append the long, actionable form to `scan.sync_problems`, so it counts in
  `- problems:` and drives exit 2 through Stage C's wiring:
  `f"{task.template} was created for period {task.period_key} but its ticket is "
   f"{ticket.status}; the control-branch landing did not complete and the prior "
   f"period's ticket is standing in for it. The period did not run."`
- Notify, mirroring the watchdog block already in `run_recurring_scan`:
  `kind="recurring-error"`, `important=True`, `fatal=False`. `fatal=False` is
  load-bearing — `_broadcast_scan` runs before the launch loop, and the comment
  on the `scan.errors` alert records that a notification crash here once took
  the whole sweep down.

Then add one branch to each renderer, placed **before** the generic
`skip ({task.status})` fallback in both:

- `_print_table` in `recurring_runner.py`:
  `typer.style(f"error ({task.period_contradiction})", fg=typer.colors.RED)`.
- `scan_lines_for_record` in `recurring_autofix.py`:
  `f"error ({task.period_contradiction})"`, no color — the record is read by an
  agent.

This also closes the ticket's one unverified link ("which renderer produced the
observed `skip (done)`"): both would have, they share `DueTask.status`, and both
are fixed.

#### Stage E — context

Re-read `coga/contexts/coga/recurring/SKILL.md` against the shipped behavior.
At minimum it should state that a sweep which creates a period task and then
observes it terminal reports an error rather than skipping, and that a git sync
failure during create now counts toward the sweep's `problems`. Sync the
packaged twin byte-for-byte.

#### Tests

`tests/test_recurring.py` (the `git_repo` fixture is already the right harness —
see `test_recurring_create_sync_restores_control_ledger_for_handled_period` for
the shape):

- `test_recurring_create_lands_with_untracked_period_script` — case 3, per
  acceptance 1. This is the reproduction the ticket says does not exist yet;
  write it **first and watch it fail** before Stage A, or the fix is unproven.
- `test_recurring_create_restores_landed_task_when_rebase_fails` —
  acceptance 2, monkeypatching `_rebase_checked_out_branch_onto` to raise.
- `test_recurring_sweep_reports_create_sync_failure_as_problem` —
  acceptance 3. `test_recurring_scan_launches_even_when_create_sync_crashes`
  and `test_recurring_create_sync_missing_git_is_soft` already build a failing
  sync; extend that setup and assert on the record instead of on stderr.
- `test_recurring_sweep_refuses_contradictory_done_skip` — acceptance 4,
  asserting on both `_print_table` output and `record.render()`.

`tests/test_recurring_autofix.py` — a unit test for the new
`scan_lines_for_record` branch.

### Out of scope

- **Making `scan_errors` count toward `- problems:`.** A template that fails to
  load is arguably a problem too, and today it renders under "## Template
  errors" without incrementing the count or the exit code. That is a
  pre-existing, separable judgment call; do not change it here.
- **Rewriting `_restore_selected_paths_from_ref`'s three-branch structure.** The
  `shutil.rmtree` branch is correct for case 1 and stays as it is; Stage A adds
  a sibling step rather than reshaping it.
- **A general `git clean` of recurring task directories.** The new helper
  deletes only untracked paths the adopted ref already owns. Broadening it to
  every untracked path would put `.state-snapshot.json` and any operator scratch
  file at risk, and `_is_generated_snapshot_status` exists precisely because the
  snapshot is treated as an ignorable local artifact.
- **Watchdog / paused-status reporting.** Untouched; the detector deliberately
  stops at `TERMINAL_STATUSES`.
- **`coga megalaunch`, the autofix analysis prompt, and the `[aliases]`
  surface.** No new CLI spelling and no new `runner.RECIPES` entry: every change
  here is inside existing shared infra.

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

### Verified during design (2026-09-10, at `aebfe867`)

Read the code; these are the facts the Proposed Shape rests on. Symbols only.

- **The lie is manufactured in `_broadcast_scan`, not in `scan_due`.**
  `scan_due` sets `DueTask.created` and reads `status` off the freshly created
  ticket (`active`). The git sync happens *later*, in `_broadcast_scan`, which
  then does `ticket = read_ticket(task.ref); task.status = ticket.status` — a
  re-read off the resurrected ticket. So after a wedged sweep the in-memory
  `DueTask` holds `created=True` **and** `status="done"` simultaneously. That
  single line is the contradiction site and it sits upstream of both renderers,
  which is why outcome (3) needs one detector rather than two.
- **`RunRecord` already has the channel outcome (2) needs.**
  `scan_problems: list[tuple[str, str]]` exists, is summed into
  `- problems: {len(self.problems) + len(self.scan_problems)}`, renders under
  `## Unresolved recurring failures`, and drives both
  `return 2 if record.scan_problems` sites. Today its only writer is the
  watchdog-recovery loop in `run_recurring_scan`. Outcome (2) is therefore a
  *feed*, not a new record concept — the ticket's "new record field vs
  `TaskOutcome`" framing has a third and better answer.
- **`RunRecord` is constructed after `_broadcast_scan` runs**, so the sync layer
  cannot write to it directly. `DueScan` is the carrier that already crosses
  that boundary (`scan_errors=list(scan.errors)`), which is why Stage C adds
  `DueScan.sync_problems` rather than passing the record down.
- **`scan_errors` is deliberately not a problem.** Template errors render under
  `## Template errors` and are excluded from both the `problems:` count and the
  exit code. Do not "fix" this in passing — see Out of scope.
- **The two restore/rebase sites, by symbol.** Post-landing (observed path):
  end of `_sync_recurring_create_on_checked_out_control_branch`, target
  `landed`. Short-circuit: inside `_sync_recurring_create_paths`, under
  `if _control_already_has_period(...)` then `if branch == cfg.git_control_branch:`,
  target `base`.
- **`_restore_selected_paths_from_ref` runs git's default no-overlay restore**,
  so it removes *tracked* files absent from the source ref but never touches
  untracked ones. That asymmetry is exactly case 3, and it is why Stage A adds
  an untracked-drop step instead of changing the restore.
- **`_append_sync_failure` is already the single funnel.** Both the
  `except git.GitError` handler in `_sync_recurring_create_paths` and the
  non-`GitError` backstop in `_sync_recurring_create` call it, so one `sink`
  parameter covers both.
- **`_sync_recurring_create` has three call sites besides `_broadcast_scan`** —
  `_run_delegated_task`, `_prepare_forced_launch`,
  `_record_forced_period_locally`. A defaulted `sync_failures=None` leaves all
  three untouched.
- **`TERMINAL_STATUSES` is `frozenset({"done", "canceled"})` in
  `coga.lifecycle`**, already imported across the tree.
- **The `git_repo` pytest fixture is the right harness.** It gives a real repo
  with an `origin`, and `test_recurring_create_sync_restores_control_ledger_for_handled_period`
  is a working example of driving `_sync_recurring_create` against it. Case 3 is
  constructible there today.

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

## Design step — 2026-09-10

Spec written into `## Description` (`### Acceptance criteria`,
`### Proposed shape`, `### Out of scope`) and the code facts it rests on into
`## Context` (`### Verified during design`). No branch, no code.

**Ticket kept whole — recommending against the split the ticket invited.**
The ticket sequenced outcome (3) first as self-contained. Reading the code
changed that: outcomes (2) and (3) share one mechanism. `RunRecord` already
carries `scan_problems`, summed into `problems:` and wired to exit 2; both
outcomes are feeds into it, and both feed through the same new
`DueScan.sync_problems` carrier because `RunRecord` is built after
`_broadcast_scan` runs. Shipping (3) alone means building that plumbing and
reopening the same three files for (2). Outcome (1) is ~15 lines once the
untracked-drop helper exists, and (4) collapses to a 3-line `except` that
re-restores from `landed`. Whole thing is ~120 source lines plus tests.

**Key finding that simplified the design.** The contradiction is manufactured in
exactly one place: `_broadcast_scan` re-reads the ticket after the sync
(`task.status = ticket.status`) while leaving `task.created` True. One detector
there sits upstream of both render sites, so outcome (3) does not need two
independent fixes — only two render *branches* off one flag. This also answers
the ticket's one open provenance link: both renderers would have printed
`skip (done)`, because both read the same `DueTask.status`.

**Design decision recorded (the one the ticket said to budget for).** A
swallowed sync failure is neither a `TaskOutcome` nor a new `RunRecord` field —
it reuses `scan_problems`, whose docstring widens from "failures inherited from
earlier runs" to "failures observed outside the launch loop". A `TaskOutcome`
would have to lie via `is_problem` (`result != "completed"`) about something
that never ran; a new field would duplicate the render section, the `problems:`
term, and the exit-code wiring that `scan_problems` already has.

**Instruction to the implementer, load-bearing:** write
`test_recurring_create_lands_with_untracked_period_script` (case 3) *first* and
watch it fail before touching Stage A. No template in this tree is currently in
case 3, so without a failing reproduction the fix is unverified — and the
ticket warns that the naive reproduction recipe will mislead you into
concluding the bug is already fixed.

## Open Questions

For `review-design`. None blocks implementation; each has a stated default in
the spec.

1. **Should the contradiction notify Slack?** Spec says yes —
   `kind="recurring-error"`, `important=True`, `fatal=False`, mirroring the
   watchdog-recovery block. Argument for: a scheduler that silently stops
   running is exactly the thing worth waking someone for, and it recurs every
   sweep until a human intervenes. Argument against: `_broadcast_scan` runs
   before the launch loop and already carries a scan-errors alert, so this adds
   a second pre-launch notification surface. Owner may prefer stderr + the run
   record only.
2. **How broad should the untracked-drop be?** Spec deletes any untracked file
   under the create pathspec that the rebase target already contains — the rule
   git itself would apply if the file were tracked. Narrower alternatives:
   delete only when the bytes match the target's, or only the reserved
   `SCRIPT_ENTRY_POINT` name. The general rule is simpler and generalizes past
   `ticket.py`; the narrow one is harder to get wrong. I recommend the general
   rule because at both call sites the target is a commit the checkout is about
   to become.
3. **Should `scan_errors` count toward `problems:` too?** Noticed while tracing
   outcome (2): a template that fails to load renders under "## Template
   errors" but increments neither the count nor the exit code, so the autofix
   analyst reads `problems: 0` for a sweep where a template never loaded. Same
   class of blind spot as this ticket, different trigger. Spec puts it out of
   scope. Confirm that, or say to fold it in.
