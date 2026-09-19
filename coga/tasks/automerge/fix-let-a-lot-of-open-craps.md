---
title: fix let a lot of open craps
status: draft
owner: nicktoper
agent: claude
contexts:
  - dev/code
workflow: code/with-review
---

## Description

The autoclose sweep (`coga run autoclose`, fired daily by
`coga/recurring/autoclose-merged/`) marks a merged final-step ticket `done`
but never disposes of the ticket's feature checkout. It only writes a
`coga retire <slug>` follow-up into `coga/recurring/autoclose-merged/retires.md`
and waits for a human to type it. Nobody does, so worktrees and branches pile
up: the worklist holds ten open entries and `git worktree list` shows seven
stale linked worktrees, most under `/tmp/coga-pr*-review`. The weekly branch
sweep cannot help — it preserves any branch pinned by a live worktree
(`skipped-worktree-pinned`).

Make the deterministic sweep dispose of the checkout itself, in the same run,
under the exact safety proofs `coga retire` already runs:

1. **Closed-in-this-run tickets.** After `sweep_merged` marks a ticket done,
   remove its recorded linked worktree, then delete its local branch, then its
   `origin` branch — the same three-step order and the same proofs as
   `coga retire` (`branchcleanup.remove_ticket_worktree`,
   `branchcleanup.delete_ticket_branch`, which covers local and remote).
2. **Drain the backlog.** On every recurring run, walk each open entry in the
   template's `retires.md` worklist and apply the same proofs to its recorded
   worktree and branch, so the ten existing entries clear on the first run
   without anyone typing `coga retire` ten times.
3. **Preserve, and say why.** Anything a proof refuses — dirty or shared
   worktree, unmerged source commits, open PR, invoking checkout — stays on the
   worklist exactly as today, and the per-run report names the reason. The
   worklist keeps its current meaning: an entry is what the sweep could *not*
   prove disposable.
4. `coga retire` keeps its own cleanup unchanged for the manual path; both
   callers share one implementation.

Done means: a fresh `coga run autoclose` on this repo removes every worktree
and branch the proofs admit, the report and `retires.md` list only the
preserved ones with reasons, the `coga/autoclose/sweep` skill and the recurring
ticket text describe the new behavior, and tests cover dispose / preserve /
backlog-drain / remote-delete paths.

## Context

**Where the sweep lives.** `autoclose.sweep_merged` scans tickets and
`autoclose._try_bump_one` closes one; `autoclose._report_retire_followups`
is where the follow-up is named today and the worklist reconciled via
`retire_worklist.reconcile_worklist`. `retire_worklist.parse_worklist` /
`is_discharged` / `discharge_slug` own the worklist file format — reuse them,
do not invent a second format. The period task's `ticket.py` runs the sweep
through `runner.run_recipe("autoclose")`, so the sweep must stay a registered
recipe with a stable argv/stdout/exit contract; no agent, no prompt.

**Where the proofs live.** `branchcleanup.remove_ticket_worktree` (same-repo
linked worktree, recorded branch checked out, no tracked/untracked local
state, no open PR, branch landed or exact merged head) and
`branchcleanup.delete_ticket_branch` (local `-d`/`-D` policy plus
`delete_remote_branch` gated on the merged PR at the exact remote tip). Both
take the `## Dev` blackboard text. The third proof, "no other live ticket
claims this branch or worktree", is `commands/retire._live_checkout_claim`
and its `_cleanup_checkout` orchestration — those are single-consumer today.
Once autoclose is the second consumer they qualify as shared infra: move them
into `branchcleanup` (or a sibling module) and have both `retire` and
`autoclose` call the shared function. Do not import from `coga.commands.*`
inside `autoclose`.

**Backlog entries have no ticket.** A `retires.md` entry's ticket may already
be deleted (retire preserved the checkout, then removed the ticket) — the
worklist header says so. For the drain path the proofs must run from the
entry's recorded branch and worktree, not from a ticket's `## Dev` text:
either build a minimal blackboard-shaped text from the entry, or split the
proof functions to accept `(branch, worktree)` directly. The live-claim scan
still applies — another non-terminal ticket may name the same branch.

**Control-branch precondition holds.** Retire skips cleanup unless the
invoking checkout is on `cfg.git_control_branch`. The recurring runner already
refuses to fire off the control branch (`coga/recurring` context, "Recurring
runs start on the control branch"; `recurring_runner` checks
`_current_branch` against `cfg.git_control_branch`), so the sweep can keep
that same guard and it will be satisfied under cron. A hand-run
`coga run autoclose` off the control branch should preserve everything and say
so, not fail.

**Destructive-behavior rule.** `coga/architecture` (cited, not attached —
the "Recurring maintenance" section near its end) says destructive behavior
such as deleting git refs is never implicit, and allows a direct destructive
change only when the rule is deterministic, narrow, and named. The proofs are
exactly that. The previous design chose to only *name* the retire; this
ticket reverses that decision on purpose because it produced the backlog.
Update the `coga/autoclose/sweep` skill's "The retire follow-up" section and
the recurring ticket's Description/blackboard text to declare what the sweep
now deletes and under which proofs. Keep the packaged twins byte-identical:
`src/coga/resources/templates/coga/bootstrap/skills/coga/autoclose/sweep/SKILL.md`
and `src/coga/resources/templates/coga/recurring/autoclose-merged/ticket.md`
(`tests/test_packaging.py` enforces it).

**Out of scope.** Do not change the branch sweep's `skipped-worktree-pinned`
behavior; do not touch Dream; do not add a manual `automerge` command. The
paused `v2/automerge-ticket` (agent-merged PRs) is unrelated — this ticket is
about cleanup after a human merge.

**Tests.** `tests/test_autoclose.py` covers the sweep today. Add cases for:
worktree+local+remote removed on a clean landed checkout; each preserve
reason keeps the worklist entry and names it; backlog entry with no ticket
drained; off-control-branch hand run preserves everything; `coga retire`
still works after the shared-function move.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
