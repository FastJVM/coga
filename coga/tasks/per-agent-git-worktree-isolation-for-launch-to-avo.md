---
slug: per-agent-git-worktree-isolation-for-launch-to-avo
title: Per-agent git worktree isolation for launch to avoid intra-clone autostash
  races
status: active
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- coga/sync
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

Add **per-agent `git worktree` isolation** to `launch.py`, gated by a simple
repo-local on/off toggle (off by default). When enabled, each launched session
runs in its own `git worktree`; when off, behaviour is unchanged (today's
shared checkout). No multi-mode enum — just worktree-or-not.

This lets multiple concurrent agents (on *different* tickets) run from a single
clone without racing a shared working tree. Motivating goal: today you keep
**several physical checkouts** as a manual workaround so concurrent agents
don't fight over one tree; worktree isolation lets one instance safely
multiplex many agents and retires that workaround.

The race it closes is **intra-clone and working-tree-level**: a recurring sweep
and an agent's `relay mark`/`bump` can both run `git rebase --autostash`
against the same checkout, contending the one `.git/index` / `index.lock` /
rebase-state / stash stack. Only a separate working tree removes that shared
resource. (A per-branch scheme was considered and rejected: separate refs still
share one tree, so they don't fix this race.)

This is harness behaviour, not a base-prompt instruction, and is the
**intra-clone half** of the fix. The *cross-clone / several-users* case is a
different race (push/merge contention on the control branch) and is already
handled by the shipped mergeable-spool companion — worktrees need not address
it.

## Context

Split out of `prevent-autostash-spool-conflicts-on-control-branc` (see its
blackboard "Out of scope" + follow-up specs). Relevant code: `launch.py`
(no worktree logic today), `git.py` (`sync_task_state`, `_rebase_onto_remote`).
`sync_task_state` is **already worktree-aware** via `git rev-parse
--show-toplevel`, so per-session worktrees reach the same `coga/tasks/` state
through the shared object db + control-branch sync. The `coga/sync` context
documents the spool contract and explicitly defers this intra-clone race to
"its own ticket" — this one. The cross-clone spool fix is the companion already
shipped.

Note coga already has a **second worktree layer**: `code/implement` has agents
create a *feature* worktree for their code. The launch-level worktree here is
harness-owned and exists only to isolate the state-plane autostash; the work
must say how the two layers coexist (e.g. the feature worktree is forked from
the launch worktree's `main`, not the primary checkout).

Gotchas surfaced in the bootstrap evaluator review:

- The spawn path (`spawn_agent_session` / `run_with_done_marker` /
  `subprocess.run`) currently takes **no working-directory argument** — the
  agent runs in the process cwd and usage capture keys off `Path.cwd()` /
  `ref.path`. "Run in a worktree" is therefore a cwd-plumbing change threaded
  through the whole spawn path, not a one-liner.
- Keep it **lock-free**: coga is intentionally mutex-free (see
  `coga/architecture`); worktrees must *isolate*, not serialize.
- The autostash race only bites when a session operates **on the control
  branch** (the cross-branch land uses a temp index and never rebases the
  tree), so isolation should target control-branch sessions, not feature-branch
  ones.

<!-- coga:blackboard -->
## Production notes

This blackboard is for active-work handoff notes. Authoring scratch was cleared at activation; durable requirements belong in the ticket body.
