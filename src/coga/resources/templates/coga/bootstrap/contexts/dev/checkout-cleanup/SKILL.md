---
name: dev/checkout-cleanup
description: How finished tickets and their feature checkouts are disposed of: `coga retire`, `coga delete`, the shared checkout proofs, ignored-state rules, and the `[git] worktrees_ticket_owned` assumption.
---

# Retiring tickets and checkouts

You do not remove your own feature checkout. `coga retire` (manual, while the
ticket and its `## Dev` lines exist) and the daily autoclose sweep (for every
ticket it closes and every open `retires.md` entry) run one shared set of
proofs: `checkout_disposal.py` over the per-checkout proofs in
`branchcleanup.py`. Both remove the recorded worktree first, since a branch
checked out in a linked worktree cannot be deleted, then prune the branch.
Keep `worktree:` accurate; it is what they act on.

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
checkout, except the regenerable caches in
`branchcleanup.REGENERABLE_IGNORED_DIRS` (`__pycache__`, `.pytest_cache`,
`.ruff_cache`, `.mypy_cache`), which retire deletes and counts. Machine-local
state (`coga.local.toml`, `.env`, `.venv/`, `.coga/`, a rebuilt
`.agent-skills/`, agent discovery links) preserves it. For ignored-only state
retire prints and records the explicit opt-in
`git worktree remove --force '<path>'`; it never offers that over tracked or
untracked work.

Reported for manual disposal: an independent `/tmp` clone (not a linked
worktree); the checkout running `coga retire`; a stale path now on another
branch; a checkout shared with another live ticket or an open PR; a locked or
dirty worktree; and a recorded path already gone (reported, not pruned).

## `coga retire <slug> [--agent <type>] [--no-launch]`

Refuses unless the ticket is `status: done`. It first disposes of the
checkout and branch under the proofs above (best-effort: a cleanup failure is
reported, never aborts). It then drops the slug from any recurring template's
`retires.md` worklist, but only once the recorded worktree and local branch are
both gone. Finally it scaffolds a `retire-<slug>` task straight to `active`,
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

With it set, the weekly branch sweep removes such a worktree before deleting
its landed branch, under the same linked-worktree, exact-branch, pristine, and
unclaimed proofs. Setting it is the owner's call: afterwards a scratch checkout
worth keeping must be dirty, unlanded, or recorded on a live ticket. The sweep
also runs `git worktree prune` repo-wide first, because a wiped `/tmp`
worktree's registration keeps pinning its branch.
