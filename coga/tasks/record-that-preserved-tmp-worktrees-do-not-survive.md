---
title: Record that preserved tmp worktrees do not survive; only the branch does
status: draft
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
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
step: 1 (implement)
---

## Description

Dream 2026-W39, Phase 2 gap G7. Work 'deliberately preserved' in a /tmp worktree is gone by the time anyone acts on it, while the local branch silently keeps the only copy. Evidence: autofix/make-dream-block-instead-of-done-when-its-retro-ch — Dream W36 preserved /tmp/dream-retro-2026-W36 plus branch dream/retro-2026-W36-1788212557; the directory and its worktree registration are gone today, but git log main..dream/retro-2026-W36-1788212557 still shows the two unlanded coga/log.md commits (d420b30, 3e4c60a), so the ticket's cleanup recipe is half-impossible and the branch is the sole copy. autofix/persist-autoclose-retire-follow-ups-beyond-the-per: 11 terminal tickets carry stale worktree lines pointing at gone directories. coga/recurring/autoclose-merged/ticket.md lists four auto-closed tickets whose /tmp ex-worktrees are gone while their branches survive in another clone, and retires.md's discharge rule then drops them as if retired. The Dream template itself put the retro clone under /tmp until this run (W39 used a sibling path). Deliverable: a short section in coga/contexts/coga/recipes/SKILL.md stating that /tmp worktrees are ephemeral on this machine; anything preserved 'for durability' must be pushed or cherry-picked onto main before the run ends; a gone worktree leaves a prune-able registration and a branch that still holds the commits; recovery is git log main..<branch>, cherry-pick/push from the primary checkout, then git branch -D. The active make-dream-block ticket's item 3 covers Dream's audit-line single point of failure; this ticket is the durable context note it does not cover. Coordinate with Dream PR #104, which edits the same context.

## Context

<!-- coga:blackboard -->

## Production notes

Moved from FastJVM/multiply on 2026-09-24: filed there by Dream/autofix against coga itself (status there was `draft`; canceled in multiply as moved). Reset to `draft` for re-triage here. Paths, branches, worktrees and ticket slugs in the notes below refer to the multiply repo unless they say otherwise.


The blackboard is a notepad to be written to often as the human and agent works through a task.
