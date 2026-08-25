---
slug: no-comms-writing-skill-the-process-is-smeared-thro
title: No comms-writing skill; the process is smeared through marketing plan
status: draft
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

There is no skill for writing a Coga post. The actual process — audience, structure, claim
discipline, the review pass — is smeared through `coga/contexts/marketing/plan/SKILL.md` and
`marketing/positioning`, mixed in with plan status and scheduling. A context should carry posture;
a skill should carry procedure.

Extract the procedure into `coga/skills/marketing/write-post/SKILL.md`.

## Context

Found by Dream 2026-08-24, Phase 2 knowledge scan (shard-07), classified `gap`.

Sequence after the marketing proposal PR from this run's Phase 6, which fixes five stale claims in
those same two contexts — including a claim-discipline rule pointing at a "5x" figure that has
never existed in `docs/vision.md`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
