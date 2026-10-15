---
name: dev/checkout-cleanup
description: How finished tickets and their feature checkouts are disposed of — `coga retire`, `coga delete`, and recovering from vanished `/tmp` checkouts — with the checkout proofs, foreign ownership, terminal-owner cleanup and the branch-sweep archive in its leaves.
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

## Leaves

- [dev/checkout-cleanup/proofs](proofs/SKILL.md) — the per-checkout proofs
  retire and autoclose share, owned-branch deletion order, and ignored state.
- [dev/checkout-cleanup/foreign-ownership](foreign-ownership/SKILL.md) —
  primary checkouts, foreign branch ownership, and the accepted
  disappearance policy.
- [dev/checkout-cleanup/terminal-owners](terminal-owners/SKILL.md) —
  terminal owners and closed PRs: ownership, durable branch debt,
  authorization, and when cleanup runs.
- [dev/checkout-cleanup/branch-sweep](branch-sweep/SKILL.md) — branch-sweep
  protection, the `retired/<branch>` archive, and
  `[git] worktrees_ticket_owned`.

## `/tmp` checkouts do not survive; the branch does

Treat any checkout under the system temp dir (a sandbox clone, a Dream or
Retro run checkout, an ad-hoc review worktree) as ephemeral: it is routinely
gone by the time anyone acts on it. Leaving work "preserved" in one, or
recording its path in `worktree:` or a blackboard note, preserves nothing.
Before the run ends, push the branch or land its commits on `main`.

When a linked `/tmp` worktree vanishes, Git keeps two things: a stale
registration (`git worktree prune` clears it; the branch sweep runs it) and
the local branch, which may now be the only copy of unlanded commits. A stale
`worktree:` line pointing at a gone path is therefore not evidence the work
landed. Recover from the primary checkout after refreshing `main` from `origin`
(here, as in `dev/checkouts`, `origin` and `main` stand for the configured
`[git].remote` and `[git].control_branch`):

1. Inspect `git log main..<branch>` for candidate commits. Squash merges and
   cherry-picks may already have landed their changes; check merged-PR
   history or patch equivalence before selecting commits to recover.
2. Recover only work still missing and wanted: cherry-pick onto `main` through
   the normal publication path, or `git push origin <branch>` and open a PR.
3. Only then `git branch -D <branch>`.

## `coga retire <slug> [--agent <type>] [--no-launch]`

Refuses unless the ticket is `status: done`. It first disposes of the
checkout and every owned branch under the
[checkout proofs](proofs/SKILL.md). A worktree or owned
branch the proofs kept is a bug: the ticket is its only owner record, so Retro
must not delete it. Retire then skips the worklist discharge, creates the retire task
already `blocked` with what it kept and why (which notifies the owner
on Slack, as `coga block` does), launches nothing and exits 2. The owner fixes
the checkout by hand, then runs `coga unblock` and `coga launch` on the retire
task. Run it from a checkout on `[git].control_branch`:
off control (or with `[git].enabled` false, or outside a git work tree) it
skips disposal and says so (`Retire: checkout cleanup skipped ...`) rather
than failing, leaving the checkout and branch to autoclose or `branch-sweep`.
It then drops the slug from any recurring template's
`retires.md` worklist, but only once its local branch is gone (judged in the
owning repository when the entry records another clone as `owner`) and its recorded
worktree directory is gone or is a repository's primary checkout (which
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
