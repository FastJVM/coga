---
title: Run launched agents in a resource-limited systemd scope
status: draft
owner: nicktoper
workflow: null
---

## Description

On 2026-10-08 a runaway agent (Rust test suite `quiet` driven by a `run.sh`) exhausted thread/process creation in the user session and flooded the disk with temp files. cosmic-comp panicked on `failed to spawn thread: EAGAIN` (22:33), then the next boot hung for hours in tmpfiles cleanup and `vfs_unlink` lock contention until a journald watchdog timeout (06:55) forced a recovery-mode restart. Root cause on the Coga side: launched agents share `user-1000.slice` (TasksMax=154804, no MemoryMax) with the desktop compositor, so nothing stops one agent from starving the whole session.

Proposal: when `systemd-run` is available, have the agent spawn sites (`src/coga/repl_supervisor.py` fork/execvpe, `src/coga/recurring_runner.py` Popen) wrap the agent argv in `systemd-run --user --scope -p TasksMax=<n> -p MemoryMax=<size> --`, with limits configurable (e.g. a `[launch.limits]` table in `coga.toml`, machine overrides in `coga.local.toml`) and sensible defaults (TasksMax=4096, MemoryMax=24G). Fall back to a plain exec with a one-line warning when systemd-run is missing (macOS, containers). Name the scope after the task ref so `systemctl --user status` shows which ticket owns it, and killing the scope reaps every child.

Task and memory limits alone would only have prevented the first crash: the overnight hang came from the temp files themselves, which sat on the root filesystem (`/tmp` is not a tmpfs on this machine), survived two reboots, and took ~2h of `systemd-tmpfiles-clean` plus contended unlinks to remove. So also give each launch a private `TMPDIR` (exported as `TMPDIR`, `TMP` and `TEMP` to the agent and everything it spawns), e.g. `.coga/tmp/<ref>-<run-id>/` in the machine-local state dir. Remove it when the agent exits, and sweep stale directories left by a crashed run at the next launch, so leftovers never accumulate in `/tmp` and cleanup is scoped to one directory. An optional size cap (`[launch.limits] tmp_max`) is an open question: unprivileged user scopes cannot mount a tmpfs, so a cap would mean either checking usage from the supervisor and stopping the scope past the threshold, or pointing `TMPDIR` at `$XDG_RUNTIME_DIR` (already a size-capped tmpfs, but shared with the session's sockets, so filling it has its own blast radius).

Acceptance: a launched agent runs inside its own transient scope with the configured limits (verified via `systemctl --user show <scope> -p TasksMax -p MemoryMax`); a fork bomb inside the agent fails within the scope without affecting the session; the agent's temp files land in its private `TMPDIR` and are gone after it exits, with stale directories swept on the next launch; the fallback path is covered by a test; the owning topic (`coga/launch`) documents the behavior and the config keys.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
