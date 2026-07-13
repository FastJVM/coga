---
slug: v2/log-timestamps-need-seconds-and-timezone-for-unamb
title: Log timestamps need seconds and timezone for unambiguous ordering
status: draft
mode: agent
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

Priority: low. Cheap fix; matters for a tool that sells an auditable
correction loop.

`append_log` writes timestamps as `%Y-%m-%d %H:%M` (`logfile.py:20`) —
**minute resolution, no seconds, no timezone**. Two events in the same minute
are unordered except by file position, and cross-machine ordering is ambiguous
(local time, no TZ offset). For a system whose pitch is "legible, auditable
correction loop," dropping seconds and TZ is a real weakness in the one
append-only audit surface.

Also note: `last_activity` (`logfile.py:26-47`) parses the timestamp prefix by
walking lines backward, but `validate.py`'s stuck-in-progress detection uses file
**mtime** instead (`validate.py:312-323`) — so the two notions of "last
activity" can disagree. Worth reconciling them while in here.

Fix: write ISO-8601 with seconds and an explicit offset (e.g.
`2026-05-29T18:43:07-07:00` or UTC `Z`). Keep it greppable/human-readable.
Update any parsers (`last_activity`) and reconcile the stuck-detection to use log
content rather than mtime if practical.

Acceptance: new log lines carry seconds + timezone; `last_activity` still parses
them; stuck-detection and `last_activity` agree on "last activity"; tested.

## Context

Code: `src/relay/logfile.py` (`append_log` :13-24, format :20; `last_activity`
:26-47), `src/relay/validate.py:312-323` (mtime-based stuck detection).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
