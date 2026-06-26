---
name: skill-update/run
description: One-step script workflow that updates clean imported Coga-managed skills into one reviewable PR.
steps:
  - name: update
    skills:
      - bootstrap/skill-update
    assignee: agent
---

## update

Script step. Runs `bootstrap/skill-update`, which calls
`coga skill update --all --pr --json`: every clean imported-skill update lands
in one draft PR on the dedicated `coga/skill-update` branch, and the result —
updated, follow-up, and skipped skills bucketed by raw status — is appended to
the task blackboard under `## Skill Update`. When no imported skill changed, no
PR is opened. When a run has human-needed follow-up and no PR artifact to carry
it, the script exits non-zero after writing the report so the period task is not
silently marked done.
