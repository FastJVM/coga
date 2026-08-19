---
slug: detect-stranded-ticket-writes-across-checkouts
title: Detect stranded ticket writes across checkouts
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow: null
secrets: null
---

## Description

Follow-up spun out of `launch-ignores-the-recorded-worktree-stranding-bla`
(see that ticket's design spec and blackboard for the reproduction). That
ticket ships a `requires: dev` completion gate that refuses `coga bump` when
the ticket copy being synced lacks a usable `## Dev` linkage. Two residuals
remain unaddressed:

1. **Divergence detection (candidate (c) there).** The gate proves the synced
   copy carries `branch:`/`worktree:`; it does not notice that *another*
   checkout's copy of the same ticket has diverged (e.g. blackboard prose or a
   duplicate `## Dev` written in the feature checkout). A sync-side check —
   bump or validate comparing the ticket blob across linked worktrees /
   the recorded worktree — could surface stranded writes generally. Known
   hard parts: in the primary-copy failure mode there may be no `worktree:`
   pointer to follow; `git worktree list` cannot see independent `/tmp`
   fallback clones; and reconciling divergent free-form markdown needs merge
   semantics.
2. **Committed-duplicate PR conflict.** A stranded ticket edit *committed on
   the feature branch* seeds a `ticket.md` merge conflict when the PR lands
   (the 2026-08-08 PR #90 evidence shape). Uncommitted duplicates are already
   caught by open-pr's cleanliness gate (`open_pr.py:373-383`); committed ones
   are not.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
