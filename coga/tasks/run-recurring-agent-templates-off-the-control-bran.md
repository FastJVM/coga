---
slug: run-recurring-agent-templates-off-the-control-bran
title: Run recurring agent templates off the control branch
status: draft
owner: nicktoper
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: code/design-then-implement
secrets: null
---

## Description

The hard remainder of "recurring should run from anywhere". Two sibling tickets
cover the easy cases: `service-recurring-from-a-temp-control-worktree-ins`
services the `--all` child's deterministic templates from a created temp
worktree, and `reuse-the-existing-control-worktree-for-recurring` runs the
single-repo sweep from a control worktree that already exists.

What neither covers: running an **agent-backed** recurring template — `dream`,
and the delegating `resolve-conflicts` — when the operator is off the control
branch and **no worktree holds control**, so a checkout has to be created for
the session to run in.

This is not a small extension of the sibling designs. An attended agent session
is long-lived, writes files, creates its own worktrees, and records paths that
outlive the run, so the temp-and-delete shape that is correct for a
seconds-long deterministic sweep breaks in specific, known ways (below). The
design step's job is to decide whether a created checkout for agent sessions is
worth having at all, and if so, what shape it takes — a *persistent* control
worktree being the leading candidate over a throwaway one.

Launch this only after the two siblings have landed, so the design is written
against real code rather than two speculative APIs.

## Context

Cite symbols, not line numbers. `5243dfd5` (`delegate:` field, 2026-08-26)
moved ~306 lines in `recurring_runner.py` and invalidated the line citations in
this work's first draft.

### Known breaks in the throwaway-worktree shape

These are established failures, not open considerations. A design that keeps
the throwaway shape must answer all three.

1. **The agent's own worktree lands inside the directory cleanup deletes.**
   `coga/skills/code/implement/SKILL.md` instructs `git worktree add
   ../coga-<branch-name> -b <branch-name> main`. From
   `/tmp/coga-recurring-X/checkout`, `../coga-<branch>` resolves inside the temp
   parent that the sibling's `finally` `rmtree`s. A Dream run that opens a
   ticket, branches, and implements would have its feature checkout destroyed by
   cleanup. This is the shipped skill's default instruction, not a hypothetical.

2. **`worktree:` gets recorded pointing at a temp path.** `src/coga/open_pr.py`
   reads it back and requires that checkout to exist, be on the branch, be clean
   and ahead of main. After cleanup it does not exist. Relatedly the `implement`
   step's `requires: branch` gate (`src/coga/step_gate.py`) is presence-based in
   *the checkout `coga bump` runs from*, so a period task whose workflow carries
   that gate interacts with the checkout identity directly.

3. **Lock duration is wrong by an order of magnitude.** Checking the control
   branch out *is* the concurrency lock in the sibling's design, and that is
   correct for a sweep measured in seconds. For an agent session it means no
   other checkout of `main` anywhere on the machine — including the operator's
   own `git switch main` in another terminal — for `COGA_REPL_IDLE_TIMEOUT`
   (15 min default) plus `max_session`, potentially hours.

A **persistent** control worktree removes the data-loss path, the recording
path, and the cleanup-on-signal problem in one move, at the cost of a durable
directory to manage. Evaluate it as the primary option.

### Scope check the design must perform first

The payoff here is two templates out of seven. Five carry `ticket.py`
(`autoclose-merged`, `blocker-reminders`, `branch-sweep`, `digest`,
`skill-update`) and are served by the siblings. Only `dream` and
`resolve-conflicts` are agent-backed. If the sibling ticket
`reuse-the-existing-control-worktree-for-recurring` admits agent templates into
an existing control worktree, the remaining gap is "agent template, off
control, and no control worktree exists" — which may be rare enough not to
justify the machinery. **Say so if that is the conclusion**; recommending this
ticket be closed unbuilt is a valid design outcome.

### Delegating templates are unanalyzed

`resolve-conflicts` is a `delegate:` template as of `5243dfd5`: the sweep
performs the delegated launch in the operator's own terminal, with its own
TTY-admission rules and a `coga/log.md` slack-sentinel completion path. Nothing
in the sibling designs considers what a delegated launch means when the sweep
itself is running from a different checkout. This design has to.

### What the agent sees

An agent session inside a control checkout scans the control tip, not the
operator's dirty feature-branch tree. For `dream` that is arguably correct; for
other agent templates it may not be. Whatever the choice, state it — it changes
what the feature *means*, not just how it is built.

### Worktree hygiene facts

- `coga.local.toml`, `.coga/`, and `.agent-skills/` are all gitignored
  (`coga/.gitignore`), so a fresh checkout lacks them. `coga.local.toml` must be
  seeded at 0600 or `load_config` raises before anything runs. `.agent-skills/`
  is rebuilt by `src/coga/commands/launch.py` and self-heals. `.coga/` is
  unanalyzed — decide explicitly. The sibling's note arguing `.agent-skills/`
  "is not needed" reasons from recipes not reading the merged skill view; that
  reasoning is void here, because this path runs agent sessions.
- A created worktree must live outside every plausible `--all` scan root, or
  `discover_coga_repos` (`src/coga/workspace_discovery.py`) picks it up as
  another Coga repo.
- The checkout must have the control branch checked **out**, not `--detach`:
  `git.sync_log` refuses on a detached HEAD and `_sync_recurring_create_paths`
  skips the local commit there, so the serviced-period ledger line would never
  reach control and every sweep would re-fire the period.

### Context to read and update

`coga/contexts/coga/recurring/SKILL.md` is deliberately not attached — at ~9.2k
tokens it dominates the composed prompt for a handful of facts. Read it
directly: `## Recurring runs start on the control branch` is the contract in
question, and the `delegate:` gotcha near the end is the only place TTY
admission for delegated launches is explained. Any behavior change rewrites the
former in the same PR, per the repo's context-in-the-same-PR rule.

### Not this ticket

- The `--all` path (`service-recurring-from-a-temp-control-worktree-ins`).
- Reusing an existing control worktree
  (`reuse-the-existing-control-worktree-for-recurring`).
- The diverged-control case. That keeps failing loud.
- Running recurring from a separate clone or install pointed at another repo.
- Moving the operator's own checkout (stash → switch → run → switch back → pop).
  Rejected with full reasoning in
  `service-recurring-from-a-temp-control-worktree-ins`; not an open question.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
