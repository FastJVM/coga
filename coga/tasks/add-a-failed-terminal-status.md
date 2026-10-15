---
title: Add a failed terminal status
status: active
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

Owner decision (2026-10-14), revising #1014. A terminal ticket can end three ways, and they need different retirement: done (positive learning landed in the merged PR); canceled (superseded, duplicate or no longer wanted, so nothing to learn, and the --message reason persists in coga/log.md); and the new failed (an approach was tried and did not work, so there is negative learning to extract: what was tried, why it failed, what would reopen it). Add `failed` as a third terminal status, set with `coga mark failed --message <reason>` (reason required, as for canceled). Retirement: `coga retire` deletes done and canceled tickets deterministically with no agent (checkout disposal, worklist discharge, `coga delete` and sync), and runs the Retro task (retro/done-ticket through retire.md) only on failed tickets, extracting the lesson into the topic that owns the subject, per the coga/knowledge rule that a decision not to act is owned by the topic, not the ticket. Rejected alternatives: one canceled status with no Retro, since failure lessons would depend on remembering to write them; and a --retro flag on cancel, since an explicit status is clearer. Design step: inventory every consumer of the status set and of the literal 'canceled' (src/coga/lifecycle.py VALID_STATUSES, TERMINAL_STATUSES and CANCELABLE_STATUSES; mark, megalaunch, views/coga status, notifications and GIF kinds, git/state publication, recurring and recurring_runner, retire, autoclose and branch-sweep terminal-owner rules, validate, create), and decide for each whether failed behaves like canceled. Decide the notification emoji and GIF key, whether autoclose or recurring can ever produce failed, and how Dream Phase 4 and Phase 6 and bootstrap/dream/scan/knowledge-scan route failed versus canceled findings (#1014 routed canceled to Retro). Update coga/lifecycle (status table and terminal rules), coga/tickets/discovery, dev/checkout-cleanup and its terminal-owners leaf, coga/dream, coga/notifications and the cli index, with live and packaged twins byte-identical. Done means: three terminal statuses with distinct retirement as above, no prompt or topic still promising Retro for canceled tickets, tests covering mark failed and retire for each terminal status, and the full suite and coga validate passing.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
