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

## No other-agent code review

This workflow runs reviewed, installed maintenance code and changes retained
state. It does not author code or a PR. Changes to the implementation use the
repository's code-review workflow before the compatible wheel is installed.
