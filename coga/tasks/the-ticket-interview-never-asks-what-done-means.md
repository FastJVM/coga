---
slug: the-ticket-interview-never-asks-what-done-means
title: The ticket interview never asks what done means
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

Nothing in the authoring interview asks the filer what would count as done. The greeting is "What
should it do, and why? I'll turn your answer into the ticket", and the question list runs
Description / Context / Workflow — no acceptance criteria.

Two tickets have asked for this independently. Decide whether `bootstrap/ticket` should ask, and
whether the answer lands as an `## Acceptance Criteria` section the validator can check.

## Context

Found by Dream 2026-08-24, Phase 2 knowledge scan (shard-12), classified `gap`. Target is
`coga/.agent-skills/bootstrap/ticket/SKILL.md` and its packaged source (identical pair).

Related parked draft: `v2/acceptance-criteria`. Check its premise and fold it in.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
