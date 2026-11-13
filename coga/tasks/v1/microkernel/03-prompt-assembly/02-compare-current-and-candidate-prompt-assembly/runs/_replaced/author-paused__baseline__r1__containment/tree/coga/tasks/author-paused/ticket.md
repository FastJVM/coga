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

Preserve the existing intent: write the agreed result after the owner resumes execution. Verify the output before handoff.

## Context

Use only the isolated trial repository. Before execution resumes, the owner must specify the agreed output value. The workflow writes it to sibling `result.txt` and reads it back; the reporting skill records the path and observed content.

<!-- coga:blackboard -->

## Notes

Keep this unrelated owner note.
