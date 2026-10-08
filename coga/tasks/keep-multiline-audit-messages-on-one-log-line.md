---
title: Keep multiline audit messages on one log line
status: draft
owner: nicktoper
workflow: code/with-review
---

## Description

Ensure logfile.append_log writes exactly one physical, parseable audit line per event even when a message contains LF, CRLF, or multiline Git stderr. Keep diagnostic content legible and preserve the exact-byte return contract.

Done when regression cases cover multiline sync errors, task-log readers, and retract_log_lines removing the whole new event without orphan continuations or deleting another task's event. Decide and document how existing malformed history is read or repaired; do not silently rewrite the append-only log. This ticket fixes event encoding, not the underlying Git failures.

## Context

### Report relayed by the owner — 2026-10-07

Another AI counted 585 out-of-format log lines and reports that multiline entries still occur in October. Its example is `sync failed: {exc}` carrying complete Git stderr. The source log and counting procedure were not supplied; treat the count as reported evidence, not a locally reproduced measurement.

Intake source inspection confirms `src/coga/logfile.py::append_log` interpolates message bytes directly despite promising one line per event. `retract_log_lines` filters physical lines by the task tag, so untagged continuation lines can survive retraction. Cover LF, CRLF, and bare CR explicitly without confusing literal backslash escapes with actual newlines.

Read coga/internals/spool-merge (`docs/contexts/coga/internals/spool-merge/SKILL.md`) and coga/internals/state-publication (`docs/contexts/coga/internals/state-publication/SKILL.md`), cited rather than attached; inspect append-only merging and strict rollback before changing encoding. Start with logfile.py and its tests. Coordinate with fix-coga-git-sync-failures-that-leave-main-diverge, which owns the failures themselves, and prevent-duplicate-session-usage-records-from-infla, which owns usage deduplication.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
