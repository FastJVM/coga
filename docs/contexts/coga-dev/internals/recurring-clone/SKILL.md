---
name: coga-dev/internals/recurring-clone
description: How `src/coga/recurring_clone.py` runs one clone-scoped template — ledger location, environment, the wall-clock deadline, bounded output draining, process-tree termination and the Windows job object.
---

# Clone-scoped template runs

The user contract (what clone scope is, what the sweep records and when it
retries) is in
[coga/recurring/scheduling](../../../coga/recurring/scheduling/SKILL.md#repo-scope-and-clone-scope).
This page holds what a change to `src/coga/recurring_clone.py` or
`recurring.scan_clone_due` must keep.

## Ledger and environment

`recurring.scan_clone_due` decides due clone templates from the clone ledger
(`read_clone_ledger`), not `coga/log.md`. `clone_state_dir` resolves
`.coga/recurring-clone/` through git's common dir, so a run from a temporary
control worktree records for the primary checkout that owns it. Only exit 0
advances the ledger (`record_clone_period`).

`run_clone_template` builds the launch environment with the template's
secrets, strips every `TASK_ENV_KEYS` variable so a shim that would bump a task
finds none, and sets the `COGA_RECURRING_*` scope, template and period
variables.

## Deadline and output

The deadline is `run_clone_template`'s `timeout` (15 minutes by default),
independent of the agent REPL watchdog; it must be finite and positive. Output
is drained as it arrives through a bounded buffer: the console and local log
retain at most the first 1,000,000 characters with an explicit truncation
marker, and a truncated log also keeps the last 4,000 characters, which is what
the sweep's run record receives. Truncation loses middle output.

A timeout returns exit 124 with a diagnostic, terminates the process group,
reaps the script, and leaves the ledger unchanged so later templates run and
the next sweep retries.

## Windows

The shared `oscompat.ProcessTree` owns both recurring runners' children.
On Windows its wrapper (`_WINDOWS_JOB_WRAPPER`) joins a supervisor-owned job
object (`_WindowsJob`) before starting any script code, so descendants remain
owned after their parent exits. Job termination and kill-on-close clean up the
entire tree; setup or cleanup errors are reported, never replaced by
best-effort PID lookup. This costs one wrapper process per run.
