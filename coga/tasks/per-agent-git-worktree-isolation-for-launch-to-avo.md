---
slug: per-agent-git-worktree-isolation-for-launch-to-avo
title: Per-agent git worktree isolation for launch to avoid intra-clone autostash
  races
status: draft
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
secrets: null
script: null
---

## Description

Give each launched agent its own `git worktree` (in `launch.py`) so concurrent
relay activity within a single clone can't race one shared working tree. The
spool-merge fix (ticket `prevent-autostash-spool-conflicts-on-control-branc`)
made the *cross-clone* state-plane contention safe, but the intra-clone case is
separate: a recurring sweep and an agent's `relay mark`/`bump` can both run
`git rebase --autostash` against the same checkout at once, which is a
working-tree-level race a mergeable spool does not address.

This is harness behaviour, not a base-prompt instruction. Scope: decide where
per-launch worktrees live, lifecycle/cleanup, and how task-state sync (already
worktree-aware via `git rev-parse --show-toplevel`) interacts with them.

## Context

Split out of `prevent-autostash-spool-conflicts-on-control-branc` (see its
blackboard "Out of scope" + follow-up specs). Relevant code: `launch.py`,
`git.py` (`sync_task_state`, `_rebase_onto_remote`). The cross-clone fix is the
companion already shipped.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
