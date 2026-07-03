---
schedule: "0 9 * * 1"
schedule_comment: "Every Monday at 9am — update clean imported skills into one reviewable PR"
title: "Skill update"
# A script step runs the updater directly with no agent: the workflow's one
# step references the `bootstrap/skill-update` skill, whose `script:` runs
# `coga skill update --all --pr`. No `claude -p` / `codex exec` buffering, so
# it is safe under the temporary mode=auto recurring freeze.
mode: script
workflow: skill-update/run
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

<!-- coga:blackboard -->

This blackboard persists across every run of this recurring task. Each period
task gets its own blackboard; the `bootstrap/skill-update` script appends its
`## Skill Update` report there, not here. This template keeps no durable state
— every run's output is the skill-update PR and the period task's report.

last_serviced_period: 2026-W27
