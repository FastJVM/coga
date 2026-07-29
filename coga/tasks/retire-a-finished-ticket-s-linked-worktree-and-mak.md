---
slug: retire-a-finished-ticket-s-linked-worktree-and-mak
title: Retire a finished ticket's linked worktree, and make branch-sweep report worktree-held
  branches
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
  - coga/architecture
  - coga/codebase
  - dev/code
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
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

Filed by the Dream run of 2026-W31 (Phase 2 knowledge scan, finding F14, class
`gap`).

## The gap

`coga/contexts/dev/code/SKILL.md` tells every code ticket to create a feature
worktree and record it under `## Dev`. **Nothing anywhere removes it.** Coga
never runs `git worktree remove` — not in `retire`, not in `branchcleanup`, not
in `branchsweep`.

The consequence compounds into a second bug. `branchsweep.sweep_branches` skips
only `_current_branch(root)` — the HEAD branch of the sweeping checkout. A branch
held by a *linked* worktree is therefore not recognized as live, falls through to
`delete_local_branch`, and `git branch -d/-D` refuses it ("checked out at ..."). The
failure is noted and **the sweep still exits 0**, so the branch looks swept and
is not.

## Evidence

This repo currently carries 17 worktrees and 25 non-main branches. The
2026-07-27 `rebase-stale-worktrees` run reported "17 live branches, all stale, 16
already-merged squash residue" — one hour after `branch-sweep` ran clean and
exited 0 that same morning.

## Scope

The knowledge gap and the code gap are separable and could ship independently:

1. **Knowledge** — `coga/contexts/dev/code/SKILL.md` (`## Checkout boundary`)
   should state when and where a ticket's worktree is removed as the ticket
   lands, and who does it.
2. **Code** — `branchsweep` should recognize worktree-held branches (they are
   enumerable via `git worktree list --porcelain`) and report them as *blocked*
   rather than silently failing to delete them. Decide whether a blocked branch
   should make the sweep exit non-zero, or stay non-fatal but visible.

Open design question for the human: should worktree retirement be automatic (on
`mark done`, on merge) or an explicit operator step? That choice determines
whether this needs a new command surface.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Findings

- The branch-sweep half already landed independently in PR #669
  (`8237453e`). Current `main` prunes stale worktree registrations, enumerates
  live worktree-held branches, preserves both refs, and reports the distinct
  non-fatal `skipped-worktree-pinned` outcome. No duplicate implementation is
  needed here.

## Dev

branch: retire-linked-worktree
worktree: /home/n/Code/codex/coga-retire-linked-worktree

## Decision

- Retire linked worktrees automatically in `coga retire`, before its existing
  branch cleanup and Retro task creation. Retire is the point where the done
  ticket still exposes `branch:` / `worktree:` / `pr:` and already owns branch
  disposal; `mark done` remains a lifecycle transition rather than a
  filesystem cleanup side effect.
- Remove only a recorded checkout that Git identifies as a linked worktree of
  the same repository. Use ordinary `git worktree remove` without `--force`;
  dirty, locked, missing, unrelated, and independent fallback-clone paths are
  preserved and reported. Branch cleanup then retains its existing merged-PR
  safety gates.
- Update both the live and packaged `dev/code` contexts so the operator and
  future agents can see who retires the checkout and what survives for manual
  inspection.
