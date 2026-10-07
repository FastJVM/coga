---
title: Prevent duplicate session usage records from inflating totals
status: draft
owner: nicktoper
workflow: null
---

## Description

Investigate identical session usage records appearing multiple times, distinguish duplicate writes from merge=union duplication, and make usage accounting count each logical record once without collapsing distinct launches or legitimate session segments.

Done when regressions cover repeated capture, duplicate lines after union merges, distinct sessions with equal token counts, records without session_id, and supported legacy schemas. Pin the safe record identity before choosing writer idempotency, reader deduplication, or both. Verify coga usage totals and identify any other affected consumers. Preserve the append-only audit history; do not rewrite old logs as a shortcut.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
