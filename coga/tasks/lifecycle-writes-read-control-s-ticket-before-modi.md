---
title: Lifecycle writes read control's ticket before modifying it
status: in_progress
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (design)
agent: claude
---

## Description

coga bump, mark, block (and other lifecycle writers) edit the checkout's local ticket bytes and only compare against control at push time. When the local copy is stale — another clone advanced the ticket, the checkout is dirty or off main so refresh never catches it up, or a sandboxed session's own write was published by another process without recording provenance — the guard refuses with 'control copy changed since this checkout last saw it' or 'would move backward', and the human must hand-take control's copy and redo the edit. Counts on origin/main logs (2026-09): coga 97 sync refusals and 194 read-only publish failures; multiply 23 refusals and 42 read-only failures. Only launch, megalaunch and the recurring runner read control first today.

Proposed behavior: every lifecycle write fetches control and reads its copy of the ticket first. (1) Local copy only behind (no unpublished edits relative to this checkout's provenance): adopt control's copy, apply the transition to it, publish. (2) Both sides changed: three-way merge from the provenance base; frontmatter status/step conflicts resolve to the side further along using the existing ticket-regression ordering; a genuine body/blackboard conflict still refuses with the current remedy. (3) Fold in ticket-sync-fails-with-read-only-git-inside-agent: after a sandboxed session exits, the supervisor republishes the session's state and records provenance in the invoking checkout, so the next bump is not refused.

Acceptance: real-Git tests for stale clone adopting control; both-sides-changed merge with step conflict; body conflict still refuses without data loss; the 2026-09-27 multiply improve-banners sequence (sandboxed bump fails to publish, another process publishes it, then a human bump from the same checkout succeeds). Offline behavior unchanged: no fetch means today's guard. Update coga/internals/state-publication, git-regressions and coga/sync. Sequence before launch-moves-the-checkout-to-main-before-and-after, whose evaluator finding #2 depends on it.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
