---
title: Retire deletes done tickets without a retro; canceled tickets get one
status: in_progress
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
agent: claude
launch_generation: f965fa2b-45a7-4d59-bc13-c9773e73fb9e
---

## Description

Owner decision 2026-10-13. Done tickets pile up (136 done, 29 canceled): autoclose marks them done and deletes their branch but leaves the branch: line in ## Dev, and Dream's Phase 4 gate only checks that the line is present, so it skips every one (it reports 153 tickets of retirement debt each week). For 119 of them the recorded branch no longer exists. Only manual coga retire drains them, at one agent run per ticket; it has run 5 times ever. New rule: positive learning already landed in the merged PR (the sync rule updates the owning topic in the same PR), and negative learning lives in the ticket or blackboard, usually as the cancellation reason. So (1) coga retire on a done ticket disposes of its checkout and deletes the ticket deterministically, with no retro agent; (2) coga retire accepts canceled tickets and runs the retro on them to extract the cancellation reason and any other negative learning, then deletes; (3) the Dream retirement gate checks whether the recorded branch or worktree still exists (as retire_worklist already does) instead of whether the line is written; (4) update dev/checkout-cleanup, coga/dream and coga/lifecycle, plus packaged twins, in the same PR. Then drain the backlog: plain deletes for done tickets with no live branch, retire for the ~17 with a live branch, and retros for the canceled tickets.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
