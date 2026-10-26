---
name: autoclose-merged/sweep
description: One-step lifecycle for the autoclose recurring task's deterministic half.
steps:
  - name: sweep
    skills:
      - coga/autoclose/sweep
    assignee: agent
---

## sweep

Script-backed recurring task. The period task's reserved `ticket.py` runs the
registered autoclose recipe to close merged final-step tickets and dispose of
recorded feature checkouts under the shared retire proofs. Refused checkouts
remain visible with their reasons and manual remedies, and the recurring
worklist preserves follow-ups across period-task deletion. After autoclose
succeeds, the script bumps. Unclaimed landed branches are swept per clone by
the `scope: clone` branch-sweep template; see
[recurring scheduling](context:coga/recurring/scheduling).

The `coga/autoclose/sweep` skill
owns the closure, disposal, reporting, and worklist rules.

## No other-agent code review

This is the one-step lifecycle of a recurring task's deterministic
half. It produces no code, so no `other-agent` step reviews it.
