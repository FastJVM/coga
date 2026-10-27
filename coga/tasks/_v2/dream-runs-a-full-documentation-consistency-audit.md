---
title: Dream runs a full documentation consistency audit once a month
status: draft
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (design)
---

## Description

Owner request (2026-10-14): once a month, Dream runs the full documentation consistency audit that a manual four-lens sweep did on 2026-10-14, which found about 30 inconsistencies that Dream's weekly knowledge scan and contract audit missed. Lenses: (1) README.md versus the topic library and the shipped base prompt, because README.md owns concepts and positioning; (2) topics, the seeded coga.toml and docstrings versus the code (CLI index, config keys, flags, paths); (3) consistency within the library (one-owner restatements, broken links and anchors, index and topic-map coverage, tickets cited as owners, size policy); (4) bundled skills, workflows, prompts and docs/design and docs/evidence versus the topics. Proposed shape: a monthly-gated decide-half scan phase in the Dream template, running only on the first Dream period of each month, whose findings flow through Dream's existing disposition (PR, draft ticket or marker). It should also lift the known corpus limitation that both scans exclude bootstrap/skills/**. Done means the Dream template (including its phase list), its packaged twin and tests are updated, and one forced run produces findings on this repo.

## Context

Previous ref: `dream-runs-a-full-documentation-consistency-audit` (renamed 2026-10-27); earlier audit lines retain that ref. Parked by the owner for v2; this work does not gate v1.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
