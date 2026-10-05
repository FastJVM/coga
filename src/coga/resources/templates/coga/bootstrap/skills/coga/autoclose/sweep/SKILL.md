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
sole trigger for closing tickets whose PR has merged. The recurring script
also runs branch-sweep after this recipe succeeds;
[coga/recurring/scheduling](context:coga/recurring/scheduling) owns that
composition. The autoclose recipe itself performs these steps:

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
   period task, to the template's durable `retires.md` worklist, and
7. report unresolved, non-outdated review threads with only their opening
   comment on each closed PR.

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
worklist entry recorded, and only those linked to the clone it runs from.
Ticket work no longer creates linked worktrees
([dev/checkouts](context:dev/checkouts)), so for a current ticket the
disposal is the local and remote branch; linked-worktree removal applies to
legacy worklist entries and tickets from the retired layout (in this repo,
`/home/n/Code/claude/coga-<branch>` worktrees of
`/home/n/Code/claude/coga`). Other clones' worktrees, including a sandbox
clone recorded as `worktree:`, are preserved as independent clones and need
their own `coga run branch-sweep`.

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
  branch is no longer a local branch of the repository that owns it (see
  *A branch in another clone*, below). Either half still to dispose of keeps
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
  under a `## Follow-ups (open)` heading, with an optional trailing
  ``, owner `<path>` `` for a worktree another repository owns. Field values use UTF-8 percent
  encoding, retaining `/` and `:`: for example, a backtick is `%60`, a literal
  percent is `%25`, and a space is `%20`. Decode the fields before using the
  recorded path or branch; use the same encoding when hand-editing or
  backfilling. A malformed line fails the sweep loudly rather than growing a
  second section nobody would find.

### The primary checkout is not debt

Apply `dev/checkout-cleanup`, "Primary checkouts and foreign branch ownership": preserve primary directories
in every clone and judge each branch in its owning repository. Independent
sandbox clones receive the same protection. Closure captures the owner before
filtering its primary path; legacy worklist entries infer missing ownership
before disposal or discharge. A cleared branch clears the entry automatically.
Unknown paths remain pending except for the missing self-owned clone policy
in `dev/checkout-cleanup`.

### A branch in another clone

Another repository's checkout has its branch in *that* repository —
typically a second clone of the same project, when the recurring job fires
from more than one. Judged against the sweeping clone's branches, such an
entry read "branch gone" the moment its worktree directory vanished and was
dropped silently while the branch lived on. So each entry whose worktree is
another repository's checkout records that repository's main working
tree as `owner` (`retire_worklist.worktree_owner`, over
`git.classify_checkout`), written by the reconcile while the directory still
exists to be classified — on the run that records it, or, for an older line,
the next run — and the discharge rule reads the owner's local branches
instead (`retire_worklist.branch_owner`). An owner that is a checkout of the
sweeping repository judges the entry like any other; an owner path that is
gone or that git cannot read is an unknown and keeps the entry — except an
independent clone recorded as its own owner (the line keeps its primary path
as `worktree:`), whose missing directory is treated as deletion, so the entry
clears. Apply `dev/checkout-cleanup`, "Accepted disappearance policy", for the
accepted relocation/unmount risk and the operator procedure before moving a
clone or making its filesystem unavailable.
Once the
worktree is gone or is a primary checkout, the sweep does not run this repository's proofs on the
branch — they would find no local branch and call it disposed — and reports
the entry as preserved with the by-hand delete in the owning clone
(`git -C <owner> branch -d <branch>`), on the run report and coga-important,
until the owner's branch is gone. When the recorded owner path is itself gone
or unreadable, that command could not run: the entry is still kept, and the
remedy says the branch's home is unknown and asks a human to locate the clone
and correct the entry's `owner` (or remove the line once the branch is
verified landed and deleted there). A union-merged duplicate of an entry
keeps its recorded `owner` when the other line names the same worktree
without one. A line recorded before the field existed
whose worktree is already gone has nothing to classify: it is judged against
this repository as before, so add its `owner` by hand if its branch lives in
another clone.

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
  exact merged-head proof. Keep the directory until both halves are verified.
  Its removal no longer discharges the entry while the owning repository
  still holds the branch (*A branch in another clone*). No runnable deletion
  command is advertised without those proofs. `coga retire` fails the same
  proof from here, and the task does not exist in the owning repo.
- **A primary checkout, including an independent clone**: preserve the
  directory; inspect and clean up the recorded branch in the owning repository
  under the contract above. Never recommend directory deletion.
- **A path git cannot read**: reports the failed probe and manual inspection.
- **A worktree already gone from disk**: says so, and names branch-only
  cleanup.

## The unanswered-thread follow-up

The `review` step is an owner gate: the owner merges from the GitHub UI, where
an unresolved thread does not block, and nothing else looks at the PR's
threads again (the `dev/dev-record` context, "Review step",
has the measurement and the decision). The sweep is the one place that already
touches every merged PR, so when it closes a ticket it fetches that PR's
`reviewThreads` once — `coga.autoclose.unanswered_review_threads`, one
paginated `gh api graphql` query against the recorded PR URL's host and base
repository — and keeps the threads that are unresolved,
not outdated, and hold only their opening comment. Resolved means a human
decided, outdated means the flagged line already moved, and a reply means
someone saw it; what remains is exactly what merged unseen.

Report-only, three surfaces:

- the ticket's own closure line in `coga/log.md` names each thread's
  `path:line` (`auto-bumped on merge of PR #7 → done; 1 unanswered review
  thread: src/coga/x.py:42`) — the durable one;
- a `## Autoclose Sweep: unanswered review threads` section beside the retire
  section, with author, opening-line excerpt, and thread link — per-run, same
  caveat as above;
- one trailing Slack line linking every thread.

The sweep never resolves a thread, replies to one, or blocks a merge. The
fetch runs *before* the close: a `gh` failure there leaves the ticket open for
the next sweep rather than closing it without its report. After the GitHub
lookups, the sweep re-reads the ticket and checks eligibility again, preserving
a pause, cancellation, or completion that happened while GitHub was responding.

Run it directly with `coga run autoclose`. Live notification configuration is
preflighted before each affected ticket closes. Later `gh` or task-validation
failures remain hard failures, but any earlier closures are still reported.
After the report exists, a transiently undeliverable Slack summary is
non-fatal and is recorded against the period task in the repo-global log.
