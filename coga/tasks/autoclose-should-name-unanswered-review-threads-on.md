---
title: Autoclose should name unanswered review threads on the PR it closes
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

Follow-up from verify-the-pr-review-comment-loop-once-the-review (phase 4 decision, 2026-09-13). Between 2026-08-17 and 2026-09-13, 7 of 38 merged PRs (696, 699, 704, 705, 706, 747, 755) carried a bot review thread that was not outdated, got no reply, and had no code change before merge. Every review step froze code/address-pr-comments correctly, so the miss is not the frozen-snapshot bug (#698); it is that nothing surfaces an unanswered thread to the owner, who merges from the GitHub UI where unresolved threads do not block, and the on-demand assist was invoked once in four weeks. Decision: keep the owner gate (merge and thread resolution stay human) and add post-merge detection, not prevention. When the autoclose sweep closes a ticket on a merged PR, fetch the PR's reviewThreads once and, for each thread that is unresolved, not outdated, and has only its opening comment, name it in the sweep summary and Slack line the same way autoclose already names the retire follow-up - report only, never resolve or reply. Rationale: the sweep is the one place that already touches every merged PR, the signal lands in coga/log.md where it is legible, and no new poller or hidden state is added. Out of scope: resolving threads, blocking merges, or running an agent on the review step automatically.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
