---
title: author-paused
status: paused
owner: trial-owner
agent: claude
contexts:
- trial/format
skills:
- trial/report
workflow:
  name: trial/inline
  steps:
  - name: write
    assignee: agent
  - name: judge
    assignee: owner
step: 1 (write)
---

## Description

Preserve the existing intent: write the agreed result after the owner resumes execution.

## Context

Use only the isolated trial repository.

<!-- coga:blackboard -->

## Notes

Keep this unrelated owner note.
