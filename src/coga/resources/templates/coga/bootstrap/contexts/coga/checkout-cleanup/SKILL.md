---
name: coga/checkout-cleanup
description: The rules shared by everything that disposes of finished tickets and their feature checkouts — the checkout proofs retire and autoclose share, protecting primary checkouts and other clones, recovering from vanished `/tmp` checkouts, and `coga delete` — with terminal-owner cleanup and the branch-sweep archive in its leaves.
---

# Retiring tickets and checkouts

You do not delete your own feature branch. `coga retire` (manual, while the
ticket and its `## Dev` lines exist) and the daily autoclose sweep (for every
ticket it closes and every open `retires.md` entry) run one shared set of
[checkout proofs](#the-checkout-proofs). Ticket work no longer creates linked
worktrees ([coga/checkouts](../checkouts/SKILL.md)), so a current ticket
records only `branch:` and the disposal is branch-only. A ticket from the
retired linked-worktree layout may still record `worktree:`; the disposal
removes that worktree first, since a branch checked out in a linked worktree
cannot be deleted, then prunes the branch. Keep `worktree:` accurate where it
exists; it is what they act on.

This topic owns only what those jobs share. Each job's own procedure lives
with its ticket: `coga retire` in the packaged `bootstrap/retire/ticket.md`,
the autoclose and branch-sweep passes in the `recurring/autoclose-merged` and
`recurring/branch-sweep` templates. Implementation detail is in
[coga-dev/internals/branch-sweep](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/internals/branch-sweep/SKILL.md).

## Leaves

- [coga/checkout-cleanup/terminal-owners](terminal-owners/SKILL.md) —
  terminal owners and closed PRs: ownership, durable branch debt,
  authorization, and when cleanup runs.
- [coga/checkout-cleanup/branch-sweep](branch-sweep/SKILL.md) — branch-sweep
  protection, the `retired/<branch>` archive, and
  `[git] worktrees_ticket_owned`.

## The checkout proofs

A recorded worktree is removed only when:

- Git identifies it as a linked worktree of the same repository, still on the
  recorded branch;
- no other non-terminal ticket in any Coga workspace of the same Git checkout
  records that branch or worktree (a refused or incomplete claim scan keeps
  even a branch-only disposal pending, which autoclose reports and retains);
- no PR for that head is open;
- the branch has landed on control or still equals the recorded merged PR head.

After these proofs, every branch the ticket owns (each `## Dev` `branch:`
line) that is still present locally or on the remote goes through the branch
sweep restricted to those names, under the
[terminal-owner rule](terminal-owners/SKILL.md) and the
[archive gate](branch-sweep/SKILL.md). Each candidate gets its own
cross-workspace live-claim check first. A kept branch is reported with its
reason, and the disposal stays pending while its local ref survives. This
step is skipped while the recorded worktree survives.

Local cleanup precedes remote deletion. Local deletion deletes only the tip
it authorized; remote deletion re-verifies the exact head and uses
force-with-lease, so a reused branch is never deleted on stale PR state. A
forced local delete logs the deleted tip SHA for reflog recovery.

**Ignored state.** Tracked, untracked, and ignored files all preserve the
checkout, except regenerable caches (`__pycache__`, `.pytest_cache`,
`.ruff_cache`, `.mypy_cache`, and Coga's rebuilt `.agent-skills/` symlink
view), which retire deletes and counts. A copied `coga.local.toml` is judged
by content: byte-identical to the operator's own (`COGA_LOCAL_CONFIG` when
set) it is deleted and counted, since the original survives; an edited copy
preserves the checkout. Other machine-local state (`.env`, `.venv/`,
`.coga/`, agent discovery links) preserves it. For ignored-only state retire
prints and records the explicit opt-in `git worktree remove --force
'<path>'`; it never offers that over tracked or untracked work.

Reported for manual disposal: a stale linked worktree now on another branch;
a checkout shared with another live ticket or an open PR; a locked or dirty
worktree; and a recorded path already gone (reported, not pruned).

## Primary checkouts and other clones

A primary checkout is never directory debt, including another clone's primary
and independent sandbox clones: Git topology cannot prove a clone disposable,
and it may hold untracked or ignored data. Autoclose preserves such a
directory and never recommends deleting it.

The branch stays debt in the repository that owns it, recorded as the entry's
`owner` for foreign primary and foreign linked checkouts. When the recorded
checkout is a primary or its directory is gone, autoclose never deletes a
same-named branch in the sweeping clone; an existing foreign *linked*
worktree is the exception, whose recorded branch is judged in the sweeping
clone. A remaining foreign branch is reported for manual cleanup in its
owning clone. The owning clone's own daily branch sweep runs the ordinary
proofs on the entries that record it as `owner`, then discharges and
publishes them (`coga/recurring/scheduling`), so the manual step remains only
for a clone that does not run `coga recurring`. An unreadable owner or branch
list keeps the entry pending, and so does a missing owner of a foreign linked
worktree. Once the owner's branch is gone, a primary-checkout entry
discharges with no directory deletion or manual `retires.md` edit; foreign
linked worktrees still owe their directory cleanup.

### Accepted disappearance policy

For an independent clone recorded as its own owner, a missing directory is
treated as deletion of the clone and its branch, so the entry clears. A
missing path does not prove deletion — relocation or a temporarily
unavailable filesystem looks the same — but automatic discharge keeps deleted
sandbox clones from generating reminders forever. The cost: a surviving
clone's branch cleanup can be forgotten if its recorded path disappears. The
policy drops bookkeeping only; it never deletes a clone.

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
(here, as in `coga/checkouts`, `origin` and `main` stand for the configured
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
abandoned ticket with nothing to retro. `coga run delete-task <slug>` does
the same removal without syncing. Both hold the checkout-local state lock.
Bootstrap tickets are not deletable. `--keep-control-checkout` is the
Retro-only form: accepted only from a linked worktree, it still pushes to the
remote control branch but does not fast-forward another checkout that has
control checked out; from the primary checkout it fails before deleting. In a
sandbox that cannot create a linked worktree, Retro may use an independent
clone and plain `coga delete`.
