---
title: Prevent duplicate session usage records from inflating totals
status: draft
owner: nicktoper
workflow: code/design-then-implement
---

## Description

Investigate identical session usage records appearing multiple times, distinguish duplicate writes from merge=union duplication, and make usage accounting count each logical record once without collapsing distinct launches or legitimate session segments.

Done when regressions cover repeated capture, duplicate lines after union merges, distinct sessions with equal token counts, records without session_id, and the supported legacy record schemas (v1 and v2, both accepted by `usage` record parsing). Pin the safe record identity before choosing writer idempotency, reader deduplication, or both. Verify coga usage totals and identify any other affected consumers. A consumer that reads records through the fixed `usage` path is covered and verified here. A consumer with its own reader gets a follow-up ticket, named on the blackboard, unless its fix is trivial. Preserve the append-only audit history; do not rewrite old logs as a shortcut.

## Context

### Report relayed by the owner — 2026-10-07

Another AI reports 12 sessions with identical usage records repeated two to four times between 2026-08-17 and 2026-10-01, plus duplicate lines introduced by merge=union in thinkpick's log. The underlying excerpts were not supplied; reproduce counts and identify the repository before claiming a cause.

The owner has no excerpts to add; reproducing is part of the work. A local checkout of thinkpick exists at `~/Code/thinkpick`. Its `coga/.gitattributes` sets `**/log.md merge=union` and `**/retires.md merge=union`, so the union path is live there. As of 2026-10-08, though, its current `coga/log.md` is only 40 lines with 3 usage records, and that file's 20-commit history shows only about 6 `"schema"` lines. So the reported duplicates probably sit on other branches, in other repos, or in history before compaction. Find where they actually are before treating thinkpick's current log as the reproduction.

The only record key that looks like an identity is `session_id`, and it is optional. Resumed segments can also share one provider session, so the design must name the record identity explicitly. `load_records` reads only the current `coga/log.md` and has no dedup today. If the design finds real double writes in launch capture rather than union duplication, consider splitting the writer fix from the reader dedup at the design gate.

This differs from the done dedupe-claude-transcript-usage-by-message-id ticket: that work deduplicates message events within a provider transcript, not whole session records stored in log.md. Start with `src/coga/usage.py::append_record`, `load_records`, and their launch callers, then the log union-merge path. Distinguish the same logical record repeated from different launches or resumed segments sharing a provider session.

The reported inflation of coga usage needs a fixture and corrected before/after totals. Telemetry inflation is unverified: coga/usage explicitly says session activity/token records are excluded from aggregate telemetry. Inspect actual consumers rather than copying that claim as fact. One concrete consumer to check is the phone-home recurring job (`coga/recurring/phone-home/ticket.md` and its `ticket.py`, packaged under `src/coga/resources/templates/coga/recurring/phone-home/`), which mentions usage.

Read coga/usage (`docs/contexts/coga/usage/SKILL.md`), coga/internals/activity-capture (`docs/contexts/coga/internals/activity-capture/SKILL.md`), and coga/internals/spool-merge (`docs/contexts/coga/internals/spool-merge/SKILL.md`), cited rather than attached as investigation and possible editing targets. Update the owning topic and twins for any changed identity or accounting contract.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
