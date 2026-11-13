---
name: trial/skilled
description: Skill-owned output followed by owner judgment.
steps:
  - name: write
    skills:
      - trial/write
    assignee: agent
  - name: judge
    assignee: owner
---

## write

Dormant inline prose for a skilled step: write `WRONG-INLINE` instead.
This text must not compose when the step has skills.

## judge

The owner judges the result.
