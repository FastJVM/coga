---
title: Ticket ownership lock
status: draft
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
contexts:
  - coga/launch
  - coga/tickets
  - coga/internals/launch-claims
  - coga/internals/claim-recovery
  - coga/internals/state-publication
  - coga/internals/git-regressions
  - coga/recurring/scheduling
---

## Description

Design an independent per-ticket ownership lock that prevents concurrent launches of the same ticket across checkouts and machines. User direction: keep an inspectable lock file beside the ticket while a launch works on it, remove the claim when the launch finishes, and include metadata for garbage collection and safe crash/restart recovery. This deliberately revises the current no-task-ownership-lock contract.

Define placement for both directory-form and bare .md tickets without introducing duplicate task discovery. If the lock is shared through Git, acquisition must atomically claim absence on control and confirm publication before spawning; creating a local file alone cannot exclude another clone. Specify owner/session UUID, machine identity, process identity including a start marker, checkout path, and start time. Explain what proves a worker dead, what remains uncertain on another machine, and how restart adopts or replaces a stale claim without admitting two workers. A reused PID or matching owner is insufficient.

Hold ownership across script and agent phases, workflow bumps and chained steps, through final publication and release. Done means launch/session completion, including interrupted or refused teardown, not only terminal ticket status; preserve unpublished work during recovery. Define ambiguous acquire/release publication outcomes, compare-and-set removal of the exact claim, stale-session write rejection, and interaction with existing launch_generation and megalaunch claims. Do not promise protection against arbitrary external side effects or manual Git writes.

Evaluate a daily recurring collector for stale claims; never clear a potentially live worker solely because the claim is old. Immediate restart recovery must not depend on a daily job. Define local-only behavior when Git sync is unavailable.

Orthogonal sibling: launch-locks/checkout-exclusivity-lock protects a physical checkout, not ticket identity. This ticket must stand alone and permit different tickets in separate clones. Describe a shared acquisition order when both ship. Include concurrency/crash acceptance scenarios and update owning contracts and packaged twins in the eventual implementation PR. The design requires owner approval before code.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
