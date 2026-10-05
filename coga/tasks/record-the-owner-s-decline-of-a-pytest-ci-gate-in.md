---
title: Record the owner's decline of a pytest CI gate in the testing topic's CI posture
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

Filed by Dream 2026-W41, Phase 6 (knowledge scan, shard ks-17, class extract, source: canceled ticket nothing-exercises-python-3-11-the-declared-floor). Target: docs/contexts/coga/testing/SKILL.md (CI posture) and its packaged twin. Filed as a draft instead of a proposal PR because open PR #950 (https://github.com/FastJVM/coga/pull/950) edits the packaged coga/testing twin and does not carry this finding; apply after #950 lands or rebase onto it. The canceled source ticket stays on disk as evidence.

The canceled ticket records an owner decision not to act (2026-09-24): test verification is a Coga workflow property (the implement / self-qa / review steps), not a GitHub Actions gate, so PR #894 adding a Python 3.11/3.12 pytest matrix (`.github/workflows/tests.yml`) was closed unmerged; the port survives as commit 58630a20f. `docs/contexts/coga/testing/SKILL.md` "CI posture and receipts" still describes the absence of a test workflow only as a current fact and says the parked `coga/tasks/_v2/minimal-ci-run-pytest-on-prs-and-tags.md` "would change this; update this section when it lands" — it does not state that adding test CI was considered and declined, why, or that the declared 3.11 floor is therefore verified by workflow steps on a real 3.11 interpreter rather than by CI. Add one short paragraph to that section (and its packaged twin, if one exists) naming the decline, its reason, the surviving commit, and that reopening it is an owner decision (the ticket's alternative was raising `requires-python`). The 3.11 MultiplexedPath gotcha itself is already in `coga/codebase/gotchas`.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
