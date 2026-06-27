---
slug: change-log-format-union-merge-in-git
title: change log format + union merge in git
status: active
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
secrets: null
step: 1 (execute)
---

## Description

Make `coga/log.md` (and the recurring `spool.md` files) safe to append to
concurrently across git branches/clones without merge conflicts, by (a) keeping
each log entry on a single self-contained line and (b) marking the file
`merge=union` via `.gitattributes` so git auto-resolves concurrent appends.

**Resolution: already implemented — closed as done, no new work.** The feature
exists and is live in this repo (landed by the rename commit #454). See Context
for exactly where.

## Context

Verified present on 2026-06-26:

- `coga/.gitattributes` contains `**/log.md merge=union` and
  `**/spool.md merge=union`. Mirrored in the packaged template
  (`src/coga/resources/templates/coga/.gitattributes`) and the `example/coga/`
  fixture. `git check-attr merge coga/log.md` returns `merge: union`, so it is
  active, not just declared.
- The log is already one-line-per-entry:
  `YYYY-MM-DD HH:MM [<task-ref>] [<actor>] <message>`, written by
  `append_log()` in `src/coga/logfile.py`. Single self-contained lines are what
  make union merge coherent (no multi-line entries to interleave).
- `src/coga/logfile.py`'s module docstring already documents the design and the
  rationale ("readers sort on display, so union's possible duplicate/unsorted
  lines are harmless for an append-only audit trail").

Out of scope / tracked elsewhere: timestamp precision under union merge
(minute-resolution, no timezone makes interleaved-append ordering ambiguous) is
covered by the separate draft `log-timestamps-need-seconds-and-timezone-for-unamb`.

<!-- coga:blackboard -->

Closed as already-done per nick (2026-06-26). The union-merge + one-line log
format was already shipped; nothing to build. Body documents where the feature
lives so this stays findable.

The blackboard is a notepad to be written to often as the human and agent works through a task.
