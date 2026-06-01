---
title: land ticket-state commits on main from any branch — cross-branch sync (B)
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
  - relay/sync
  - relay/codebase
  - relay/architecture
  - dev/code
skills: []
workflow: code/design-then-implement
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
