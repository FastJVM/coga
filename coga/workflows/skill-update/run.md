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
is opened. `ticket.py` exits non-zero in two different cases, and both write
the `## Skill Update` report first so the period task is not silently marked
done: exit 1 when a run has human-needed follow-up and no PR artifact to carry
it, and exit 2 when `coga skill update` itself failed or emitted output that
was not valid JSON — that report carries a `### Failed` block with the command
and its stderr in place of the per-skill buckets.
