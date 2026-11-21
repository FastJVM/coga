---
name: coga-dev/internals/spool-merge
description: Event-aware audit publication, guarded log mutation and recovery, retained legacy bytes, retire-worklist union merging, and local writer locking.
---

# Append and compact the audit log

`logfile.append_log` writes a complete encoded line in one `O_APPEND` write.
Git's union driver retains concurrent lines. `coga_edge.trim_log.trim`
selects eligible events from a snapshot and `logfile.replace_log` reads the
latest tail immediately before the atomic replacement. The remaining race
and operator conventions are documented in `coga/git`.
