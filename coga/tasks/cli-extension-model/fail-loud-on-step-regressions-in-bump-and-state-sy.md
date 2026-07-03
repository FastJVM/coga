---
slug: cli-extension-model/fail-loud-on-step-regressions-in-bump-and-state-sy
title: fail loud on step regressions in bump and state sync
status: draft
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- coga/architecture
- coga/sync
- coga/codebase
skills: []
workflow: null
secrets: null
script: null
---

## Description

Make step-state writes fail loud when they would move a ticket backward,
instead of silently clobbering newer state (principle 6: fail loud).

Two guards:

1. **Compare-and-swap in `coga bump`.** A launched session knows which step it
   was composed for. If the on-disk `step:` no longer matches when the bump
   runs (another chain already advanced it), refuse with an error naming both
   steps instead of advancing from stale state.
2. **Regression check in the git ticket-state sync.** Before committing a
   "Sync coga state" that changes a ticket's `step:`/`status:`, compare against
   the committed version. If the write would move `step:` *backward* (or
   resurrect a pre-bump blackboard, i.e. the file shrinks around the fence
   while step regresses), refuse and report instead of committing — the
   on-disk regression stays visible and the log names it, rather than a quiet
   "Sync coga state" burying it.

Out of scope: a filesystem mutex or lock. The no-mutex design stands; this
ticket only makes divergence loud at the write, not impossible.

## Context

Motivating incident (2026-07-02, ticket
`cli-extension-model/move-the-recurring-scan-into-a-dream-shaped-task`):

- Two supervisor chains ran the same `in_progress` ticket concurrently. Each
  independently ran peer-review → open-pr → review, opening duplicate PRs
  (#506 and #507) and bumping to step 6 twice.
- At 22:56 a stale session's "Sync coga state" commit (`bdb16681`) rewound the
  ticket from `step: 6 (review)` back to `step: 4 (peer-review)`, flipped
  `assignee:` back to the agent, and deleted 64 blackboard lines including the
  peer-review verdict and the PR link. The task then looked "never bumped".
- Restored by hand from `f1bd3e61` (commit `89ec9458`).
- Aggravating factor: sandboxed sessions hit `git add` failures ("Read-only
  file system", non-fatal by design), so one chain's progress was invisible to
  git and fed the stale-copy interleaving.

Both guards are one-comparison-shaped checks on existing write paths
(`commands/bump.py` and the shared task-state sync), not new machinery.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
