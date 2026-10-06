---
title: Dream's own blackboard trips large-blackboard every run
status: draft
owner: nicktoper
workflow: null
---

## Description

Found by validate-drift-blackboard-hygiene-two-oversized-bl on 2026-10-06. `coga validate --json` reports `large-blackboard` (warn, 51.5 KiB vs 32.0 KiB) for `recurring/dream` itself: the recurring template's blackboard holds the latest run's report, and its `## Findings` section alone was ~30 KiB for 2026-W41 (plus ~12.5 KiB `## Dream Skill: validate-drift` and ~8 KiB `## Dream Run Summary`). Dream's phase writers replace these sections on each firing, so hand-trimming would be overwritten next run and would interfere with Dream's own writers (coga/period-task: own only your keys). Because every run regenerates sections of this size, the warning will keep coming back, and Dream's own Phase 1 reports it about itself. Owner decision needed: have Dream write bulky per-run sections (Findings, validate-drift detail) to a sibling attachment under `coga/tasks/recurring/dream/` and keep only the summary and cross-run state on the blackboard; or exempt a recurring template's report sections from `large-blackboard`; or accept the warning, with the rationale recorded in coga/dream. Done when the chosen option is implemented, or the acceptance is recorded in docs/contexts/coga/dream/SKILL.md.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
