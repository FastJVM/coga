---
slug: carry-adjacent-bugs-out-of-a-blackboard-before-ret
title: Carry adjacent bugs out of a blackboard before Retro deletes it
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
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
secrets: null
step: 1 (implement)
---

## Description

`coga/skills/code/implement/SKILL.md` instructs: "If you find a real adjacent bug, write it on the
blackboard for a follow-up ticket; don't fix it here." Nothing downstream is required to carry that
note out. Dream Phase 4 then deletes done tickets — with their blackboards — so an adjacent bug
parked this way is destroyed unless a human happened to read it first.

Either `code/implement` must require filing the follow-up ticket before bump, or
`retro/done-ticket` must treat parked adjacent bugs as durable knowledge. Decide which.

## Context

Found by Dream 2026-08-24, Phase 2 knowledge scan (shard-11), classified `gap`. Verified live in
this repo.

Directly relevant to Dream itself: this run's Phase 4 deleted 8 done tickets. The risk is not
hypothetical.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
