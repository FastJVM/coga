---
name: bootstrap/dream/tasks/cleanup-orphan-markers
description: Find processed done tickets whose task directories survived Retro cleanup, then gate deletion through the public delete-task skill.
script: run.py
---

# Cleanup Orphan Markers

This Dream skill is the recovery path for done tickets whose blackboard already
contains the processed Retro marker from a knowledge PR but whose task
directory still exists. Normal Retro knowledge PRs delete the source task
directory in the same PR, so this skill should usually report no work.
No-durable-knowledge tickets are direct-deleted by the Phase 4 Retro pass and
never carry a marker, so they never reach this gate; for safety the gate still
excludes any `result: no-new-durable-knowledge` marker left behind by an older
run.

## Known Skill Contract

- Purpose: detect already-processed done tickets that are eligible for
  delete-only cleanup.
- Runs: a `mode: script` Relay task whose workflow step references
  `bootstrap/dream/tasks/cleanup-orphan-markers`.
- Inputs: task directories under `relay-os/tasks/`, the source task
  `blackboard.md` marker, GitHub open PR metadata when available, and the
  public `bootstrap/delete-task` skill.
- May change: none directly. Cleanup deletion must go through the public
  `bootstrap/delete-task` skill inside a reviewable cleanup PR worktree.
- Action: `pr-required`
- Idempotency: a source task is skipped when its directory is already gone, the
  marker is absent, the marker has `result: no-new-durable-knowledge`, the task
  is not exactly `status: done`, or an open PR is already touching
  `relay-os/tasks/<slug>/`.
- Stop and ask: `bootstrap/delete-task` is not installed, open PR state cannot
  be checked when deletion would otherwise proceed, or the task slug is not an
  exact directory name.
- Output: append `## Dream Skill: cleanup-orphan-markers` to the child task
  blackboard with `no-op` or `human-needed` details.

## Detection Gate

A task is a cleanup candidate only when all of these are true:

- `relay-os/tasks/<slug>/ticket.md` has exact `status: done`;
- `relay-os/tasks/<slug>/blackboard.md` has a `## Retro` block containing both
  `skill: retro/done-ticket` and `status: processed`;
- that Retro block does not contain `result: no-new-durable-knowledge`;
- `<slug>` is the exact task directory name, not a prefix match;
- no open PR is already touching `relay-os/tasks/<slug>/`;
- the public delete surface `bootstrap/delete-task` is available.

`bootstrap/delete-task` now ships, but until cleanup's PR-dispatch wiring
follows that skill's launch contract, this skill
reports eligible candidates as `human-needed` and does not delete anything.
