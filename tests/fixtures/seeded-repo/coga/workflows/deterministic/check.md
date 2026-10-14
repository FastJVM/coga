---
name: deterministic/check
description: One-step workflow for the seeded deterministic ticket example.
steps:
  - name: execute
    assignee: agent
---

## execute

Run the ticket's reserved `ticket.py` entry point. It records its result on the
blackboard and completes this final step itself.
