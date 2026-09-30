---
title: Record that contexts linking tickets by path break at retirement after PR 918
  lands
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
step: 2 (peer-review)
agent: claude
---

## Description

Filed by Dream 2026-W40, Phase 6 (proposal-ownership overlap). Extract from the canceled ticket `phase-0-audit-is-complete-per-the-plan-but-still-i` (Dream shard ks-17, class extract, source: canceled, area coga/knowledge): Retro (`retro/done-ticket`) and `coga delete` delete a reaped ticket without repairing inbound links, so a context that names a ticket by path as the owner of an open question dangles once that ticket retires (observed: `marketing/plan` and `marketing/map` pointing at a reconciliation ticket; the same shape recurs this run in the fix-installer links). The durable rule: point durable surfaces at the question's standing owner rather than at a transient ticket, and grep for inbound references to a slug before it retires. Target `docs/contexts/coga/knowledge/SKILL.md` (and packaged twin). Open PR #918 (branch `preserve-no-action-decisions`) edits that topic without carrying this fact; add it after #918 merges or closes, in the same voice. The canceled source ticket stays on disk until this lands. Verify with `python -m pytest tests/test_packaging.py`.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: knowledge-ticket-links-at-retirement

Plan: PR #918 merged 2026-09-29 (commit 1ec281c9b), so the precondition holds.
Add a short paragraph to `docs/contexts/coga/knowledge/SKILL.md` right after
#918's no-action-decision paragraph (same voice, same "lifecycle retires
tickets" argument): durable surfaces cite the question's standing owner, not a
ticket path; grep for inbound references to a slug before it retires. Mirror
into the packaged bootstrap twin.

## Handoff (implement)

- Commit on `knowledge-ticket-links-at-retirement` (pushed): one new paragraph in
  `docs/contexts/coga/knowledge/SKILL.md` under "Where knowledge lives",
  directly after #918's no-action-decision paragraph, reusing its "lifecycle
  retires tickets" argument. Packaged twin
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/knowledge/SKILL.md`
  copied byte-identical.
- Wording choice: "standing owner (a topic, or the role that decides it)" —
  the ticket named no alternative owner kind; kept it to those two.
- Did not repair the observed dangling links (`marketing/plan`,
  `marketing/map`, fix-installer) — out of scope; the ticket asks only for the
  rule.
- Verified: `.venv/bin/python -m pytest tests/test_packaging.py` (23 passed)
  and full `.venv/bin/python -m pytest` (3135 passed). Note: bare `python`
  lacks `tomlkit`; use the repo `.venv`.
- After this lands, the canceled source ticket
  `phase-0-audit-is-complete-per-the-plan-but-still-i` can be reaped.
