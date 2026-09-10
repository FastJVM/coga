---
name: direct/body
description: One-step workflow whose single step runs the ticket body directly as its spec. Used by machine-authored tasks (Dream/recurring, retire) whose process lives in the body rather than a multi-step workflow, so every task past `draft` still carries a workflow.
steps:
  - name: execute
    skills:
      - direct/body
    assignee: agent
---

## execute

Runs `direct/body`: the ticket body is the spec. Execute the phases it lays
out in order, honoring its own stop/skip rules, keep the blackboard current,
and finish with `coga mark done <slug>` (the body may specify its own
completion command — that command is the instruction). This is the only
step, so there is nothing to bump into.
