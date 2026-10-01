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
  - coga/internals/launch-claims
  - coga/internals/claim-recovery
  - coga/internals/state-publication
  - coga/internals/git-regressions
---

## Description

Design an independent per-ticket ownership lock that prevents concurrent launches of the same ticket across checkouts and machines. User direction: keep an inspectable lock file beside the ticket while a launch works on it, remove the claim when the launch finishes, and include metadata for garbage collection and safe crash/restart recovery. This deliberately revises the current no-task-ownership-lock contract.

Define placement for both directory-form and bare .md tickets without introducing duplicate task discovery. If the lock is shared through Git, acquisition must atomically claim absence on control and confirm publication before spawning; creating a local file alone cannot exclude another clone. Specify owner/session UUID, machine identity, process identity including a start marker, checkout path, and start time. Explain what proves a worker dead, what remains uncertain on another machine, and how restart adopts or replaces a stale claim without admitting two workers. A reused PID or matching owner is insufficient.

Hold ownership across script and agent phases, workflow bumps and chained steps, through final publication and release. Done means launch/session completion, including interrupted or refused teardown, not only terminal ticket status; preserve unpublished work during recovery. Define ambiguous acquire/release publication outcomes, compare-and-set removal of the exact claim, stale-session write rejection, and interaction with existing launch_generation and megalaunch claims. Do not promise protection against arbitrary external side effects or manual Git writes.

Evaluate a daily recurring collector for stale claims; never clear a potentially live worker solely because the claim is old. Immediate restart recovery must not depend on a daily job. Define local-only behavior when Git sync is unavailable.

Orthogonal sibling: launch-locks/checkout-exclusivity-lock protects a physical checkout, not ticket identity. This ticket must stand alone and permit different tickets in separate clones. When both ship, acquire the checkout lock first, then the ticket lock (the sibling already fixes this order); specify release order and how a refusal of either unwinds the other. Include concurrency/crash acceptance scenarios and update owning contracts and packaged twins in the eventual implementation PR. The design requires owner approval before code.

## Context

Owner priority: design and ship ticket ownership locking before checkout exclusivity; checkout collisions are considered uncommon. Keep the two deliverables independent.

The owner clarified "fast git sync" means immediate lock acquisition/release publication, not general state-sync performance work. Publish the claim immediately and confirm acquisition on control before work starts; publish removal immediately when the launch finishes. Do not depend on delayed sweeps. Failed or uncertain acquisition must not start work; failed release must remain visible for reconciliation. Fast publication alone is not mutual exclusion: simultaneous claims still require an atomic remote decision.

Contract being revised: `coga/launch` (`docs/contexts/coga/launch/SKILL.md`, "Status is the signal") currently says there is no task-ownership mutex and that megalaunch's claim and `git.state_lock` are not ownership locks. The implementation PR rewrites that paragraph and the related lines in `coga/internals/launch-claims` and `coga/internals/claim-recovery`.

Code anchors (cite by symbol; line numbers drift):

- `git.publish` with `expect={path: bytes | None}` (`None` = must not exist on control) and `guard=` is the existing atomic compare-and-set against control; the lock's acquire and exact-claim release should build on it rather than invent a new remote primitive.
- `git.ticket_regression_reason` holds the `pending:`/`released:` launch_generation seal rules; `launch._reconcile_released_launch_admission` is the existing released-witness recovery path. Define how the ownership lock composes with both.
- `git.state_lock` is the short-lived, per-checkout, reentrant `flock`; keep it separate and do not lengthen it.
- `git.fetch_control` and `git.sync_task_state` are the fetch and strict-publication helpers.
- `tasks.list_tasks` / `tasks.resolve_task` own discovery (see placement facts below).

Cited, not attached — `coga/tickets` (`docs/contexts/coga/tickets/SKILL.md`, "Where tasks live and how they are named"). Placement facts: `list_tasks` walks `coga/tasks/` at any depth; a directory holding `ticket.md` is a task and is never recursed into; a bare `<slug>.md` is a file-form task; `<slug>.md` and `<slug>/` must not both exist (`DuplicateTaskSlugError`); `README.md` is never a task and `_`-prefixed names are skipped at every level; attachments are never composed, and only the exact sibling `ticket.py` changes dispatch. Moving a task orphans its log history under the old ref.

Cited, not attached — `coga/recurring/scheduling` (`docs/contexts/coga/recurring/scheduling/SKILL.md`), for evaluating the daily collector. Facts: templates live under `coga/recurring/` and materialize one stable task per template under `tasks/recurring/`; a `ticket.py` period runs headless and is the shape for unattended schedulers, while agent periods need TTYs; a scheduled agent run must reach `done` in one launch or the sweep pauses it; repo-inactivity skips templates unless `run_when_inactive: true`; the shipped daily `autoclose-merged` template chains registered `coga run` recipes from its `ticket.py`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
