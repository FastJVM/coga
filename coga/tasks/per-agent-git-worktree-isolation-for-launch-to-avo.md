---
slug: per-agent-git-worktree-isolation-for-launch-to-avo
title: Per-agent git worktree isolation for launch to avoid intra-clone autostash
  races
status: draft
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
  - coga/sync
skills: []
workflow: code/with-review
secrets: null
script: null
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

## Implementation decisions (no design gate — settle these in the PR)

1. **Worktree location** — outside the repo (`../coga-worktrees/<id>`) or a
   gitignored dir inside it (`.coga/worktrees/<id>`)? Tradeoffs: disk layout,
   `.gitignore` hygiene, IDE noise.
2. **Worktree key** — key by **launch/session id** (recommended) so a relaunch
   of a still-running ticket can't collide. Scope is different-tickets-per-
   instance, but session-keying is the safer default.
3. **Lifecycle / cleanup** — remove on normal teardown (`done`/`bump`/`panic`);
   plus orphan reaping for sessions that died mid-launch (`git worktree prune`
   + age threshold). Guarantee no leaked checkouts accumulate. (This half is
   the heaviest part of the change — keep it tight.)
4. **Toggle spelling + default** — simple on/off, default **off** (unchanged
   behaviour when off). No `none`/`branch`/`worktree` enum — that was dropped.
5. **Coexistence with `code/implement`'s feature worktree** — confirm the
   feature worktree forks from the launch worktree's `main`, not the primary
   checkout, and the `worktree:` recorded on the blackboard stays coherent.
6. **cwd plumbing** — the spawn path (`spawn_agent_session` /
   `run_with_done_marker` / `subprocess.run`) takes **no cwd argument** today;
   the agent runs in the process cwd and usage capture keys off `Path.cwd()` /
   `ref.path`. Thread a working-dir through the whole spawn path.
7. **Scope to control-branch sessions** — the race only bites on the control
   branch (cross-branch land uses a temp index, never rebases the tree). Target
   that case; don't needlessly isolate feature-branch sessions.

## Design notes (from bootstrap interview)

- Race is **working-tree-level**: two `rebase --autostash` against one
  `.git/index` → `index.lock` contention, wrong stash-pop, rebase-state
  collision. Only a separate working tree removes the contended resource.
- `branch` mode rejected: separate refs still share one tree.
- Cross-clone / several-users is a **different** race (control-branch
  push/merge) already solved by the mergeable-spool companion. Out of scope.
- Real driver: retire the multi-checkout workaround → one instance multiplexing
  concurrent agents on different tickets.
- Keep it **lock-free**: coga is intentionally mutex-free; worktrees must
  isolate, not serialize.

## Evaluator review

*(Reviewed the earlier draft — `code/design-then-implement`, three-mode enum —
before the switch to `code/with-review` and the worktree-only trim. Its
scope/over-built-enum critiques are resolved by those changes; its spawn-path
and control-branch findings are folded into `## Context` above.)*

- **Description — startable, yes.** The race mechanism (shared `.git/index` /
  `index.lock` / stash stack), the motivating goal (retire multi-checkout
  workaround), and the mode model are all spelled out. A cold agent could begin
  design. Well above average clarity.
- **Workflow fit — good.** Six genuine unresolved design questions (location,
  keying, lifecycle, mode semantics) justify `code/design-then-implement`; this
  isn't a mechanical change. No mismatch.
- **Contexts — `coga/sync` is right but blunt.** `coga/sync` literally
  forward-references "its own ticket" at the intra-clone-race note (git.py-spool
  section), so it's the correct anchor. The ticket already copied the
  load-bearing facts into `## Context`/`## Design notes`, which is the right
  call given `coga/sync` is ~500 lines mostly about notifications. **Missing:**
  `architecture/SKILL.md` (the no-mutex/no-lock model this knob must respect)
  and `codebase/SKILL.md` — both directly relevant to harness/launch work and
  neither attached.
- **Scope — borderline-heavy.** Bundles: a 3-mode config knob, worktree
  creation, lifecycle + orphan reaping (`git worktree prune`), and reconciling
  with the existing `code/implement` feature-worktree layer. The cleanup/reaping
  half could stand alone. `branch` mode is admitted-maybe-stub — if it's a stub,
  the knob is really a `none`/`worktree` boolean and the three-value framing is
  over-built.
- **Assumptions to question.** "launch.py has no worktree logic" — true
  (verified). But the ticket understates the real gap: **`spawn_agent_session`/
  `run_with_done_marker`/`subprocess.run` take no working-directory argument at
  all** — the agent always runs in the process cwd, and usage capture keys off
  `Path.cwd()` and `ref.path`. "Reads a knob and applies it" hides a non-trivial
  cwd-plumbing change through the whole spawn path; call it out before launch.
  "sync_task_state already worktree-aware" — verified true (`_toplevel` uses
  `--show-toplevel`). "Cross-clone already solved" — accurate (explicit-stash
  `_rebase_onto_remote` + compare-and-swap push). One design question to add:
  the autostash race only bites when an agent runs *on the control branch* (the
  cross-branch land uses a temp index and never rebases the tree) — confirm
  worktree isolation targets that case, not feature-branch sessions.
