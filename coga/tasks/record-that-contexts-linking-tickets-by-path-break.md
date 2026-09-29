---
title: Record that contexts linking tickets by path break at retirement after PR 918
  lands
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

Filed by Dream 2026-W40, Phase 6 (proposal-ownership overlap). Extract from the canceled ticket `phase-0-audit-is-complete-per-the-plan-but-still-i` (Dream shard ks-17, class extract, source: canceled, area coga/knowledge): Retro (`retro/done-ticket`) and `coga delete` delete a reaped ticket without repairing inbound links, so a context that names a ticket by path as the owner of an open question dangles once that ticket retires (observed: `marketing/plan` and `marketing/map` pointing at a reconciliation ticket; the same shape recurs this run in the fix-installer links). The durable rule: point durable surfaces at the question's standing owner rather than at a transient ticket, and grep for inbound references to a slug before it retires. Target `docs/contexts/coga/knowledge/SKILL.md` (and packaged twin). Open PR #918 (branch `preserve-no-action-decisions`) edits that topic without carrying this fact; add it after #918 merges or closes, in the same voice. The canceled source ticket stays on disk until this lands. Verify with `python -m pytest tests/test_packaging.py`.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
