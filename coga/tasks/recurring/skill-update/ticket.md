---
slug: recurring/skill-update
title: Skill update
status: active
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- coga/period-task
skills: []
workflow:
  name: skill-update/run
  steps:
  - name: update
    skills:
    - bootstrap/skill-update
    assignee: agent
secrets: null
script: null
step: 1 (update)
---

## Description

Update every clean imported (Coga-managed) skill in one reviewable PR.

Imported skills live as plain directories under `coga/skills/` with
`.coga-source.json` provenance. Once a week this ticket fires on its schedule
and its script step runs `coga skill update --all --pr`, which:

1. walks every imported skill with recorded provenance,
2. rewrites in place each skill whose upstream digest changed and whose local
   copy is unmodified,
3. commits the clean updates onto the dedicated `coga/skill-update` branch
   and opens (or updates) one draft PR, and
4. appends a `## Skill Update` report to this period task's blackboard,
   bucketing every skill by raw update status.

Local adaptations are never overwritten: a skill whose local copy diverged, a
provenance conflict, or a fetch failure is left untouched and listed under the
report's follow-up heading for a human to resolve. Bundled (package-backed)
skills are not touched here — they refresh when the coga package is upgraded.

A week with no upstream changes is a quiet no-op: nothing is committed and no
PR is opened. A week with only follow-up statuses is intentionally loud: after
writing the `## Skill Update` report, the script exits non-zero so this period
task remains visible until a human resolves or parks it.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
