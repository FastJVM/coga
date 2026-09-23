---
name: coga/internals/recurring-temp-worktrees
description: How an unattended `coga recurring --all` child services a checkout parked off the control branch from a temporary linked worktree — deterministic-only execution, hybrid pause, process-group cancellation, run-record transfer, and SIGKILL-survivor recovery.
---

# Recurring temporary control worktrees

When an `--all` child's catch-up fails *only* because the control branch is not
checked out, and nothing else holds that branch, the child services the repo
from a temporary linked worktree instead of failing every sweep until a human
runs `git checkout` (`recurring_runner._service_from_control_worktree`).
Single-repo commands never create worktrees; they relay into an existing one
([recurring-control](../recurring-control/SKILL.md)).

## Shape

- `git worktree add` under the system temp dir checks the control branch out
  genuinely. A missing local control ref is created from the freshly fetched
  remote-tracking ref (`git.fetch_control`), never checkout-wide `FETCH_HEAD`, so
  single-branch and narrow-refspec clones work.
- The gitignored `coga.local.toml` is seeded into it (without it there is no
  `user` and config load fails), and the scan re-dispatches from the mirrored
  Coga workspace: the checkout root, or the nested Coga directory in a monorepo.

Why this shape:

- **The operator's state never moves.** No stash, switch or restore; branch,
  tracked and untracked files and stash list are untouched. The one deliberate
  local write is the gitignored run transcript copied back. Stash-and-switch
  would hold work hostage, conflict with the scan's writes, and strand work on a
  cron timeout.
- **A real checkout, not a detached HEAD.** `git.sync_log` and
  `_sync_recurring_create_paths` refuse to publish from detached HEAD; without
  that the period task would land without its ledger line.
- **`git worktree add` is the lock.** Git will not check a branch out twice, so
  a second sweep or any other holder loses there and gets the loud refusal
  naming the holder and the `git -C <root> checkout <control>` remedy.

An ahead or diverged control checkout is out of scope and fails loud.

## Deterministic only

No agent runs here, TTY or not: a throwaway worktree is the wrong place for a
session that edits files and opens PRs. Existing periods are admitted from the
`ticket.py` frozen in the materialized task (including statuses surfaced by
`--force`), never the mutable template. File presence admits the script but does
not prove it completes the period, so the inner runner threads a **hard no-agent
reason** through shared launch: if the script leaves its current or next
agent-owned step open, launch returns before agent-only setup, keeps the
script's output, and the runner **pauses that exact period** for a later
launch from a durable checkout. Skipped agent templates and refused hybrid
handoffs are named with the temporary-worktree reason (not "requires a TTY"),
and the `--all` summary lists these repos separately.

## Cancellation and cleanup

The inner scan runs in its own process session. Once its handle is known,
cancellation signals the whole **process group** and waits for the leader, so a
`ticket.py` descendant cannot keep writing to a removed checkout. Known-safe
cleanup runs in a `finally` — success, non-zero recipe exit, exception,
SIGINT/SIGTERM. If an interrupt lands after a possible fork but before the
handle and process-group ID are published, cleanup **retains** the registered
worktree without reading its run records; the operator must confirm nothing
still uses it.

Before removal, every `.coga/recurring-runs/*.md` transcript is copied to the
matching workspace in the durable checkout; a same-name different-content record
is kept side by side. A failed transfer retains the worktree rather than
destroying the only copy.

## SIGKILL survivors

Each temp parent carries a versioned repo/branch/workspace ownership marker with
the wrapper PID and the inner spawn state: `starting` before spawn, then the
process-group ID. A later run removes that exact Coga-owned checkout only when
the wrapper is dead and either no child started or the published group is dead,
after transferring its run records (retaining it if that fails). An ambiguous
`starting` window, a live wrapper or group, an old or invalid marker, and any
unrelated user worktree are all retained. `--all` discovery prunes these temp
parents (prefix plus marker), even when `<path>` includes `/tmp` or `/`.
