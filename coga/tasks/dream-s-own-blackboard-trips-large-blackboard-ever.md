---
title: Dream's own blackboard trips large-blackboard every run
status: draft
owner: nicktoper
contexts:
  - coga/dream
workflow: code/design-then-implement
---

## Description

Found by validate-drift-blackboard-hygiene-two-oversized-bl on 2026-10-06. `coga validate --json` reports `large-blackboard` (warn, 51.5 KiB vs 32.0 KiB) for `recurring/dream` itself: the recurring template's blackboard holds the latest run's report, and its `## Findings` section alone was ~30 KiB for 2026-W41 (plus ~12.5 KiB `## Dream Skill: validate-drift` and ~8 KiB `## Dream Run Summary`). Dream's phase writers replace these sections on each firing, so hand-trimming would be overwritten next run and would interfere with Dream's own writers (coga/period-task: own only your keys). Because every run regenerates sections of this size, the warning will keep coming back, and Dream's own Phase 1 reports it about itself. Owner decision needed: have Dream write bulky per-run sections (Findings, validate-drift detail) to a sibling attachment under `coga/tasks/recurring/dream/` and keep only the summary and cross-run state on the blackboard; or exempt a recurring template's report sections from `large-blackboard`; or accept the warning, with the rationale recorded in coga/dream. Done when the chosen option is implemented, or the acceptance is recorded in docs/contexts/coga/dream/SKILL.md.

## Context

The design step picks one of the three options and lays out the tradeoff. The owner makes the final decision at the `review-design` gate. If the owner accepts the warning, `implement` only edits the docs, and the PR is a docs-only change.

Where things live (as of 2026-10-08):
- The check is `validate._check_task` → `blackboard.blackboard_size_warning`. It emits `large-blackboard` (warn), and the threshold is `blackboard.BLACKBOARD_WARN_BYTES` (32 KiB). `launch` uses the same constant for its own warning when a blackboard is oversized.
- Dream's `validate-drift` scan classifies `large-blackboard` in `dream_validate_drift.classify_issue` as a PR proposal. The remedy it proposes is the `coga/blackboard` bloated-blackboard fix: move to directory form, then move dated evidence into sibling attachments. That remedy is option 1 applied to Dream itself. Dream's own blackboard keeps triggering it, so Dream reports on itself every run.
- Section writers: `dream_validate_drift` renders `## Dream Skill: validate-drift`, and `dream_cleanup_orphan_markers` renders `## Dream Skill: cleanup-orphan-markers`. The `## Findings` and `## Dream Run Summary` sections come from the scan skills under `src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/` (`scan-protocol`, `knowledge-scan`, `contract-audit`). Each writer replaces only the keys it owns (`coga/period-task`), so a fix has to change the writers themselves. Hand-trimming the blackboard does not last.
- `coga/tasks/recurring/dream/` is already in directory form (`ticket.md`, about 90 KiB on 2026-10-08). The recurring template's packaged twin is `src/coga/resources/templates/coga/recurring/dream/ticket.md`. Keep the twins byte-identical, or record the difference in `tests/test_packaging.py` (`coga/packaging`).
- Option 1 needs a retention rule for the attachment: overwrite it each run, or keep it per period. It also needs a decision on whether the blackboard keeps a pointer to the attachment. Option 2 would put a recurring-template special case into the core validator, so the design should explain why that is better than fixing the writers (`coga/extension-model`, `coga/principles`).
- Behavior contract owners to update in the same PR: `docs/contexts/coga/dream/SKILL.md` (attached; its `## Results and safety` section owns the run report). Depending on the option, also update `coga/blackboard` and `coga/recurring`. These are cited rather than attached, so read their bloated-blackboard and recurring-template sections when you need them.

Out of scope: lowering or raising `BLACKBOARD_WARN_BYTES` for every task, and trimming other tasks' oversized blackboards.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
