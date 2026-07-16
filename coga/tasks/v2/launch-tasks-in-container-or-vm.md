---
slug: v2/launch-tasks-in-container-or-vm
title: Launch tasks in a container or VM instead of locally
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow: null
---

## Description

Today `relay launch` always runs the configured agent CLI on the
human's local machine. That's fine for interactive work, but starts
to bite for:

- **Recurring tasks** scheduled via cron — they tie up the local
  shell, can't run when the laptop is closed, and inherit whatever
  half-broken state the dev environment happens to be in.
- **Idle/auto runs** (see `token-budget-aware-idle-execution-of-low-priority`)
  that we'd like to fire-and-forget without blocking the developer.
- **Tasks needing isolation** — different dependency sets, different
  secrets, network egress rules, GPUs, etc.

Add a way to launch a task in a container or VM instead of locally,
keeping the rest of the relay model (markdown files, git as the sync
layer, `bump` / `feed` / `panic` semantics) unchanged.

## Shape (sketch — to nail down in design step)

- **Where the runner is declared.** Probably `[runners.<name>]` in
  `relay.toml`, parallel to `[agents.<type>]`. An assignee or a
  recurring entry can set `runner = "<name>"` to opt in. Default
  remains local.
- **What a runner spec looks like.** At minimum: an image (or VM
  template), a way to fetch the repo (git clone vs. volume mount),
  and the env vars / secret refs to inject (same `env:VAR_NAME`
  pattern relay already uses).
- **Bump / feed / panic from inside the container.** The runner needs
  git push back to origin and Slack webhook access. Lockfile is local
  to the working tree, so the container's clone gets its own — fine
  as long as there's a heartbeat the local side can see (or as long
  as concurrent launches against the same task are still gated some
  other way).
- **Triggering.** Either an explicit `relay launch <slug> --runner X`
  flag, or implicit from the assignee/recurring config. Lean toward
  implicit so the human doesn't have to remember.

## Open questions

- **Tension with "locally operated"** (relay/principles). The whole
  pitch is markdown files on the user's machine. Containerized launch
  doesn't violate that — the source of truth is still the local repo —
  but it does add a remote execution surface. Worth being explicit
  about the boundary: state stays local, *execution* can be remote.
- **How does the container see the repo?** Cloning per-launch is
  clean but slow and doubles the lock state. Mounting the working
  tree is fast but ties the container's filesystem to the host — bad
  fit for actual VMs / cloud workers.
- **Synchronization back to the host.** If the container commits +
  pushes, the host needs to pull before the next local launch sees
  the new state. Cron-pull? Post-bump hook? Out of scope for v1?
- **Failure modes.** Container crashes mid-task → lock orphans → who
  cleans up? (Current dream/validate story handles stale local locks;
  remote heartbeats are a new thing.)
- **Scope of "container".** Docker locally, Docker on a remote host
  via SSH, a real cloud VM, a managed worker (Fly, Modal, etc.) —
  do we abstract over all of these, or pick one and ship?

## Out of scope (for this ticket)

- Replacing local launch entirely. Local stays the default.
- Multi-tenant orchestration / queueing / autoscaling — if we get
  there, it's a separate ticket on top.

## Why now

Two pressures pointing the same direction: recurring tasks (cron)
and the token-budget idle-execution proposal both want a way to run
work off the developer's machine. Worth designing once for both
rather than bolting on twice.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
