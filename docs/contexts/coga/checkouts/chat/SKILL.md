---
name: coga/checkouts/chat
description: Direct chat's checkout — the per-checkout occupancy guard, and the session-owned branch an agent prepares with `coga run prepare-checkout` before its first edit.
---

# Direct chat checkouts

Part of [coga/checkouts](../SKILL.md).

## Direct chat occupancy

A direct `bootstrap/orient` launch (`coga chat`) acquires a nonblocking,
checkout-scoped advisory lock before publishing state or preparing the
checkout. It holds the guard through the session, checkout return, and the
CLI's final state sweep. Another direct chat in the same checkout refuses
with exit 75, without publishing, switching branches, or starting an agent,
even when the first chat's feature branch is clean. Finish the first chat
or use a separate checkout; stateless tickets do not isolate shared files.

The guard is per Git checkout: nested Coga roots and symlink spellings of
one checkout share it; separate clones or linked checkouts do not. It is
released when the supervisor process exits; never delete its lock file to
bypass a live session. A guard failure refuses rather than assuming the
checkout is free. Agent subprocesses can still publish their ticket and log
updates while it is held.

`--prompt-report`, delegated bootstrap sessions, other launch targets,
Git-disabled and non-Git workspaces do not acquire this guard. It coordinates
direct chats running this version, not older supervisors, other launch types,
manual Git commands, or agents orphaned by a killed supervisor. Do not run
those concurrently against a chat's checkout. No task ownership lock or
cross-checkout exclusion is introduced.

## Preparing the chat's branch

`coga chat` (`bootstrap/orient`) starts on a clean, current `main` and may
stay discussion-only: nothing is allocated. Its notice carries an exact
`coga run prepare-checkout --session <id>` invocation; run it before the
first edit. It proves the session is the live chat holding this checkout's
occupancy guard (above), then
creates and switches to that chat's one reserved branch (`coga/chat-<id>`)
through the same mechanics. Repeating it on that branch is a no-op, even with
the chat's dirty work, and publishes nothing (the CLI exit sweep skips it).
Repeating it from a clean `main` after the chat committed on its branch and
switched back reuses that branch, commits kept, when it still descends from
the commit this chat created it at; a tip that does not refuses.
It exits 0 for prepared, reused, or an explicitly reported remote-less
exemption; 2 for bad usage; 75, changing nothing, for a stale or mismatched
session, a different branch, a conflicting reservation, or a dirty or
unprepared control checkout. A new chat never adopts an earlier chat's
branch; recover that work by hand under
[launch-boundary](../launch-boundary/SKILL.md#checkout-recovery). The launcher
returns the checkout when the chat ends, not after each turn. Without the
guard (Git disabled, non-Git) no invocation is offered: follow the
[manual procedure](../manual/SKILL.md).

After a failed or interrupted preparation, retry the same command: it
finishes creating the branch at the original commit even if control
advanced. A conflicting ref, a confirmed branch moved to a non-descendant,
or deletion of an already-confirmed branch still refuses. The preparation
recipe is a fixed `coga run` entry
([coga/extension-model](../../extension-model/SKILL.md)); it is not a task:
no ticket, workflow, transition, or blackboard.
