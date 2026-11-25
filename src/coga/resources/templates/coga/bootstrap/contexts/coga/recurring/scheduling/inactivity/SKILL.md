---
name: coga/recurring/scheduling/inactivity
description: Repo inactivity — the local ticket-activity gate on recurring sweeps, and when autofix runs on an inactive sweep.
---

# Inactivity

`[recurring].idle_days` sets the number of calendar days after which ordinary
recurring templates are skipped. Zero disables the gate. Activity is read from
the local audit log, excluding recurring and autofix ticket entries. Templates
that declare `run_when_inactive: true` may still run. A forced sweep bypasses
this gate.

On an inactive repo the post-sweep [autofix](../../autofix/SKILL.md) loop runs
only when the sweep launched something, such as a `run_when_inactive`
template; an inactive sweep that launched nothing is not analyzed.
