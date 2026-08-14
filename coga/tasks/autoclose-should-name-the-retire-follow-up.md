---
slug: autoclose-should-name-the-retire-follow-up
title: Autoclose should name the retire follow-up
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
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
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

`coga autoclose` bumps a ticket to `done` when its `## Dev` PR merged, and then
nothing points at the next step. Checkout disposal belongs to `coga retire`
(it owns the linked-worktree / open-PR / landed-branch proofs), but retire is a
human-typed command — so an auto-closed ticket's feature worktree and branch
outlive the ticket silently, and by the time anyone notices, the ticket's
`## Dev` lines may already be gone.

Make the debt visible without making autoclose destructive: after a sweep,
report the closed tickets that still have a `worktree:` or `branch:` recorded,
with the exact `coga retire <slug>` command for each. Two surfaces to cover:

- the recipe's stdout / blackboard report (`## Dream Skill:`-style section when
  run under a task);
- the per-ticket Slack line, or one trailing summary line for the sweep — a
  decision to make in design, since the existing `🎉 ... merged` line is
  per-ticket and a retire hint per row may be noisy.

Explicitly out of scope: autoclose deleting anything. It should stay a
lifecycle sweep; duplicating retire's safety proofs (same-repo linked worktree,
no other live ticket sharing it, no open PR for the head, branch landed or
equal to the recorded merged head, tracked/untracked/ignored files preserved)
would either copy that machinery or ship a weaker version of it, and implicit
destruction cuts against the principle that destructive behavior is never
implicit.

## Context

Found while auditing seven leftover worktrees under `~/Code/claude/` on
2026-08-14. `coga run autoclose` closed five tickets in one pass; three of the
worktrees on disk belonged to tickets that had already been closed and deleted,
with no trace left of which command should have cleaned them up.

Related but separate: `coga retire` refuses worktree removal when the checkout
holds ignored files, and every dev worktree accumulates `.pytest_cache/` and
`__pycache__/` from the workflow's own test runs — so retire's cleanup half
currently no-ops on nearly every real code ticket. That is its own ticket, not
this one.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
