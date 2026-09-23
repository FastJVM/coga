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
   workflow, and the PR is merged,
5. dispose of the feature checkout of every ticket it closed that still
   records a `branch:` or `worktree:` under `## Dev`, and of every open entry
   in every `retires.md` worklist, under the shared retire proofs, and
6. report what it disposed of and what a proof refused, with the reason —
   the refusals to the coga-important Slack channel and, under a recurring
   period task, to the template's durable `retires.md` worklist.

The scope is defined by `coga.autoclose.sweep_merged` (the close) and
`coga.autoclose._dispose_checkouts` (the disposal).
Mid-workflow merges stay untouched because they are suspicious and need a human
to finish the ticket explicitly.

## The retire follow-up

Closing a ticket also disposes of its feature checkout, under exactly the
proofs `coga retire` runs — both call the shared `coga.checkout_disposal`
orchestration over `branchcleanup`. The earlier design only *named* a
`coga retire <slug>` follow-up here, on the principle that destructive
behavior is never implicit; that produced a ten-entry backlog nobody typed
(the recurring clone was carrying 45 linked worktrees), so the sweep now runs
the deterministic, narrow, named rule itself. This section names it.

**The proofs, in order, per checkout.** Each refusal preserves the checkout and
carries its reason into every surface below:

1. *No other live ticket claims it.* No non-terminal ticket in any Coga
   workspace of the git repository records the same `branch:` or the same
   `worktree:` path. A scan that cannot complete (an unreadable workspace or
   ticket) counts as a refusal.
2. *The worktree is disposable.* The recorded path is a linked worktree of
   the checkout the sweep runs from (`branchcleanup._is_linked_worktree_of`
   over `git.classify_checkout` — an independent clone, another repository's
   linked worktree, and anything git cannot answer for are preserved; the
   primary checkout is not debt at all, below), it is not the checkout
   running the sweep, it holds the
   recorded branch, and it carries no tracked or untracked local state
   (ignored regenerable caches — `__pycache__/`, `.pytest_cache/`,
   `.ruff_cache/`, `.mypy_cache/` — are deleted with it; any other ignored
   file preserves it). No PR is open for the branch, and the branch has
   landed on the control branch or its local and remote tips equal the merged
   PR's exact head. Then `git worktree remove`, unforced.
3. *The local branch.* Plain `git branch -d` when the tip is reachable from
   the control branch; a logged `-D` when the merged PR's exact head vouches
   for it (the squash-merge shape), re-reading the tip first. A branch still
   checked out anywhere, or with an open PR, or that advanced past the merged
   head, is preserved.
4. *The remote branch.* Deleted only when the live remote tip equals the
   merged PR's exact head, with a `--force-with-lease` on that tip, and only
   after the local branch is gone.

The merge signal is the ticket's `pr:` link. A worklist entry whose ticket
retire already deleted has none, so the proofs then use the merged PRs for
the recorded **head branch name** (`gh pr list --head <branch> --state
merged`) — the lookup the branch sweep already trusts — and compare the same
exact heads.

**Only from the control branch, only this clone's worktrees.** A hand-run
`coga run autoclose` on a checkout that is not on `[git].control_branch`
closes tickets as usual but preserves every recorded checkout and says so
(`[autoclose] checkout disposal skipped (...)`): the claim scan reads that
checkout's tickets and the branch proofs its refs. `coga recurring` services
deterministic phases from a checkout on the control branch, so the scheduled
run meets the guard. The sweep only ever touches worktrees a ticket or a
worklist entry recorded, and only those linked to the clone it runs from: in
this repo the recurring jobs run from `/home/n/Code/claude/coga`, whose
`/home/n/Code/claude/coga-<branch>` worktrees are what the worklist names.
Other clones' worktrees are preserved as independent clones and need their
own `coga run branch-sweep`.

**Four surfaces.** The first three are per-run and silent when the run touched
no checkout; the fourth is the durable worklist:

- a `## Autoclose Sweep: retire follow-ups` section — appended to the task
  blackboard when run under a task, written to stdout otherwise — listing each
  checkout disposed of, and each preserved one with its reason, the proof
  notes, and the manual remedy (`CheckoutOutcome.manual_command`; see
  *Remedies a human can act on* below). **That
  surface is per-run, not a worklist.** Autoclose's only recurring caller is
  `recurring/autoclose-merged`, and the `coga/period-task` context is explicit
  that a period task's blackboard is scratch space for one firing, deleted
  with the task the next period; the section exists so the run record and the
  autofix analyst see what the run did, and under a period task it names the
  worklist below. When the disposal phase never ran (off the control branch,
  or the sweep failed first), the section names `coga retire <slug>` per
  closed ticket as it did before;
- one coga-flow Slack line naming what the run disposed of;
- one **coga-important** Slack line naming every checkout a proof refused,
  with its reason — and, for a worktree refused as not linked here, its
  remedy, since the generic refusal cannot say where to act. A preserved checkout is work a human must do — the proofs
  will refuse it again tomorrow — which is the `coga/important` bar, so it is
  re-posted on every run until the cause is fixed and the entry clears. The
  per-ticket `🎉 ... merged` line is left alone: it announces a lifecycle
  event, while a disposal summary is operational;
- **the durable worklist `retires.md` beside the recurring template's
  `ticket.md`** — `coga/recurring/<name>/retires.md`, the template being the
  one the period task under `coga/tasks/recurring/<name>/` was minted from,
  never a hardcoded `autoclose-merged`. `coga.retire_worklist` owns the file.
  On **every** run, hand-run or recurring, the sweep walks the open entries of
  every worklist and runs the proofs above on each — that is how the backlog
  drains without a hand-typed retire per entry — and then reconciles each
  file: under a period task it records that run's preserved closures keyed by
  task slug (re-recording one refreshes the branch and worktree it names and
  keeps the first sighting's date), and everywhere it drops every entry that
  is **discharged** — its recorded worktree path is no longer a directory
  (or is this repository's own primary checkout, below) *and* its recorded
  branch is no longer a local branch. Either half still to dispose of keeps
  the entry, and a branch list that cannot be read keeps every
  entry: the failure mode is one listing too many, never a forgotten
  checkout. `coga retire <slug>` drops its own line by the same rule once its
  cleanup has really disposed of the checkout; a retire that *preserved* the
  checkout keeps the line even though it goes on to delete the ticket, and the
  next sweep re-judges that entry by head branch name. A worklist the sweep
  cannot safely rewrite, including a filesystem or text encoding failure,
  fails the run (exit 2) only after the per-run report and Slack lines are
  emitted (its backlog is not walked that run). If the task blackboard also
  fails with an I/O or encoding error, the report falls back to stdout and the
  run still fails, so a refused durable record never hides the follow-up on
  every surface. The reconcile is a barrier-held, compare-and-swap, atomic
  rewrite; the file is `merge=union` like `log.md`, and a line union merge
  resurrects or duplicates is healed by the next reconcile. A run that
  recorded, refreshed, or dropped nothing, and has no open entries, prints
  nothing about the file; otherwise stdout carries one
  `[autoclose] retire worklist <path>: N open, ...` line per file. A hand-run
  `coga run autoclose` never *records* a new entry — there is no period task
  to own one — but it drains and prunes every existing worklist. Each line
  reads
  ``- `<slug>` — branch `<branch>`, worktree `<path>`, recorded `<YYYY-MM-DD>` ``
  under a `## Follow-ups (open)` heading. Field values use UTF-8 percent
  encoding, retaining `/` and `:`: for example, a backtick is `%60`, a literal
  percent is `%25`, and a space is `%20`. Decode the fields before using the
  recorded path or branch; use the same encoding when hand-editing or
  backfilling. A malformed line fails the sweep loudly rather than growing a
  second section nobody would find.

### The primary checkout is not debt

A recorded `worktree:` is debt while somebody still has to dispose of it.
Exactly one recorded path never is: **this repository's own primary
checkout**. A ticket worked in the single-checkout layout records it as its
own `worktree:`; the worktree proof refuses it forever (it is always a
directory and never a linked worktree), and nobody deletes it. Counted as
debt, such an entry was preserved, re-posted to coga-important on every run,
and — once retro deleted the ticket — told a human to dispose of the repo by
hand.

Both halves apply one probe, `retire_worklist.is_primary_checkout` over
`git.classify_checkout`, so they cannot disagree: a closure drops the
worktree half before the proofs run (a live branch still gets a branch-only
follow-up; neither gets none), and an entry already on disk stops counting
its worktree half and clears once its branch is gone — no hand edit of
`retires.md`. The verdict compares common git dirs, so it holds when the
sweep runs from a recurring control worktree rather than the primary
checkout. Every unknown keeps the worktree half: a relative path with no git
root, a directory inside a checkout rather than its root, or a checkout git
cannot read.

**A checkout `coga retire` will not remove is still listed.** Retire and
the sweep dispose of one shape, a linked worktree of this repository; an
independent fallback clone and another repository's linked worktree they
preserve by design, and a human removes those by hand. They stay on the
worklist until the directory goes, because this file is their only durable
trace once the ticket is deleted — the ticket's own `## Dev` dies with it, and
another repository's sweeps never see a ticket here.

### Remedies a human can act on

`coga retire <slug>` is named only where it can help: the task still exists
here and its proofs could pass from this repository. A worktree the proof
refused as not a linked worktree of this repository is classified again, and
the remedy names where it can be removed:

- **Another repository's linked worktree** (cross-repo work): the owning
  repository's main checkout and read-only worktree/status inspection commands.
  Classification proves ownership only, not that deletion is safe. Verify the
  recorded branch, preserve tracked/untracked/ignored local data, and check live
  claims, open PRs, and landed-or-exact-merged-head evidence in the owning repo
  before removing anything. Plan worktree and branch cleanup together: ordinary
  `branch -d` can refuse squash/rebase-merged tips; forced deletion needs the
  exact merged-head proof. Keep the directory until both halves are verified,
  because its removal can discharge this worklist entry. No runnable deletion
  command is advertised without those proofs. `coga retire` fails the same
  proof from here, and the task does not exist in the owning repo.
- **An independent clone, or a path git cannot read**: says so, and to
  inspect and remove the directory by hand; a local branch still here is
  named separately (`coga retire <slug>` for it while the ticket exists,
  otherwise `git branch -d`).
- **A worktree already gone from disk**: says so, and names branch-only
  cleanup.

Run it directly with `coga run autoclose`. Live notification configuration is
preflighted before each affected ticket closes. Later `gh` or task-validation
failures remain hard failures, but any earlier closures are still reported.
After the report exists, a transiently undeliverable Slack summary is
non-fatal and is recorded against the period task in the repo-global log.
