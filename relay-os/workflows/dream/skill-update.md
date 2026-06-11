---
name: dream/skill-update
description: One-step script workflow that runs the Dream skill-update skill against the repo.
steps:
  - name: run
    skills:
      - bootstrap/dream/tasks/skill-update
    assignee: agent
---

## run

Script step. Runs `bootstrap/dream/tasks/skill-update`, which runs
`relay skill update --all --pr` so every clean imported-skill update lands in
one draft PR on the dedicated `relay/skill-update` branch, reports conflicting
or skipped skills as follow-up work, and appends `## Dream Skill: skill-update`
to this task's blackboard.
