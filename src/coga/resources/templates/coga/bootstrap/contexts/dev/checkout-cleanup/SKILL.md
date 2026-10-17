---
name: dev/checkout-cleanup
description: The rules shared by everything that disposes of finished tickets and their feature checkouts — protecting primary checkouts and other clones, recovering from vanished `/tmp` checkouts, and `coga delete` — with the checkout proofs, terminal-owner cleanup and the branch-sweep archive in its leaves.
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

This topic owns only what those jobs share. Each job's own procedure lives
with its ticket: `coga retire` in the packaged `bootstrap/retire/ticket.md`,
the autoclose and branch-sweep passes in the `recurring/autoclose-merged` and
`recurring/branch-sweep` templates.

## Leaves

- [dev/checkout-cleanup/proofs](proofs/SKILL.md) — the per-checkout proofs
  retire and autoclose share, owned-branch deletion order, and ignored state.
- [dev/checkout-cleanup/terminal-owners](terminal-owners/SKILL.md) —
  terminal owners and closed PRs: ownership, durable branch debt,
  authorization, and when cleanup runs.
- [dev/checkout-cleanup/branch-sweep](branch-sweep/SKILL.md) — branch-sweep
  protection, the `retired/<branch>` archive, and
  `[git] worktrees_ticket_owned`.

## Primary checkouts and other clones

A primary checkout is never directory debt, including another clone's primary
and independent sandbox clones: Git topology cannot prove a clone disposable,
and it may hold untracked or ignored data. `git.classify_checkout` identifies
another repository's primary as `foreign-primary`, with its root as `owner`;
`retire_worklist.is_primary_checkout` exempts its directory. Autoclose
preserves it and never recommends deleting it.

The branch stays debt in the repository that owns it. `worktree_owner`
records that owner for foreign primary and foreign linked checkouts. Autoclose
captures ownership before dropping a primary's directory from the closure, and
infers missing ownership on legacy entries before any branch cleanup or
discharge check; it never deletes a same-named branch in the sweeping clone.
A remaining foreign branch is reported for manual cleanup in its owning
clone. The owning clone's own daily branch sweep runs the ordinary proofs on
the entries that record it as `owner`, then discharges and publishes them
(`coga/recurring/scheduling`), so the manual step remains only for a clone
that does not run `coga recurring`. An unreadable owner or branch list keeps
the entry pending, and so does a missing owner of a foreign linked worktree.
Once the owner's branch is gone, a primary-checkout entry discharges with no
directory deletion or manual `retires.md` edit; foreign linked worktrees still
owe their directory cleanup.

### Accepted disappearance policy

For an independent clone recorded as its own owner, a missing directory is
treated as deletion of the clone and its branch, so the entry clears (owner
decision, 2026-10-01). A missing path does not prove deletion — relocation or
a temporarily unavailable filesystem looks the same — but automatic discharge
keeps deleted sandbox clones from generating reminders forever, replacing the
repeated-posting failure in
[the September incident](../../../archive/evidence/independent-clone-worklist-2026-09.md).
The cost: a surviving clone's branch cleanup can be forgotten if its recorded
path disappears. The policy drops bookkeeping only; it never deletes a clone.

Before moving or renaming a clone, pause autoclose sweeps in every
participating checkout, update both `owner` and `worktree` in its
`retires.md` entries to the new path (using the worklist's field encoding),
and update any surviving ticket's `worktree:`. Move the clone and verify the
new path before resuming sweeps. For a temporary unmount, keep sweeps paused
until the original path is back. Publish ephemeral work before deliberately
removing a clone; that removal also discharges its entry.

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
