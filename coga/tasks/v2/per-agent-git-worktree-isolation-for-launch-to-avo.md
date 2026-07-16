---
slug: v2/per-agent-git-worktree-isolation-for-launch-to-avo
title: Per-agent git worktree isolation for launch to avoid intra-clone autostash
  races
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
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

## Dev
branch: per-agent-launch-worktree-isolation
worktree: /home/n/Code/claude/coga-launch-worktree-isolation
pr: https://github.com/FastJVM/coga/pull/487
pr-state: MERGEABLE / CLEAN; no CI checks configured on repo (none reported).

## Implementation summary (implement step — committed, no PR yet)

Shipped on the feature branch above. How each open decision landed:

1. **Location** — gitignored `.coga/worktrees/<id>` at the **git toplevel**
   (operator's call). Outside the tracked `coga/` OS subtree, so the
   `sync_coga_state` sweep never touches it; `.coga/` added to the coga-managed
   host `.gitignore` block (`update.py`) and this repo's `.gitignore`.
2. **Key** — `uuid4().hex` per launch (collision-proof on relaunch). One
   worktree per launch, reused across all chained steps.
3. **Lifecycle** — created just before the supervisor loop, removed in a
   `finally` on every exit path (clean chain, `sys.exit` on agent failure/
   timeout, exception). `reap_orphan_launch_worktrees` prunes + force-removes
   dirs older than 24h on launch entry (crash backstop; the finally is primary).
4. **Toggle** — `[launch].worktree` bool, default off, **shared-repo-only**
   (operator's call; parsed in `_parse_launch`, no local override). Off =
   byte-for-byte today's behaviour (cwd stays None → inherits process cwd).
5. **Coexistence** — the launch worktree is **detached at the control-branch
   tip** (can't check out `main` — it's in the primary tree). The agent's
   `code/implement` feature worktree (`git worktree add ../coga-<b> -b <b> main`)
   is unchanged: shared refs mean `main` resolves identically from inside the
   launch worktree. Documented in `dev/code` (live + packaged).
6. **cwd plumbing** — threaded `cwd` through `spawn_agent_session` →
   `run_with_done_marker` (PTY child `os.chdir` + non-tty `subprocess.run`) and
   the auto `subprocess.run`; `usage_cwd = cwd or Path.cwd()` so transcript
   lookup resolves. The supervisor re-roots `cfg`/`ref` into the worktree
   (`load_config` + `resolve_target`) so reads/spawns/syncs all target it; the
   primary `base_cfg` is kept for teardown (git refuses removing a worktree from
   inside it).
7. **Scope** — detached HEAD forces every sync onto the cross-branch temp-index
   overlay (never rebases a tree), so control-branch contention has nowhere to
   land. Bootstrap tickets (stateless) and non-git checkouts skip isolation.

**Why re-root the whole supervisor, not just the subprocess cwd:** the agent's
`coga bump` rewrites the *worktree's* `ticket.md`; a supervisor still reading the
primary's copy would mis-chain. `os.chdir` was rejected — `coga recurring` calls
`launch()` in-process sequentially, so a global chdir would corrupt the sweep.

**Files:** `config.py` (toggle), `git.py` (add/remove/reap worktree +
`repo_root_in_worktree`), `commands/launch.py` (setup/re-root/cleanup + cwd),
`repl_supervisor.py` (cwd), `commands/update.py` (`.gitignore`), `.gitignore`,
`coga/coga.toml` + template, `coga/sync` + `dev/code` contexts (live + packaged).
**Tests:** worktree helpers + 2 launch integration tests (real-git fixture) in
`test_git.py`; `[launch].worktree` parsing in `test_config.py`; existing spawn
fakes updated for the new `cwd` kwarg. Full suite: 947 passed, 1 skipped.

## Peer review (codex)

Native review: `codex review --base main` initially failed under the managed
sandbox with `Read-only file system`; reran escalated and received four
functional findings. Applied must-fixes on
`/home/n/Code/claude/coga-launch-worktree-isolation` and committed
`67906046 peer-review: apply review findings`.

Fixes applied:

- launch worktree creation now happens before launch-owned task mutations, so
  `_auto_activate` / `mark_in_progress` no longer write through the primary
  checkout when isolation is enabled.
- the live resolved task file/dir and ignored `coga.local.toml` are seeded into
  the isolated worktree before reloading config and resolving the task there.
- launch worktrees detach from full `refs/heads/<control>` (or remote-tracking
  fallback) instead of falling back to `HEAD` from feature checkouts.
- teardown runs a final Coga-state sync and removes the worktree only if no
  recoverable Coga OS changes remain; otherwise it prints the path and preserves
  the worktree for recovery.

Verification:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider tests/test_git.py -q`
  -> 65 passed.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider tests/test_config.py tests/test_git.py tests/test_launch.py tests/test_launch_auto.py tests/test_project.py tests/test_ticket.py -q`
  -> 244 passed.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q`
  -> 948 passed, 1 skipped.

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
