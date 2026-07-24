---
name: skill-update/run
description: One-step lifecycle for the skill-update recurring recipe.
steps:
  - name: update
    skills:
      - bootstrap/skill-update
    assignee: agent
---

## update

Recipe-backed recurring task. `coga recurring` runs `coga run skill-update`,
which calls `coga skill update --all --pr --json`: every clean imported-skill update lands
in one draft PR on the dedicated `coga/skill-update` branch, and the result —
updated, follow-up, and skipped skills bucketed by raw status — is appended to
the task blackboard under `## Skill Update`. When no imported skill changed, no
PR is opened. When a run has human-needed follow-up and no PR artifact to carry
it, the recipe exits non-zero after writing the report so the period task is not
silently marked done.
