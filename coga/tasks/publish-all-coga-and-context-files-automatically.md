---
title: Publish all Coga and context files automatically
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

Replace the narrow tasks/log/recurring automatic publication scope with one directory rule: publish eligible changes anywhere under the configured Coga workspace and the configured contexts directory. The owner explicitly approved this on 2026-10-07 while discussing PR #973: contexts, skills, workflows, shared config and other files in those directories should be committed through normal Coga state publication, without requiring a separate knowledge PR. In this repository the roots are coga/ and docs/contexts/; resolve configured paths rather than hard-coding these spellings. Retain Git ignore behavior and existing publication safeguards. Packaged copies under src/ remain ordinary reviewed source changes. Apply the same roots consistently to the sweep, authoring finalization, checkout preparation/return, state-only commit recovery and any unpublished-edit warning. Update the owning contracts, instructions, fixtures and packaged twins together, removing the obsolete knowledge-only PR requirement for files inside these roots.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
