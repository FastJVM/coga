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
is opened. `ticket.py` exits 1 when a run has human-needed follow-up and no PR
artifact to carry it, and 2 when `coga skill update` itself failed or emitted
output that was not valid JSON — the exit-2 report carries a `### Failed` block
with the attempted command and its failing output (stderr, or stdout, or the
JSON decode error) in place of the per-skill buckets. Both paths write the
`## Skill Update` report first, best-effort, so the period task is not silently
marked done. `ticket.py` also returns `coga bump`'s exit code once the update
succeeds, and that is 2 on most of its own refusals: an exit 2 carrying
per-skill buckets and no `### Failed` block is a failed bump, not a failed
update.
