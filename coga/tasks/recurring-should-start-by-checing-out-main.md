---
slug: recurring-should-start-by-checing-out-main
title: Service single-repo recurring runs from a control worktree too
status: draft
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- coga/recurring
skills: []
workflow: code/design-then-implement
secrets: null
---

## Description

`coga recurring` should be runnable from any working directory, on any branch.
Today it is not: bare `coga recurring` and `coga recurring launch <name>` both
hard-refuse when the checkout is not on the configured control branch, so
`coga dream` from a feature branch is a dead stop that only a manual
`git switch main` clears.

The sibling ticket `service-recurring-from-a-temp-control-worktree-ins` fixes
this for the `coga recurring --all` child only, by servicing the repo from a
temporary linked worktree holding the control branch. This ticket extends that
same mechanism to the entry points that ticket explicitly leaves out of scope —
bare `coga recurring`, `coga recurring launch <name>`, and `--interactive` —
and, unlike the `--all` path, **runs agent templates in the worktree** rather
than skipping them.

Done looks like: from a repo parked on a feature branch with a dirty tree,
`coga dream` creates and launches its period task, the agent session runs on
the control branch inside the temp worktree, its work and the serviced-period
ledger reach `<remote>/<control-branch>`, the temp worktree is removed, and the
operator's checkout is byte-identical afterwards — same branch, same `HEAD`,
same `git status --porcelain --untracked-files=all --ignored`, no new stash
entry.

## Context

### The refusal being removed

Both single-repo entry points return `2` before scanning:

- `run_recurring_scan` — `recurring_runner.py:693`,
  `if not require_fresh_control and _refuse_non_control_branch(cfg)`. The gate
  applies to the *non*-`--all` path; `--all` children use the stricter
  `require_fresh_control` freshness gate instead.
- `run_recurring_named` — `recurring_runner.py:967`, unconditional
  `_refuse_non_control_branch(cfg)`.

`_refuse_non_control_branch` (`recurring_runner.py:122`) prints "Recurring
launch refused: the current checkout is on branch 'x', not the configured
control branch 'main'" and tells the human to `git switch main`. It exempts
only `git_enabled = false` and confirmed non-git workspaces.

Correct the record when designing: the sibling ticket's Out of Scope claims
these entry points "keep today's best-effort behavior off the control branch
(they scan the working tree they are in)". They do not — they refuse outright.
Verify against the two line references above rather than trusting that
sentence.

### Dependency

This ticket assumes `_service_from_control_worktree(cfg, *, force, interactive,
agent_override)` and the `--control-worktree` inner flag from
`service-recurring-from-a-temp-control-worktree-ins` (currently `in_progress`
at `review-design`) already exist, and generalizes them. Do not build a second
worktree helper. If that ticket has changed shape by the time this one is
designed, re-read its `## Proposed Shape` before writing this spec, and
reconcile rather than duplicate.

That ticket also records two rejected alternatives with full reasoning —
stash/switch/restore of the operator's checkout, and a detached worktree at the
remote tip. Both rejections carry over here unchanged; they are not open
questions.

### Why agent templates change the shape

The `--all` path is recipe-only for a defensible reason: an unattended sweep
with no TTY drops agent templates anyway, so the set it must serve needs no
interactive checkout. Single-repo runs are the opposite case — they are usually
attended, and the agent-backed templates (`dream`, and anything else without a
`ticket.py`) are the entire point of running them by hand.

That makes worktree lifetime the central design problem, and the main thing the
design step has to solve:

- The worktree must survive the whole agent session — `COGA_REPL_IDLE_TIMEOUT`
  (15 min default) plus `max_session` — not just a recipe subprocess. It holds
  the control branch for that entire time, and `git` refuses to check one branch
  out twice, so a concurrent sweep or a human `git switch main` elsewhere fails
  while it is held.
- Anything the agent writes but does not commit and push is destroyed when the
  worktree is removed. Decide explicitly what happens to a session that ends
  dirty — refuse to remove, remove anyway, or park the diff — and cover it in
  Acceptance Criteria.
- The agent's own `coga bump` / `coga open-pr` calls run from inside the temp
  checkout. The `implement` step's `requires: branch` gate is presence-based in
  *the checkout `coga bump` runs from* (see the `code/design-then-implement`
  workflow body), so a period task whose workflow has such a gate needs the
  interaction checked, not assumed.
- Cleanup must hold on success, non-zero exit, exception, SIGINT/SIGTERM, and
  be reaped by the next run after SIGKILL.

### Load-bearing git facts

Carried from the sibling ticket's design so this one need not re-derive them:

- The worktree checks the control branch **out** (rather than `--detach`)
  because `git.sync_log` refuses on a detached HEAD and
  `_sync_recurring_create_paths` skips the local commit there — the
  serviced-period ledger line would never reach control, and every sweep would
  re-fire the period. Checking the branch out also *is* the concurrency lock.
- `coga.local.toml` is gitignored, so a fresh worktree has no `user` and
  `load_config` raises before anything runs. It must be seeded into the
  worktree at 0600.
- The temp worktree must live outside any plausible `--all` scan root, or
  `discover_coga_repos` (`src/coga/workspace_discovery.py:18`) will pick it up
  as another Coga repo.

### Not this ticket

- The `--all` path and its parent summary — the sibling ticket owns those.
- The diverged-control case (control branch checked out but its local commits
  cannot rebase onto the fetched tip). That keeps failing loud.
- Running recurring from a **separate clone or install** pointed at another
  repo. Discussed and deliberately deferred; if wanted, it is its own ticket.
- A general-purpose temp-worktree helper for commands other than `recurring`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
