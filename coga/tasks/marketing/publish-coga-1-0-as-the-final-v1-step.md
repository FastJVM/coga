---
title: Publish coga 1.0 as the final V1 step
status: draft
owner: nicktoper
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: owner
  - name: report-to-coga
    skills: []
    assignee: agent
step: 1 (agent-produces)
---

## Description

Prepare and publish coga 1.0.0 to PyPI as the final V1 product-delivery step, after all remaining V1 changes and readiness checks are complete and before the public V1 launch. The 0.4.0 release published on 2026-10-02 is an interim release, not the final V1 release. Prepare a tested release candidate and release notes for owner approval, publish through the existing Trusted Publishing workflow when authorized, then verify the public package and record the release evidence.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
