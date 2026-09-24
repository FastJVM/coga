---
title: 'Record the attended ticket-switch recipe: launch, do not mark active'
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

Dream 2026-W39, Phase 2 gap G4. Two attended sessions (native-runtime/1-debug-and-platform-failure-contract, section 'Handoff requires a task launch — 2026-09-16', and native-runtime/2-macos-arm64-runtime-readiness, 'Pending design handoff — 2026-09-17') hit the same dead end after the owner redirected the session to a prerequisite ticket: the agent ran coga mark active <slug>, authored the full step, then coga bump refused (Task is 'active'. Cannot advance.) because bump requires in_progress and only coga launch performs the start transition. One session burned a block/unblock cycle purely for this. CLAUDE.md only says mark active activates a draft without launching it; no context carries the recipe. Deliverable: a short section in coga/contexts/coga/recipes/SKILL.md ('Switching an attended session to another ticket'): have the owner run coga launch <slug> from their own terminal before the agent does the step's work; do not mark active and author first; if work was already done under active, record a handoff note and ask for the launch — the next launched session verifies the note and bumps once. Coordinate with Dream PR #104, which edits the same context.

## Context

<!-- coga:blackboard -->

## Production notes

Moved from FastJVM/multiply on 2026-09-24: filed there by Dream/autofix against coga itself (status there was `draft`; canceled in multiply as moved). Reset to `draft` for re-triage here. Paths, branches, worktrees and ticket slugs in the notes below refer to the multiply repo unless they say otherwise.


The blackboard is a notepad to be written to often as the human and agent works through a task.
