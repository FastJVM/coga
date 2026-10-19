---
title: Retire a finished ticket
---

## Description

Command ticket for the `retire` verb, and the owner of its contract. It has no
agent phase: launch runs the sibling `ticket.py` with the verb's argv
([coga/script-tickets](context:coga/script-tickets)), and this file describes
what that script does. It creates no task for itself and writes no
blackboard.

`coga retire <slug> [--agent <type>] [--no-launch]` is a default alias for
`coga launch bootstrap/retire -- <slug> ...`. The `--` keeps `--agent` and
`--no-launch` away from launch's own options so they reach the script.
`coga retire --help` prints the script's usage; like any launch, it needs a
configured workspace (`coga.local.toml` with a user).

### Why done and canceled differ

Owner decision, 2026-10-13: positive learning already landed in the merged PR
(the same PR updates the owning topic), and negative learning lives in the
ticket, usually as the cancellation reason. So a **done** ticket is retired
deterministically, with no agent, and a **canceled** ticket gets a Retro task
that extracts the cancellation reason and any other negative learning before
deleting it.

### Steps

1. **Refuse unless finished.** The slug resolves like any task ref (unique
   prefix included). An unknown slug, a status other than `done` or
   `canceled`, or a configuration error exits 2.
2. **Dispose of the checkout.** Read `branch:`, `worktree:` and `pr:` from
   the ticket's `## Dev` section while the ticket still exists, and dispose of
   the recorded worktree and every owned branch under the
   [checkout proofs](context:dev/checkout-cleanup/proofs), including the
   [terminal-owner rule](context:dev/checkout-cleanup/terminal-owners).
   Primary checkouts and other clones are never disposed of
   ([dev/checkout-cleanup](context:dev/checkout-cleanup)). This runs only from
   a checkout on `[git].control_branch`: off control, with `[git].enabled`
   false, or outside a Git work tree, retire prints
   `Retire: checkout cleanup skipped ...` and leaves the checkout and branch to
   autoclose or `branch-sweep`.
3. **A kept checkout is a bug.** The ticket is the checkout's only owner
   record, so a worktree or owned branch the proofs kept must not lose it.
   Retire skips the worklist discharge and exits 2:
   - done: it deletes and creates nothing; fix the checkout by hand and run
     `coga retire` again.
   - canceled: it creates the retire task already `blocked` with what it kept
     and why (which notifies the owner, as `coga block` does) and launches
     nothing; fix the checkout, then `coga unblock` and `coga launch` the
     retire task.
4. **Discharge the worklist.** Drop the slug from any recurring template's
   `retires.md`, but only once its local branch is gone (judged in the owning
   repository when the entry records another clone as `owner`) and its
   recorded worktree directory is gone or is a repository's primary checkout.
   A worklist error is reported, never fatal.
5. **Done: delete.** Remove the task as `coga delete` does and publish the
   removal (`Ticket: <slug> — deleted (retire)`); recover with `git restore`.
6. **Canceled: Retro.** Scaffold `retire-<slug>` straight to `active` on the
   one-step `direct/body` workflow, its body rendered from the `retire.md`
   resource (a repo override substitutes only `{slug}`), and publish it
   (`Ticket: retire-<slug> — created (retire)`). The body invokes the
   `retro/done-ticket` skill, which opens the PR that records `## Retro`,
   edits knowledge if warranted, and deletes the source task in the same PR.
   `--agent` picks that task's main agent (default: the configured default
   agent); a canceled retire with no agent configured exits 2. Retire then
   launches the task in-process and exits with its code, unless
   `--no-launch`, which prints the `coga launch` command instead. If that
   launch kept local changes after a refused checkout return, retire exits 75
   so the outer launch neither refreshes the checkout nor sweeps them.

`--agent` and `--no-launch` affect only step 6. Branches with no live ticket
are the `branch-sweep` job's.
