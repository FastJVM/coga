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
worklist preserves follow-ups across period-task deletion.

The `coga/autoclose/sweep` skill
owns the closure, disposal, reporting, and worklist rules.
