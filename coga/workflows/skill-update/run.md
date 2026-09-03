---
name: skill-update/run
description: One-step lifecycle for the skill-update recurring task's deterministic half.
steps:
  - name: update
    skills:
      - bootstrap/skill-update
    assignee: agent
---

## update

Script-backed recurring task. `coga launch` runs the period task's reserved
`ticket.py`, which calls `coga skill update --all --pr --json`: every clean
GitHub- or URL-backed update lands in one draft PR on the dedicated
`coga/skill-update` branch, and the emitted result — updated, follow-up, and
skipped statuses bucketed raw — is appended to the task blackboard under
`## Skill Update`. Local-backed and hand-vendored skills are unmanaged by this
run and currently emit no row. When no remotely managed skill changed, no PR
is opened. When a run has human-needed follow-up and no PR artifact to carry
it, `ticket.py` exits non-zero after writing the report so the period task is
not silently marked done.
