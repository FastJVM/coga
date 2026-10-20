---
title: Retire canceled tickets without Retro
status: canceled
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
---

## Description

Owner decision (2026-10-14), revising #1014: `coga retire` deletes canceled tickets deterministically, exactly like done tickets (checkout disposal, worklist discharge, `coga delete` removal and sync), with no Retro agent. Why: most cancellations (superseded, duplicate, no longer wanted) carry nothing to learn, and the `coga mark canceled --message` reason already persists in coga/log.md. When a ticket is canceled because an approach did not work, the lesson belongs in the topic that owns the subject, written at cancel time; that is the existing coga/knowledge rule that an owner decision not to act is owned by the topic that owns X, never the ticket. A new failed status and an opt-in --retro flag were considered and rejected: a status touches every status consumer, and a flag is more mechanism than the problem needs. Scope: remove the canceled-ticket Retro path that #1014 added to src/coga/commands/retire.py and src/coga/resources/retire.md (drop retire.md and the retire-<slug> task scaffold if nothing else uses them), the retro/done-ticket skill, the Dream template (live and packaged) Phase 4 and Phase 6 canceled routing, bootstrap/dream/scan/knowledge-scan, and the coga/lifecycle, dev/checkout-cleanup (and its leaves), coga/recurring/dream/ticket.md and coga/tickets/discovery wording. Add one sentence to coga/lifecycle near `mark canceled` pointing failure lessons at the owning topic. Keep live and packaged twins byte-identical, and update tests/test_retire.py and the Dream template tests. Done means: retire handles done and canceled the same way with no agent, no prompt or topic still promises Retro for canceled tickets, and the full suite and coga validate pass.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
