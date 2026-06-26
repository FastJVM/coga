---
name: dream/validate-drift
description: One-step script workflow that runs the Dream validate-drift skill against the repo.
steps:
  - name: run
    skills:
      - bootstrap/dream/tasks/validate-drift
    assignee: agent
---

## run

Script step. Runs `bootstrap/dream/tasks/validate-drift`, which executes the
deterministic `relay validate` surface, applies the conservative safe-repair
pass, classifies any drift, and appends `## Dream Skill: validate-drift` to
this task's blackboard.
