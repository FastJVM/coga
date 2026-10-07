---
title: Recheck Codex usage completeness after the session matching fix
status: draft
owner: nicktoper
workflow: null
---

## Description

On or after 2026-10-14, audit Codex sessions started after the deployed fix from PR #961 to see whether session_id and human_turns are still missing. This is a dated follow-up investigation, not evidence of a surviving bug and not an automatic scheduled job.

Confirm the merge timestamp and the installed revision actually used by each launch. Exclude sessions started before that deployment from the post-fix cohort. Report sample size, date range and timezone, missing-field counts, usage_reason and transcript availability, and whether missing human_turns is unknown versus a legitimate zero. If the sample is too small, say so and choose a later observation window. File or update a narrowly scoped fix only if post-fix evidence reproduces a defect; otherwise record the result without restamping old records.

## Context

### Baseline reported by another AI, relayed by the owner — 2026-10-07

- 65 Codex records lacked session_id from 2026-07-19 through 2026-10-07.
- Since 2026-10-05, 10 of 21 Codex sessions lacked human_turns.
- PR #961 (https://github.com/FastJVM/coga/pull/961), match-concurrent-codex-sessions-to-their-launch-so, reportedly merged 2026-10-07 at 11:23; the report did not specify a timezone.
- The last session missing data reportedly started before the merge, so the report cannot establish that the fix failed.

These counts and timing were not independently reproduced during intake. Preserve the distinction between merge time, installed revision, session start, and record write time. Collect the source logs and matching transcript evidence without exposing private transcript content.

Earliest reassessment: 2026-10-14, one week after this report. This draft is not a reminder or automation. Read coga/usage (`docs/contexts/coga/usage/SKILL.md`) and coga/internals/activity-capture (`docs/contexts/coga/internals/activity-capture/SKILL.md`), cited rather than attached; inspect matching, unknown reasons, and the activity schema. Keep missing metadata separate from duplicate records and incorrectly classified failures.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
