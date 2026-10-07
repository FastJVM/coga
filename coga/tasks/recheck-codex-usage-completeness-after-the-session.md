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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
