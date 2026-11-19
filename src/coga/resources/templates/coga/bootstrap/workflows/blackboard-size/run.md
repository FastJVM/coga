---
name: blackboard-size/run
description: One-step lifecycle for the blackboard-size recurring task's deterministic report.
steps:
  - name: report
    skills: []
    assignee: agent
---

## report

Script-backed recurring task. `coga launch` runs the period task's reserved
`ticket.py`, which reports the `large-blackboard` findings of
`coga validate --json` (ref, measured size, threshold) and closes the period
through `python -m coga.cli bump`. The report is informational; the
[blackboard-size template](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/recurring/blackboard-size/ticket.md)
owns its contract.

## No other-agent code review

This is the one-step lifecycle of a recurring task's deterministic half. It
reads the repo and changes nothing, so no `other-agent` step reviews it.
