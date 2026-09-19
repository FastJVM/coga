---
title: fix let a lot of open craps
status: active
owner: nicktoper
agent: claude
contexts:
- dev/code
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
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

**Make the assumption explicit.** Removing an unrecorded worktree rests on
one repo-level assumption: every linked worktree of this repository belongs
to a Coga ticket, so a landed, pristine one nobody claims is finished work,
not someone's scratch checkout. Declare it as a `[git]` setting in
`coga.toml` (new key, e.g. `worktrees_ticket_owned = true`, default `false`),
gate the weekly worktree GC on it — off, the sweep keeps today's
`skipped-worktree-pinned` — and write the assumption down in the context that
owns the checkout convention.

Done means: on the recurring clone, one `coga run autoclose` closes and
disposes of every recorded checkout the proofs admit and drains the worklist
down to preserved entries with reasons; one `coga run branch-sweep` removes
every pristine landed worktree and its branches; `coga/autoclose/sweep`,
`coga/branch-sweep/sweep`, both recurring ticket texts, and the
`retire_worklist.RETIRE_WORKLIST_HEADER` constant describe the new behavior;
tests cover dispose / preserve / backlog-drain / remote-delete /
worktree-GC (key on and off) paths and `coga retire` after the
shared-function move.

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

**The ticket-owned-worktrees setting.** `[git]` is shared config
(`config.py` — `git_remote` / `git_control_branch` come from it; see
`coga.git`). Add the new key beside them with a `false` default, so a repo
that never declares it keeps the conservative behavior — destructive
behavior is never implicit, and a repo opts in by writing the assumption
down. Document the key where the other `[git]` keys are documented, and
state the assumption itself in `dev/code` → "Checkout boundary", which owns
the worktree convention (one owner per fact; `coga/architecture` may link,
not restate). Setting the key to `true` in this repo's `coga/coga.toml` is
the owner's call at the review step, not the agent's — the base prompt
forbids agents editing `coga.toml`; say so in the PR body. Autoclose's daily
path does not depend on the key: it only ever touches worktrees a ticket
recorded.

**For the peer reviewer.** The behavior change is as much in the skill and
recurring-ticket text as in the code: review the `coga/autoclose/sweep` and
`coga/branch-sweep/sweep` diffs against the proofs actually implemented, not
just the Python.

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
