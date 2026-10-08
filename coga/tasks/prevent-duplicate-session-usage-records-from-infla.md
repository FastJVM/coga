---
title: Prevent duplicate session usage records from inflating totals
status: draft
owner: nicktoper
workflow: code/design-then-implement
---

## Description

Investigate identical session usage records appearing multiple times, distinguish duplicate writes from merge=union duplication, and make usage accounting count each logical record once without collapsing distinct launches or legitimate session segments.

Done when regressions cover repeated capture, duplicate lines after union merges, distinct sessions with equal token counts, records without session_id, and supported legacy schemas. Pin the safe record identity before choosing writer idempotency, reader deduplication, or both. Verify coga usage totals and identify any other affected consumers. Preserve the append-only audit history; do not rewrite old logs as a shortcut.

## Context

### Report relayed by the owner — 2026-10-07

Another AI reports 12 sessions with identical usage records repeated two to four times between 2026-08-17 and 2026-10-01, plus duplicate lines introduced by merge=union in thinkpick's log. The underlying excerpts were not supplied; reproduce counts and identify the repository before claiming a cause.

The owner has no excerpts to add; reproducing is part of the work. A local checkout of thinkpick exists at `~/Code/thinkpick`. As of 2026-10-08 its `coga/log.md` is only 40 lines with 3 `usage` mentions, and the repo has no `.gitattributes`. So the reported records probably live elsewhere (another file, branch, or history) or were already compacted. Find where its usage records actually live, and check `git log -p` on them, before treating thinkpick as the reproduction.

This differs from the done dedupe-claude-transcript-usage-by-message-id ticket: that work deduplicates message events within a provider transcript, not whole session records stored in log.md. Start with `src/coga/usage.py::append_record`, `load_records`, and their launch callers, then the log union-merge path. Distinguish the same logical record repeated from different launches or resumed segments sharing a provider session.

The reported inflation of coga usage needs a fixture and corrected before/after totals. Telemetry inflation is unverified: coga/usage explicitly says session activity/token records are excluded from aggregate telemetry. Inspect actual consumers rather than copying that claim as fact.

Read coga/usage (`docs/contexts/coga/usage/SKILL.md`), coga/internals/activity-capture (`docs/contexts/coga/internals/activity-capture/SKILL.md`), and coga/internals/spool-merge (`docs/contexts/coga/internals/spool-merge/SKILL.md`), cited rather than attached as investigation and possible editing targets. Update the owning topic and twins for any changed identity or accounting contract.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
