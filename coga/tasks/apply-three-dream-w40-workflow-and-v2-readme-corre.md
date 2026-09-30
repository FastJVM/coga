---
title: Apply three Dream W40 workflow and v2 README corrections after PR 912 lands
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
launch_generation: pending:3ea18fa6-019c-4fba-b89f-7db0812eee67
---

## Description

Filed by Dream 2026-W40, Phase 6 (proposal-ownership overlap). These stale findings target files that open PR #912 (branch `docs/v2-batch-verdicts`, "Add an Applying-a-batch-of-verdicts section to the v2 parking README") also edits, and #912 does not carry them. Apply after #912 merges or closes; keep live/packaged twins byte-identical.

1. `docs/contexts/coga/workflows/SKILL.md` "Step completion gates" (Dream shard ks-18, class stale): the `branch` gate is described as needing `branch:` **and** `worktree:` under `## Dev`, but `src/coga/step_gate.py::_has_branch_linkage` checks only a usable `branch:` (`worktree:` is recorded only for the sandbox-clone fallback). Change the bullet accordingly.
2. Same file, opening paragraph (shards ks-32, ca-03, class stale/drift): "Packaged workflows are the `code/*` loop and `docs/*`; `direct/body` ... is seeded by `coga init`." The packaged `bootstrap/workflows/` also ships `brief-for-human` and `draft-for-human`, and the init scaffold `src/coga/resources/templates/coga/workflows/` also seeds `_template`, `build/onboarding` and the recurring-job workflows. Reword (or point at the two directories instead of enumerating).
3. `coga/tasks/v2/README.md` "Title-only drafts: a capture, not a ticket" (shard ks-05, class stale): the README says the first sweep reporting a v2 stub's `empty-description` is its expiry and cites `interview-the-owner-on-the-17-title-only-v2-stubs` as batch precedent. That ticket was canceled 2026-09-20 without applying verdicts, and `coga/roadmap` "Direction change, 2026-09-20: park v2 out of reach" records v2 title-only warnings as the accepted baseline (`validate-drift: empty-description`). Scope the expiry rule to title-only tickets outside `v2/` and replace the precedent sentence.

Verification: `python -m pytest tests/test_packaging.py`.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
