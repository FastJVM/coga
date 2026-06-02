---
title: land ticket-state commits on main from any branch — cross-branch sync (B)
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/sync
- relay/codebase
- relay/architecture
- dev/code
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
  - name: open-pr
    skills:
    - code/open-pr
  - name: review
    skills: []
    assignee: owner
---

> **This is ticket B of a 3-ticket split.** A
> (`git-sync-a-helper-and-same-branch`) ships the
> `src/relay/git.py` helper, config, same-branch commit+push wiring, and the
> real-git test fixture. **B depends on A being merged first.** C
> (`git-sync-c-panic-and-ticket-auth`) wires the bespoke
> sites. This ticket is the load-bearing, highest-risk piece.

## Description

After ticket A, relay auto-commits and pushes ticket-state files when the
repo is on the control branch (`main`), and no-ops with a warning when on
a feature branch. B removes that limitation: make control-plane state
reach `main` **from any branch**, without disturbing the in-progress
feature working tree.

The intent (see A's "control-plane / feature split"): `relay-os/tasks/<slug>/`
files are shared team state and must hit `main` immediately even while an
agent is mid-feature-work on a branch. When on a feature branch, the task
files should land on `main` (the shared source of truth) **and** be present
on the current branch — feature code stays where it is.

Done looks like: from a feature branch with uncommitted code in the working
tree, a `relay bump` (etc.) lands the task files on `origin/main` without
touching or losing the feature work, and the test fixture proves it under
concurrency.

## Acceptance Criteria

- [ ] From a feature branch, `sync_task_state` lands the task dir on
  `origin/main` **and** commits it on the current branch's HEAD, without
  ever checking out `main`.
- [ ] The feature working tree is untouched throughout: pre-existing
  **staged** and **unstaged** code changes outside the task dir survive
  unchanged (no sweep, no stash, no reset). Asserted in the fixture.
- [ ] The current-branch commit is scoped to the task dir only (reuses A's
  `git commit --only -- <task-dir>`); unrelated staged paths stay staged.
- [ ] A non-fast-forward `origin/main` (it moved under us) is handled by a
  bounded fetch-rebuild-retry loop, not a crash. After the loop, the
  previously-landed competing commit **and** our task commit are both on
  `origin/main` — nothing is clobbered. Asserted in the fixture.
- [ ] The same-branch case (HEAD == control branch) keeps A's behavior
  (commit on HEAD + push); B does not regress any A test.
- [ ] Repo nesting still resolves correctly (git toplevel ≠ `cfg.repo_root`):
  reuses A's `_toplevel` / `_relative_to_root`.
- [ ] Offline / fetch-or-push failure on the control branch crashes loud
  (`GitError` → stderr + `log.md` → `typer.Exit(1)`), matching A's settled
  failure model. `[git].enabled = false` and "not a git repo" remain soft
  no-ops.
- [ ] No new config keys; no new locking primitive (CAS via the push +
  `update-ref`, per relay's no-mutex architecture).
- [ ] `relay/sync` context (live + packaged copies) updated to describe the
  cross-branch landing, replacing the "ticket B handles this" placeholder.
- [ ] `python -m pytest` green (modulo the one pre-existing unrelated
  `test_packaging` failure A also saw); `relay validate --json` on
  `example/` clean.

## Proposed Shape

**Files changed**
- `src/relay/git.py` — the cross-branch landing path + retry loop (the bulk).
- `tests/conftest.py` — extend the `git_repo` fixture/`GitRepo` helper with a
  competing-push helper and feature-branch assertions.
- `tests/test_git.py` — new cross-branch + concurrency tests.
- `relay-os/contexts/relay/sync/SKILL.md` and
  `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/sync/SKILL.md`
  (and the materialized `relay-os/bootstrap/contexts/...` copy) — document
  cross-branch sync.

**`git.py` control flow.** `sync_task_state` keeps A's guards (disabled /
not-a-repo / GitError boundary) unchanged. After resolving `root` and
`branch`:

1. **Commit on HEAD (both cases).** Extract A's commit body into a shared
   `_commit_task_dir(root, rel, message) -> bool` (`git add -- rel`; if
   staged, `git commit --only -m message -- rel`). This is exactly A's
   working-tree-safe commit; call it on HEAD regardless of branch so the task
   files are committed on whatever branch is checked out. **Exception —
   detached HEAD** (`branch == "HEAD"`): skip the HEAD commit (warn; a commit
   on detached HEAD would be orphan-ish), but still land on the control branch
   via step 3. Detached HEAD takes the feature-branch (`_land_on_control_branch`)
   path, just without the local HEAD commit.
2. **If `branch == cfg.git_control_branch`:** if step 1 committed, `git push
   <remote> <branch>` — i.e. A's same-branch path, unchanged.
3. **Else (feature branch):** call the new
   `_land_on_control_branch(cfg, root, task_path, rel, message)`.

**`_land_on_control_branch` — pure plumbing, push-as-CAS, no working tree.**
Bounded loop (`_MAX_SYNC_ATTEMPTS = 5`):

1. `git fetch <remote> <branch>` → read tip as `base = git rev-parse
   FETCH_HEAD`. (Fetch failure → `GitError`, crash-loud.)
2. Build the target tree in a **temporary index** so neither the real index
   nor the working tree is disturbed — set `GIT_INDEX_FILE=<tmp>` for these:
   - `git read-tree <base>` (temp index = origin/main's tree)
   - `git rm -r --cached --ignore-unmatch -- <rel>` (drop stale task subtree)
   - `git add -- <rel>` (stage the *working-tree* task files into temp index)
   - `tree = git write-tree`
   This overlays the current task dir onto origin/main's full tree; code
   paths keep origin/main's blobs (we only touch `<rel>`).
3. If `tree == <tree of base>` → nothing to land, return (no-op).
4. `new = git commit-tree <tree> -p <base> -m <message>`.
5. `git push <remote> <new>:refs/heads/<branch>`.
   - exit 0 → success: best-effort fast-forward local `refs/heads/<branch>`
     to `new` via `update-ref` (failure here is logged, not fatal — origin
     already has the commit); return.
   - rejected non-fast-forward (stderr matches `rejected` / `non-fast-forward`
     / `fetch first`) → loop again (refetch picks up the new tip).
   - any other non-zero → `GitError`, crash-loud.
6. Loop exhausted → `GitError("could not land on <branch> after N attempts —
   contention")`.

The temp-index env is threaded through a small `_run_git(..., env=...)`
extension (or a dedicated `_run_git_index` helper). The push is the atomic
serialization point: concurrent relay processes (local *or* cross-machine)
each fetch→build→push, exactly one fast-forwards per round, losers refetch
and retry — no lock file, consistent with `relay/architecture`'s no-mutex
model.

**Fixture extensions (`conftest.py`).** Add to `GitRepo`: a
`push_competing_commit(path, text)` helper that commits an unrelated file
straight to `origin/main` (simulating another process landing first), and
reuse the existing `checkout_branch`. The `git_repo` fixture already seeds a
bare origin and runs on `main`; tests call `checkout_branch` to move onto a
feature branch.

**New tests (`test_git.py`).**
- feature-branch sync lands on `origin/main` *and* commits on the feature
  branch; `origin` gets the task file.
- feature working tree undisturbed: seed an unstaged edit and a staged edit
  to a code file outside the task dir; after sync, both are exactly as left
  (still unstaged / still staged, not pushed, not in any commit).
- non-fast-forward retry: `push_competing_commit` before sync; assert sync
  still succeeds and both the competing file and the task file are on
  `origin/main` (anti-clobber).
- no-op when origin/main already has identical task content.
- feature-branch fetch/push failure crashes loud (remove origin) — log + exit.

## Out of Scope

- **Hardening the same-branch path against non-fast-forward.** It stays
  crash-loud as A shipped it; the retry loop is added only to the detached
  cross-branch plumbing path (where retry is trivial because no working tree
  is involved). A separate ticket can unify if needed.
- **Pushing the feature branch.** B lands control-plane state on `main` and
  commits on HEAD; pushing the feature branch / opening its PR remains the
  dev/PR flow's job.
- **Propagating task-file *deletions* within a task dir to `main`.** The
  overlay mirrors current task-dir files; the three canonical files
  (`ticket.md` / `blackboard.md` / `log.md`) are never deleted, so this is a
  non-scenario. (The `rm --cached` + `add` rebuild does handle modify/add
  correctly; whole-file deletes are simply not exercised.)
- **The bespoke call sites** (`relay panic`, `relay ticket` authoring) —
  ticket C.
- **New config surface or a configurable retry count** — `_MAX_SYNC_ATTEMPTS`
  is a module constant.

## Context

- **Design step first (this is why the workflow has one).** Two viable
  working-tree-free mechanisms — pick and justify on the blackboard before
  coding:
  1. **Pure plumbing**: read `main`'s tree, splice in the `relay-os/tasks/<slug>/`
     blobs (`git hash-object` / `read-tree` / `update-index`), `git commit-tree
     -p refs/heads/main`, `git update-ref refs/heads/main <new> <old>` (the
     compare-and-swap form), then `git push origin main`. Touches no working
     tree at all — the natural fit.
  2. **Worktree pinned to `main`**: a hidden `git worktree add` dir; write +
     commit + push there. Simpler conceptually but adds lifecycle/GC, a
     second on-disk copy, and re-staging the same paths.
  The owner reviews the chosen mechanism at the `review-design` step.

- **Own the full edge/failure matrix — this is the bulk of B.** None of it
  has prior art in this repo:
  - **Non-fast-forward** (`main` behind `origin/main`): fetch + retry. The
    CAS `update-ref refs/heads/main <new> <old>` is the natural primitive.
  - **Concurrent relay processes** racing `refs/heads/main` (the `relay
    launch` auto-chain, the post-merge hook, manual commands): **no locking
    exists anywhere in the codebase** (confirmed by grep). Introduce a lock
    or a CAS-retry loop. See `relay/architecture` for relay's locking model
    before inventing one.
  - **Offline / no remote**: per A's failure policy + `[git].enabled`.
  - **Repo nesting**: git toplevel ≠ `cfg.repo_root` when `relay-os/` is a
    nested subdir — resolve them separately (A already does this for the
    same-branch case; extend it).

- **Also land on the current branch.** The task files must end up on the
  feature branch too (not only `main`) so the agent's checkout reflects the
  ticket state it's working against. Decide whether that's a normal commit
  on HEAD plus the separate `main` update, or a cherry-pick/merge — and keep
  the feature working tree (staged + unstaged code) untouched throughout.

- **Extend A's git.py and fixture, don't fork them.** B slots the
  cross-branch path into the helper A designed for extension, and extends
  the real-git test fixture with feature-branch + concurrency assertions
  (commit lands on `main` and the branch; feature working tree undisturbed;
  two processes don't clobber `refs/heads/main`).

- **Auto-push to `main` bypasses PR review by design** (control-plane state
  is not code) — already accepted in A; B just makes it work from anywhere.

- **`src/relay/` work, higher review bar.** Update `example/` + `tests/`;
  run `python -m pytest` and `relay validate --json`.
