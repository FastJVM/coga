---
title: Keep multiline audit messages on one log line
status: draft
owner: nicktoper
workflow: null
---

## Description

Ensure logfile.append_log writes exactly one physical, parseable audit line per event even when a message contains LF, CRLF, or multiline Git stderr. Keep diagnostic content legible and preserve the exact-byte return contract.

Done when regression cases cover multiline sync errors, task-log readers, and retract_log_lines removing the whole new event without orphan continuations or deleting another task's event. Decide and document how existing malformed history is read or repaired; do not silently rewrite the append-only log. This ticket fixes event encoding, not the underlying Git failures.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
