---
name: coga-dev/internals/spool-merge
description: Local audit-log appends, megalaunch dependency events, Git union merges, and compaction.
---

# Append and compact the audit log

`logfile.append_log` writes a complete encoded line in one `O_APPEND` write.
Git's union driver retains concurrent lines. `coga_edge.trim_log.trim`
selects eligible events from a snapshot and `logfile.replace_log` reads the
latest tail immediately before the atomic replacement. The remaining race
and operator conventions are documented in `coga/git`.

During megalaunch's dependency drain, `coga_edge.megalaunch` appends an
event after each successful local ticket update:

- `_resolve_partial_dependency_blockers` records `resolved finished dependency
  blockers (still blocked)` as `megalaunch` after updating the blackboard.
  The ticket stays blocked and the drain uses no launch attempt.
- `_activate_for_launch` validates and writes the active ticket with its
  blocker answers, then records `activated (blocked → active)` as `system`,
  including the dependency that finished.
