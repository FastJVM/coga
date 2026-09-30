---
title: Autoclose re-posts another clone's primary checkout forever
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
launch_generation: 76f05ecc-195d-4764-b277-3a2ee053ba9a
---

## Description

Filed by Dream 2026-W40, Phase 6, routing the unresolved adjacent bug that Dream's Phase 4 Retro preserved in knowledge PR #920 ("New context: another clone's primary checkout never leaves the autoclose worklist", target `docs/contexts/dev/checkout-cleanup/SKILL.md`), from the done tickets `clean-up-all-the-working-trees` and `recurring/autoclose-merged`. Six autoclose `retires.md` entries record `/home/n/Code/coga` or `/home/n/Code/codex/coga` as their worktree; both are live primary checkouts of separate FastJVM/coga clones. The sweeping clone classifies them `standalone`, so they never discharge and are re-posted to coga-important on every run, and the `autoclose.py` remedy tells a human to "inspect and remove it by hand", i.e. delete an actively used clone. `is_primary_checkout` exempts only this repo's own primary, and `worktree_owner` records no owner for standalone clones. Fix so another clone's primary checkout is recognized (and discharged or reported without a delete remedy), then update the known-failure-mode text PR #920 adds. No open ticket owns this.

## Context

<!-- coga:blackboard -->

## Dev
branch: fix-autoclose-clone-primary

## Implementation plan

Recognize independent Git primary checkouts as preserved repositories, retain
branch ownership in their own clone, and discharge the worklist once that
branch is gone. Do not infer disposability from a path or advise deleting a
primary checkout. Cover legacy ownerless entries and newly closed tickets;
update the cleanup contract and packaged twins.
