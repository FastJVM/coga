---
slug: no-skill-exists-for-the-cold-evaluator-review-of-a
title: No skill exists for the cold evaluator review of a design spec
status: active
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

Several tickets carry an `## Evaluator review` section: a deliberately cold reading of a design
spec by an agent with no prior context, used to catch assumptions the author could not see. It is a
repeated, valuable ritual with no skill behind it, so each run improvises the rubric.

Write it as `coga/skills/code/review-design/SKILL.md`, or decide it belongs as a step in the
`code/design-then-implement` workflow.

## Context

Found by Dream 2026-08-24, Phase 2 knowledge scan (shard-05), classified `gap`.

Note the interaction with Phase 1: `coga validate` flags `## Evaluator review` as an
`unsynthesized-draft-blackboard` authoring section on three `v2/` drafts. If this ritual becomes a
skill, the validator needs to know the section is legitimate — otherwise formalizing it makes
validate noisier, not quieter.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
