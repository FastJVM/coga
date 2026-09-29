---
name: dev/checkout-cleanup
description: How finished tickets and their feature checkouts are disposed of: `coga retire`, `coga delete`, the shared checkout proofs, ignored-state rules, and the `[git] worktrees_ticket_owned` assumption.
---

# Retiring tickets and checkouts

You do not delete your own feature branch. `coga retire` (manual, while the
ticket and its `## Dev` lines exist) and the daily autoclose sweep (for every
ticket it closes and every open `retires.md` entry) run one shared set of
proofs: `checkout_disposal.py` over the per-checkout proofs in
`branchcleanup.py`. Ticket work no longer creates linked worktrees
([dev/checkouts](../checkouts/SKILL.md)), so a current ticket records only
`branch:` and the disposal is branch-only. A ticket from the retired
linked-worktree layout may still record `worktree:`; the disposal removes that
worktree first, since a branch checked out in a linked worktree cannot be
deleted, then prunes the branch. Keep `worktree:` accurate where it exists; it
is what they act on.

## The checkout proofs

A recorded worktree is removed only when:

- Git identifies it as a linked worktree of the same repository, still on the
  recorded branch;
- no other non-terminal ticket in any Coga workspace of the same Git checkout
  records that branch or worktree (claim discovery scans every workspace,
  including a recurring runner's temporary control checkout, via
  `discover_coga_repos(..., allow_control_worktree_root=True)`; a refused or
  incomplete claim scan keeps even a branch-only disposal pending, which
  autoclose reports and retains);
- no PR for that head is open;
- the branch has landed on control or still equals the recorded merged PR head.

Local cleanup precedes remote deletion; remote deletion re-verifies the exact
head and uses force-with-lease, so a reused branch is never deleted on stale
PR state.

**Ignored state.** Tracked, untracked, and ignored files all preserve the
checkout, except the regenerable entries in
`branchcleanup.REGENERABLE_IGNORED_DIRS` (`__pycache__`, `.pytest_cache`,
`.ruff_cache`, `.mypy_cache`, and Coga's rebuilt `.agent-skills/` symlink
view), which retire deletes and counts. A copied `coga.local.toml` is judged
by content: byte-identical to the operator's own (`local_config_path`, so
`COGA_LOCAL_CONFIG` when set) it is deleted and counted, since the original
survives; an edited copy preserves the checkout. Other machine-local state
(`.env`, `.venv/`, `.coga/`, agent discovery links) preserves it. For ignored-only state
retire prints and records the explicit opt-in
`git worktree remove --force '<path>'`; it never offers that over tracked or
untracked work.

Reported for manual disposal: an independent `/tmp` clone (not a linked
worktree); the checkout running `coga retire`; a stale path now on another
branch; a checkout shared with another live ticket or an open PR; a locked or
dirty worktree; and a recorded path already gone (reported, not pruned).

**Known failure mode (unresolved): another clone's primary checkout never
discharges.** The "primary checkout is not debt" rule
(`retire_worklist.is_primary_checkout`) exempts only *this* repository's
primary. A ticket worked in the single-checkout layout of a second,
long-lived clone of the same project records that clone's primary as its
`worktree:`. The sweeping clone classifies it `standalone`, so autoclose keeps
the `retires.md` entry and re-posts it to coga-important on every run. Its
remedy (`autoclose.py`: "an independent checkout with its own repository,
which no proof removes — inspect and remove it by hand") cannot tell that
clone from a disposable one, so it now carries this exception: never remove
another clone's primary checkout in active use. `worktree_owner` records no `owner` for
a standalone clone, on the assumption that its branch dies with its
directory, so the branch half is judged against this repository, where the
branch may never have existed. The worktree half never clears. The rule that
keeps independent clones on the worklist as their only durable trace was
written for disposable fallback clones and does not cover this case. Until a
fix lands, do not act on that remedy for a clone in active use: check that
the branch is gone in the named clone, then remove the line from `retires.md`
by hand. The observed instance is recorded in
`docs/evidence/independent-clone-worklist-2026-09.md`.

## `coga retire <slug> [--agent <type>] [--no-launch]`

Refuses unless the ticket is `status: done`. It first disposes of the
checkout and branch under the proofs above (best-effort: a cleanup failure is
reported, never aborts). It then drops the slug from any recurring template's
`retires.md` worklist, but only once its local branch is gone (judged in the
owning repository when the entry records another clone as `owner`) and its recorded
worktree directory is gone or is the repository's own primary checkout (which
nobody disposes of). Finally it scaffolds a `retire-<slug>` task straight to `active`,
whose body invokes the `retro/done-ticket` skill; that skill opens the PR that
records `## Retro`, edits knowledge if warranted, and deletes the source task
in the same PR. Retire launches the task unless `--no-launch`, which prints the
`coga launch` command instead. Branches with no live ticket are the
`branch-sweep` job's.

## `coga delete <slug>`

Removes a task directory (ticket, blackboard, attachments) and syncs the
removal; recovery is `git restore`, with no Slack broadcast. Use it for an
abandoned ticket with nothing to retro. The removal lives in
`coga.delete_task`, also reachable as `coga run delete-task <slug>`, which does
not sync. Both hold the checkout-local state lock. Bootstrap tickets are not
deletable. `--keep-control-checkout` is the Retro-only form: accepted only from
a linked worktree, it still pushes to the remote control branch but does not
fast-forward another checkout that has control checked out; from the primary
checkout it fails before deleting. In a sandbox that cannot create a linked
worktree, Retro may use an independent clone and plain `coga delete`.

## Unrecorded worktrees: `[git] worktrees_ticket_owned`

The proofs only touch worktrees a ticket or worklist recorded. An ad-hoc
worktree pins its branch forever, and `coga run branch-sweep` reports it
`skipped-worktree-pinned`. A repo may assert, with
`worktrees_ticket_owned = true` under `[git]` in shared `coga.toml` (default
`false`):

> Every linked worktree of this repository belongs to a Coga ticket. A
> landed, locally pristine linked worktree that no non-terminal ticket
> records is finished work, not someone's scratch checkout.

With it set, the branch sweep removes such a worktree before deleting
its landed branch, under the same linked-worktree, exact-branch, pristine, and
unclaimed proofs. Setting it is the owner's call: afterwards a scratch checkout
worth keeping must be dirty, unlanded, or recorded on a live ticket. The sweep
also runs `git worktree prune` repo-wide first, because a wiped `/tmp`
worktree's registration keeps pinning its branch.

The daily autoclose template also runs this existing branch pass after its
ticket/worklist cleanup, including on days when no ticket closes. The standalone
weekly sweep remains a retry; cadence and failure ordering live in
[recurring scheduling](../../coga/recurring/scheduling/SKILL.md).
Both passes preserve and report local refs with unpushed non-bookkeeping
commits. A closed but unmerged PR alone is not evidence that its work landed.
