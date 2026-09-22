---
name: upstream-coga/run
description: One-step lifecycle for the upstream-coga recurring task's deterministic half.
steps:
  - name: sweep
    skills: []
    assignee: agent
---

## sweep

Script-backed recurring task. `coga launch` runs the period task's reserved
`ticket.py`, which reads each configured client checkout's
`coga/upstream-coga.md`, files one draft ticket here per entry past that
checkout's cursor, and advances the cursor on the template's blackboard.
