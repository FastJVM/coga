---
name: trim-log/run
description: One-step deterministic audit retention maintenance.
steps:
  - name: trim
    skills: []
    assignee: agent
---

## trim

The reserved script runs the installed audit-retention job, reports the result,
and closes the period through `python -m coga.cli bump`. An incomplete or
uncertain transaction exits nonzero and retains recovery evidence.
