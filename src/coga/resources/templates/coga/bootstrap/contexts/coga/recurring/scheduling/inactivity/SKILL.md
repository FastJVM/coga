---
name: coga/recurring/scheduling/inactivity
description: Repo inactivity and session liveness — the human-commit gate on sweeps, completion signaling and terminal-ticket recovery, and how late teardown differs from unfinished timeouts.
---

# Inactivity

`[recurring].idle_days` sets the number of calendar days after which ordinary
recurring templates are skipped. Zero disables the gate. Activity is read from
the local audit log, excluding recurring and autofix ticket entries. Templates
that declare `run_when_inactive: true` may still run. A forced sweep bypasses
this gate.
