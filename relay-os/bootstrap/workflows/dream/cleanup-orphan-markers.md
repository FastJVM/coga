---
name: dream/cleanup-orphan-markers
description: One-step script workflow that runs the Dream cleanup-orphan-markers skill against the repo.
steps:
  - name: run
    skills:
      - bootstrap/dream/tasks/cleanup-orphan-markers
    assignee: agent
---

## run

Script step. Runs `bootstrap/dream/tasks/cleanup-orphan-markers`, which detects
done tickets carrying a processed Retro marker whose task directory survived
cleanup, gates deletion through `bootstrap/delete-task`, and appends
`## Dream Skill: cleanup-orphan-markers` to this task's blackboard.
