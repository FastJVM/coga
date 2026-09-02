---
schedule: "0 9 * * 1"
schedule_comment: "Every Monday at 9am — update clean imported skills into one reviewable PR"
title: "Skill update"
# The reserved `ticket.py` sibling is this task's deterministic half: `coga
# launch` runs it directly, with no agent and no composed prompt. The one-step
# workflow keeps the period task's lifecycle and skill contract legible.
workflow: skill-update/run
---

## Description

Update every clean imported (Coga-managed) skill in one reviewable PR.

Imported skills live as plain directories under `coga/skills/`. No skill
currently carries a `.coga-source.json` file: Coga writes that provenance only
for URL-installed skills, and none are installed. The GitHub-backed skills — the
seven `google-agents-cli-*` refs declared in `managed-skills.toml` — are tracked
by `gh skill`'s own metadata instead, and the two vendored packs
(`anthropic/skill-creator`, `browser/playwright`) carry hand-written attribution
and report as unmanaged. Once a week this ticket fires on its schedule and its
`ticket.py` runs `coga skill update --all --pr`, which:

1. delegates every GitHub-backed skill to a single `gh skill update --dir
   coga/skills --all`, then walks in Coga's own code only those skills that do
   carry `.coga-source.json` with `source_type = "url"` — today an empty set,
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
writing the `## Skill Update` report, `ticket.py` exits non-zero so this period
task remains visible until a human resolves or parks it.

<!-- coga:blackboard -->

This blackboard persists across every run of this recurring task. Each period
task gets its own blackboard; the `skill-update` run appends its
`## Skill Update` report there, not here. This template keeps no durable state
— every run's output is the skill-update PR and the period task's report.
