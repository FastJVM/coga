---
title: Recover recurring runs orphaned when the supervisor dies (e.g. laptop sleep)
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/recurring
- relay/architecture
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 4 (review)
---

## Description

A `relay recurring` (or `relay recurring --all`) sweep runs a PTY supervisor
process tree: `relay recurring` → `relay launch` → the agent REPL. That tree is
in-memory only — nothing is checkpointed. When the terminal dies (laptop sleep,
SSH drop, tab close), the whole tree is SIGKILLed mid-sweep. Resuming the agent
conversation (`--resume`) only restores transcript, not the process tree, so the
sweep does **not** continue.

The disk is left wedged: the in-flight task is frozen `in_progress`, the sweep's
later tasks never launched, and the `--all` cleanup lines never printed. Because
`relay recurring` **skips** `in_progress` tasks (it reads that status as "someone
is actively working this"), nothing ever picks the orphan back up. There is no
daemon and no mutex to distinguish a *stale* claim (dead supervisor) from a
*live* one (real running session), so a crashed run sits dead forever until a
human manually deletes/marks it.

Concrete instance that motivated this (2026-06-04): a `recurring --all` debug
sweep was killed by laptop sleep, leaving `digest-dbg-…` and
`relay-dev-update-dbg-…` stuck `in_progress`; they had to be cleaned up by hand
(`git checkout` the leaked digest spool + three `relay delete`s + a rebase to
reconcile the failed auto-push).

## Chosen approach (decided with the human, 2026-06-05)

Don't detect liveness at all. Just stop skipping `in_progress` and relaunch it.

The earlier framing reached for staleness heuristics / a heartbeat marker to
answer "is this `in_progress` task dead or a live session?" We deliberately drop
that question. `relay recurring` is a foreground command a human runs in a
shell — there is no daemon and (in normal use) no second sweep running
concurrently — so the only way an `in_progress` recurring period task exists at
scan time is that a *past* sweep died and left it. Relaunch it and resume its
step. Worst case a false relaunch re-does some work the human then catches; that
is a cheap, recoverable event, not worth a detection mechanism to avoid.

**The rule:**

- `done` period task → still **skipped**. Finished work never re-runs. This is
  the "distinguish done from incomplete" requirement, and it falls out of
  status for free: a completed period task is `done`, a crashed one is
  `in_progress` (it definitionally never reached `relay mark done`).
- `in_progress` period task → **relaunch and resume its current workflow step**
  (not scaffold fresh, not restart from step 1). This is the only behavior
  change.
- `active` period task → launches as today.

So the later, still-`active` tasks in a crashed sweep are picked up by the same
idempotent scan, and the frozen orphan is resumed — no marker, no threshold, no
liveness check, no new files.

### Accepted tradeoff

Two flavors of "runs twice," only one of which we're accepting:

- **Sequential re-run (accepted):** a past sweep died; a later `relay recurring`
  relaunches the orphan. Worst case it redoes a step or re-opens a PR — the
  human notices and cleans up. This is the explicit accepted cost.
- **Concurrent stomp (out of scope, naturally avoided):** two `relay recurring`
  running *at the same time* both grab the same `in_progress` task → two agents
  writing the same task dir / branch in real time. This is corruption, not a
  catchable dup — but it only arises if two sweeps run simultaneously, which a
  foreground shell command run by hand doesn't. If recurring ever moves to
  cron/unattended where overlap is real, a guard becomes a *separate, future*
  ticket. Not handled here.

### Implementation surface

- `recurring.py` — widen the relaunch predicate. `DueTask.launchable` currently
  returns `status == "active"`; it (or a new "relaunchable" notion feeding
  `DueScan.due`) must also include `in_progress`. `scan_due` already
  get-or-creates the existing period task (`scaffold_template` returns the
  existing dir when present), so no duplicate task dir is created.
- The launch path must **resume the existing step** of an `in_progress` ticket
  rather than treat it as a fresh `active` launch. Confirm `relay launch`
  accepts an `in_progress` ticket and re-composes from its current `step:`; wire
  it up if it currently refuses anything past `active` (cf. `_launch_scaffolded`
  in `commands/recurring.py`, which today only launches `active`).
- Leave `paused` skipped (a human deliberately parked it — not an orphan).
- Update the `relay/recurring` context and `relay recurring` CLI help to state
  the new behavior (in_progress recurring period tasks are relaunched/resumed;
  done is skipped). Keep the packaged copy under
  `src/relay/resources/templates/relay-os/` in sync (per CLAUDE.md).

### Out of scope

- No liveness detection, heartbeat/pid/mtime marker, staleness threshold, or new
  `relay recover` command.
- Cleaning up partial side effects of the crash (the motivating incident leaked
  a digest spool and a failed auto-push needing a rebase). Resuming the *step*
  is this ticket; the resumed agent/step owns reconciling half-written artifacts
  and worktree/branch state.

Sibling ticket: `supervisor-liveness-watchdog-for-agents-that-never-signal-done`
covers the *inverse* failure — a wedged agent while the supervisor is still
**alive** (idle-timeout territory). This ticket is the case where the supervisor
itself is **gone**, so a watchdog has nothing to fire. They're complementary,
not duplicates.

## Context

- `relay/recurring` — recurring tasks as ticket-format directories, the scaffold
  contract, period-task naming, the template-blackboard ledger, and that the
  bare sweep currently skips `done`/`in_progress`/`paused`. **Attached** — this
  ticket changes that skip behavior for `in_progress`.
- `relay/architecture` — "Status is the signal" (no mutex; `status` is the only
  coordination signal). **Attached** — this change leans directly on status as
  the sole signal (relaunch `in_progress`, skip `done`) and on the no-daemon /
  single-foreground-sweep reality that makes skipping liveness detection safe.
- Source: `recurring.py` (`scan_due`, `DueTask.launchable`, `DueScan.due`,
  period slug + ledger helpers), `commands/recurring.py` (the sequential
  `for task in due` sweep loop and `_launch_scaffolded`, which today only
  launches `active`).

