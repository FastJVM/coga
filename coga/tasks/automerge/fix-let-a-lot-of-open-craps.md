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

Merged tickets leave their worktrees and branches behind. The daily autoclose
sweep (`coga run autoclose`, fired by `coga/recurring/autoclose-merged/`)
marks a merged final-step ticket `done` but never disposes of its checkout:
it only writes a `coga retire <slug>` follow-up into
`coga/recurring/autoclose-merged/retires.md` and waits for a human to type it.
Nobody does. The worklist holds ten open entries, and the clone that runs the
recurring jobs (`/home/n/Code/claude/coga`, the editable `uv` install) has 45
linked worktrees — the ten recorded ones plus dozens of ad-hoc review and
scratch checkouts no ticket ever recorded. The weekly branch sweep cannot take
any of them: it preserves every branch a live worktree pins
(`skipped-worktree-pinned`).

Fix both halves, deterministically, no agent in the loop:

**Daily — autoclose disposes of what it closes.** After `sweep_merged` marks
a ticket done, remove the ticket's recorded linked worktree, then delete its
local branch, then its `origin` branch, under exactly the proofs `coga retire`
runs today (`branchcleanup.remove_ticket_worktree`,
`branchcleanup.delete_ticket_branch`). On every recurring run also walk the
open `retires.md` entries and apply the same proofs to each recorded
branch/worktree, so the existing backlog drains without ten hand-typed
retires. Anything a proof refuses stays on the worklist with its reason;
`coga retire` keeps working unchanged for the manual path, and both callers
share one implementation.

**Weekly — branch sweep GCs what no ticket links.** Extend
`branchsweep.sweep_branches` so a landed branch held by a live worktree is no
longer `skipped-worktree-pinned`: if that worktree is a linked worktree of
this repo, checked out on that branch, locally pristine (no modified tracked
or untracked files; ignored caches are fine), and claimed by no non-terminal
ticket, remove the worktree first and then delete the local and remote branch
under the sweep's existing landed-branch authorization. Worktrees that fail
any of those proofs are reported with the reason, as today.

Done means: on the recurring clone, one `coga run autoclose` closes and
disposes of every recorded checkout the proofs admit and drains the worklist
down to preserved entries with reasons; one `coga run branch-sweep` removes
every pristine landed worktree and its branches; `coga/autoclose/sweep`,
`coga/branch-sweep/sweep`, both recurring ticket texts, and the
`retire_worklist.RETIRE_WORKLIST_HEADER` constant describe the new behavior;
tests cover dispose / preserve / backlog-drain / remote-delete /
worktree-GC paths and `coga retire` after the shared-function move.

## Context

**Which clone runs the jobs.** Recurring jobs run from
`/home/n/Code/claude/coga` (the `uv tool` editable install; it holds
`.coga/recurring-runs`). Both sweeps only ever touch worktrees linked to the
clone they run from — `branchcleanup._is_linked_worktree_of` preserves
anything else as an independent clone — so state that in the skill text. The
ten worklist entries point at `/home/n/Code/claude/coga-<branch>` worktrees of
that clone, so the drain will find them there. Other clones (this one at
`/home/n/Code/coga` has seven stale `/tmp/coga-pr*-review` review worktrees)
need their own `coga run branch-sweep`.

**Where the sweeps live.** `autoclose.sweep_merged` scans tickets,
`autoclose._try_bump_one` closes one, and `autoclose._report_retire_followups`
is where the follow-up is named today and the worklist reconciled via
`retire_worklist.reconcile_worklist`; `retire_worklist.parse_worklist` /
`is_discharged` / `discharge_slug` own the worklist file format — reuse
them. `branchsweep.sweep_branches` enumerates worktrees and branches and
already runs the landed-branch proofs (`local_branch_landed`, merged-PR
authorization); the pinned-worktree skip is the one branch to change. Both
period tasks' `ticket.py` run through `runner.run_recipe`, so each sweep
stays a registered `coga run` recipe with a stable argv/stdout/exit contract.

**Where the proofs live.** `branchcleanup.remove_ticket_worktree` (same-repo
linked worktree, recorded branch checked out, no tracked/untracked local
state, no open PR, branch landed or exact merged head) and
`branchcleanup.delete_ticket_branch` (local `-d`/`-D` policy plus
`delete_remote_branch` gated on the merged PR at the exact remote tip). Both
take `## Dev` blackboard text. The third proof — no other non-terminal ticket
claims the branch or worktree, across every Coga workspace in the git repo —
is `commands/retire._live_checkout_claim` with its `_cleanup_checkout`
orchestration, single-consumer today. With autoclose and branch-sweep as
further consumers they qualify as shared infra under the microkernel rule
(`coga/codebase`, cited not attached: core holds code with ≥2 real
consumers): move them into `branchcleanup` or a sibling module. Never import
from `coga.commands.*` inside a sweep.

**Proofs must accept `(branch, worktree)` without a ticket.** A worklist
entry's ticket may already be deleted (retire preserved the checkout, then
removed the ticket), and a GC'd worktree may never have had one. Split or
wrap the proof functions so they take the branch and worktree path directly;
the `## Dev`-text entry point becomes a thin parser on top. The live-claim
scan still runs in every path.

**Control-branch guard.** Retire skips cleanup unless the invoking checkout
is on `cfg.git_control_branch`. `coga recurring` refuses to fire off the
control branch, and when the host checkout is elsewhere the runner services
deterministic phases from a temporary control worktree that *is* on `main`
(`recurring_runner._service_from_control_worktree`) — so under the scheduler
the guard is satisfied. A hand-run `coga run autoclose` has **no** branch
guard today: add one, and off the control branch preserve everything and
say so rather than fail.

**Destructive-behavior rule.** `coga/architecture` (cited, not attached — the
recurring-maintenance rules near its end) says deleting git refs is never
implicit, and allows a direct destructive change only when the rule is
deterministic, narrow, and named. These proofs are exactly that. The previous
design chose to only *name* the retire; this ticket reverses that on purpose
because it produced the backlog. Declare the new deletes and their proofs in
the `coga/autoclose/sweep` skill ("The retire follow-up" section), the
`coga/branch-sweep/sweep` skill, both recurring tickets' text, the
`retire_worklist.RETIRE_WORKLIST_HEADER` constant ("Autoclose only ever names
the follow-up" is no longer true), and the `retires.md` header on disk. Keep
packaged twins byte-identical
(`src/coga/resources/templates/coga/bootstrap/skills/coga/{autoclose,branch-sweep}/sweep/SKILL.md`,
`src/coga/resources/templates/coga/recurring/{autoclose-merged,branch-sweep}/ticket.md`;
`tests/test_packaging.py` enforces it). `retires.md` has no packaged twin —
do not create one.

**Out of scope.** Dream; a manual `automerge` command; the paused
`v2/automerge-ticket` (agent-merged PRs — unrelated, this is cleanup after a
human merge); splitting `dev/code` into a smaller core context (the evaluator
flagged it at 64% of this ticket's composed prompt — separate ticket).

**Tests.** `tests/test_autoclose.py` and the branch-sweep tests cover the
sweeps today. Add: worktree + local + remote removed on a clean landed
checkout; each preserve reason keeps the worklist entry and names it; a
worklist entry with no ticket drains; off-control-branch hand run preserves
everything; branch-sweep removes a pristine pinned worktree and reports a
dirty or claimed one; `coga retire` unchanged after the shared-function move.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

**Clarity.** Good. A fresh agent can start: the problem, four numbered outcomes, a "done means", file/symbol map, and out-of-scope are all present. Every cited symbol exists (`autoclose.sweep_merged`/`_try_bump_one`/`_report_retire_followups`, `retire_worklist.parse_worklist`/`is_discharged`/`discharge_slug`/`reconcile_worklist`, `branchcleanup.remove_ticket_worktree`/`delete_ticket_branch`/`delete_remote_branch`, `commands/retire._live_checkout_claim`/`_cleanup_checkout`, `recurring_runner._current_branch`, `runner.RECIPES["autoclose"]`, `tests/test_autoclose.py`, both packaged twins).

**Workflow fit.** `code/with-review` fits: Python change, tests, PR. No mismatch. Note `review` step text says autoclose closes the ticket after merge — this ticket changes what that closure then does, so the peer-reviewer should read the sweep skill diff, not just code.

**Contexts.** `dev/code` is the only attachment and is what its own frontmatter demands. `coga/architecture` and `coga/recurring` are cited with section names, not sizes — correct. Neither needs attaching: the one architecture rule is quoted into `## Context`, and the recurring precondition is a single fact. Nothing important missing, except `coga/codebase` (microkernel rule) is neither cited nor quoted, and the ticket moves a helper into core on the ≥2-consumers rule — one sentence citing it would suffice.

**Prompt size.** `ticket_context dev/code` = 24.1 KiB, 64% of the composed prompt. It is over the 40% flag. Not this ticket's fault (frontmatter mandates it), but the fix is structural: split `dev/code` into the ~8 KiB `## Dev` line-shape + checkout-boundary core that every branch ticket needs, and cite the rest (design pivots, superseded designs, review-threads-that-merge-unanswered) from it. Worth a separate ticket; the paused `attach-vs-cite` work is adjacent.

**Scope.** Two tickets' worth. (1) dispose-in-run + shared-proof move is one coherent change. (2) "Drain the backlog" from `retires.md` entries with no ticket requires a new `(branch, worktree)` proof signature and a ticketless live-claim scan; the ticket itself flags it as an open design choice. Recommend splitting drain into a follow-up.

**Assumptions to question before launch.**
- **The evidence and the fix don't meet.** The seven stale worktrees in this clone (`/tmp/coga-pr817..826-review`) are review checkouts recorded nowhere — not on any `## Dev` line, not on the worklist. The proofs only act on the *recorded* worktree, so the change as written removes none of them, and `delete_local_branch` will refuse the five branches they pin.
- **The ten worklist entries point at another clone.** All nine surviving recorded worktrees (`/home/n/Code/claude/coga-*`) have `--git-common-dir` = `/home/n/Code/claude/coga/.git`, not this repo's. From `/home/n/Code/coga`, `_is_linked_worktree_of` preserves every one as "independent clone". "Ten entries clear on the first run" is only true if the run is from that other clone. State which clone hosts the cron.
- **Control-branch precondition: right conclusion, incomplete reason.** `_refuse_non_control_branch` gates `coga recurring`, but the runner also services deterministic phases from a temporary control worktree (`_service_from_control_worktree`) when the host is off-control. That path still passes the guard (the temp checkout *is* on `main`, same common dir), so it works — but the hand-run `coga run autoclose` today has no branch guard at all; the ticket must add one, not "keep" one.
- `RETIRE_WORKLIST_HEADER` in `retire_worklist.py` says "Autoclose only ever names the follow-up" — that constant, plus the existing `retires.md` header on disk, must change too; the ticket lists only the skill and recurring ticket.
- Packaged twin for `retires.md` does not exist; fine, but don't create one.
