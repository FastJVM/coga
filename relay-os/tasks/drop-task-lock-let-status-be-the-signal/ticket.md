---
title: Drop task.lock; let status be the signal
status: done
mode: interactive
owner: nick
human: nick
agent: claude1
assignee: nick
workflow:
  name: code/with-review
  steps:
  - name: implement
    skill: code/implement-and-pr
  - name: review
    assignee: owner
contexts:
- relay/architecture
- relay/codebase
- relay/cli
- relay/principles
---

## Description

`task.lock` is a file-existence mutex that protects against two workers
running the same task concurrently. Under the one-task-one-worker v1
constraint (≤5-person teams, single repo, local-only), that collision
is rare; the lock's steady-state cost is not.

Costs we're paying for it today:

- `src/relay/lock.py` — ~94 lines plus `LockHeldError`/`LockInfo` types
  threaded through `launch`, `launch_script`, `bump`, `delete`, `panic`,
  `validate`.
- `relay launch --force` and `relay delete --force` flags exist
  *only* to break stale locks.
- A dedicated Dream worker (`validate-drift`) reports stale locks.
- `relay-os/.gitignore` excludes `**/task.lock` (a tracked exclusion
  for a file most users never see).
- Agent base prompt has two "don't touch `task.lock`" rules.
- Crashed agents leave orphan locks that have to be hand-cleared.

What it actually buys us: a hard guarantee that two `relay launch`
processes on the same slug can't both proceed. In practice this collision
is rare, and the failure mode (two divergent blackboard edits, two PR
branches) is visible and recoverable.

## Decision

Drop the lock file entirely. Replace it with a soft staleness check
read off the existing control plane:

- `relay launch <slug>` proceeds without writing any lock file.
- If the ticket is already `status: active`, `launch` prints a warning
  that names the assignee and (if available from `log.md`) the time of
  the last log entry, then prompts the human to continue. In `mode: auto`
  / `mode: script`, the warning is logged but does not block.
- No `--force` flags. `relay delete` removes the directory unconditionally
  (it's already destructive; `git restore` is the audit trail per the
  existing spec).

Status is the signal:
- `draft` — not started.
- `active` — work in flight; soft-warn on relaunch.
- `paused` — frozen by a human.
- `done` — finished.

This collapses control plane + "is it locked" into one read of `status:`.

## Implementation

### Code

- Delete `src/relay/lock.py`.
- Remove `TaskLock` / `LockHeldError` imports and call sites from:
  - `src/relay/commands/launch.py`
  - `src/relay/commands/launch_script.py`
  - `src/relay/commands/delete.py` (drop `--force` flag entirely)
  - `src/relay/commands/panic.py` (release-on-panic logic disappears)
  - `src/relay/bump.py`
  - `src/relay/validate.py`
- In `launch`: if `status == "active"`, read the last `log.md` entry's
  timestamp, print
  `⚠ <slug> is already active (assignee: <name>, last log <Nm> ago) — continue? [y/N]`
  in interactive; log a one-line warning in auto/script and proceed.
- Drop the `--force` flag from `relay launch` (was lock-only).
- Remove `**/task.lock` line from `src/relay/resources/templates/relay-os/.gitignore`
  and from any tracked `relay-os/.gitignore` files.
- Drop the two "don't touch `task.lock`" lines from
  `src/relay/resources/prompt.md` (base prompt) and the parallel rule
  in `src/relay/commands/init.py`'s scaffolded `rules.md`.

### Dream

- `bootstrap/dream`'s known-skill list drops the lock-aware part of
  `validate-drift`. The skill still validates frontmatter shape and
  drift; it stops looking at `task.lock`.

### Tests

- Delete `tests/test_primitives.py`'s lock cases.
- Update `tests/test_launch.py`, `tests/test_launch_auto.py`,
  `tests/test_launch_script.py`, `tests/test_commands.py`,
  `tests/test_validate.py` — drop any `TaskLock` imports, drop the
  "no task.lock left behind" assertions (true by construction now),
  add tests for the new soft-warn-on-active behavior.

### Docs

Three layers to update, kept in sync with the code:

- `relay-os/contexts/relay/architecture/SKILL.md` — drop the
  "Locking" section, rewrite the "Two state machines per ticket"
  paragraph to note status absorbs the in-flight signal, and remove
  `task.lock` from the primitives list.
- `relay-os/contexts/relay/cli/SKILL.md` — remove the `--force` flag
  doc from `launch` and `delete`; rewrite the "Refuses if `task.lock`
  is held" sentence under `relay delete`.
- `docs/spec.md` — the spec has the deepest lock surface
  (§ lock file contents, staleness detection, single-lock-per-task
  rationale, script-mode acquisition rules). Replace with the
  status-is-signal model and the soft-warn UX.
- `README.md` — two sentences mention the lock; rewrite.
- `relay-os/contexts/relay/project-stage/SKILL.md` — the line
  "Renaming `task.lock` to `lock` is fine" becomes "Removing the
  task-lock mechanism is fine" (or just drops the example).

## Migration

Existing on-disk `task.lock` files become noise but cause no harm —
the new code ignores them. A one-liner cleanup is fine:

```bash
find relay-os/tasks -name task.lock -delete
```

Not blocking; let it happen naturally as Dream runs or as tasks finish.

## Out of scope

- Distributed locking, multi-machine coordination, anything that
  re-introduces a coordination primitive. The v1 constraint (one
  worker per task, local-only, ≤5-person teams) still holds; we just
  stop pretending we need a mutex to enforce it.
- Renaming `status` values. `active` already means "in flight." Don't
  add `in_progress` or `working` — that's the conflation we just
  argued against.

## Why this is the right shape

- Legibility (per `relay/principles`): one file, one fact. Today a
  human reading `ticket.md` sees `status: active` but has to also
  `ls task.lock` to know if a worker is *actually* running. After:
  the answer is in the file you opened.
- No premature abstraction: the lock defends against a collision we
  rarely see; the steady-state tax is paid every launch, every
  delete, every panic, every Dream run.
- Fail-loud: a soft warn on relaunch surfaces the situation visibly;
  the previous behavior (hard block requiring `--force`) hid it
  behind a flag.

## Discussion log

Decision originated in an orient session (2026-05-11). Path traveled:

1. "Could we add an `in_progress` status?" → No, conflates control
   plane (`draft → active → done`) with execution state.
2. "Then surface the lock in `relay status` output (🔒 column)?" →
   Helps readability but doesn't address brittleness.
3. "The lock is overkill and creating more issues than anything else."
   → Agreed. Status absorbs the signal; soft warn replaces hard mutex.
