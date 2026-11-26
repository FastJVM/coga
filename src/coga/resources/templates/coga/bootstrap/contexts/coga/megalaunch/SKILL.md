---
name: coga/megalaunch
description: How `coga megalaunch` selects, orders, gates, and runs queued work — the owner-scoped sweep and picker (`--owner`, `--all-owners`), the `--pick`/`--relaunch` staged selection, drain order, the post-sweep dependency drain, `--max-tasks` accounting, `--agent`, and the run summary.
---

# Coga megalaunch

`coga megalaunch` runs launchable work one task at a time (flags and syntax:
`coga megalaunch --help`). It is on-demand only: no recurring template ships
for it. `megalaunch` expands to `launch bootstrap/megalaunch --`; `pick` expands
directly to `launch bootstrap/megalaunch -- --pick`. For one task,
`coga launch <slug>` ([launch](../launch/SKILL.md)) is the attended path.

## Sessions

Every step is a normal interactive agent REPL under the PTY watcher,
released by the done sentinel, never a headless `-p` run. The whole run,
and the picker, require stdin and stdout to be TTYs. The TTY is transport,
not approval: the composed `megalaunch` conduct layer tells the agent to
announce its plan and continue, and to end in `coga block` when it truly
needs the owner; a normal final reply does not release the queue. Idle and
max-session backstops are armed with the same resolution recurring uses; a
timeout names its trigger and duration. A task chains through at most 8
agent steps per run (`failed: exceeded 8 unattended steps`), and an exit that
changes neither step nor status is `failed`.

The queue reads local tickets. A workflow script runs before the agent
phase. A script that bumps chains to the next step, and one that leaves
its step open hands it to the agent. The queue stops a ticket when it
reaches an owner-held step or a script or agent failure.
If a workflow's step script fails or a step ends after `enter` without
completing its handoff, Megalaunch stops the queue so the operator can
recover the checkout before another ticket starts.

## Owner filter

The sweep and the `--pick` list cover one owner's tickets: `current_user`'s
by default, `--owner <name>`'s instead, or every owner's (owner-less tickets
included) with `--all-owners`. The filter reads the ticket's `owner:`, never
who holds the current step. Owners are free strings, so an `--owner` that
matches nothing gives an empty picker or sweep with a message, not an error.
`--owner` with `--all-owners` is refused, and so is either flag with
`--relaunch`, whose saved selection replays as-is. The operator stays
`current_user` even when the tickets belong to someone else; lifecycle
notifications still go to each ticket's owner, and the summary names a
non-default filter (`Owner: <name>`).

## Bare sweep

Silently ignores tickets outside the owner filter and every status but
`active`, `in_progress`, and `blocked`.
Blocked tickets and ones with open asks report `skipped-unresolved-blocker`;
a missing current step or an owner-held step reports `skipped-human-gate`.
Coordinate with a ticket’s owner before queuing work they already started. The queue
scan is only a hint: each launch rereads exact bytes and reapplies the same
owner filter plus the status, blocker, and current-step gates to them. A task that vanished since
the scan is skipped without a row.

## Explicit selection

`--pick` offers every non-terminal task inside the owner filter (yours by
default) with no launchability filter, displayed like default `coga status` (last updated first), with
nothing checked. The confirmed set is saved machine-locally under `.coga/`;
`--relaunch` replays it, skipping vanished tasks with a warning. A selection
runs in three stages:

1. **Prepare** — if the pick has drafts, one `[Y/n]` prompt offers the guided
   `coga ticket` interview for each; an authoring failure leaves the draft.
   The interviewer follows the authoring-agent order in
   [coga/tickets/authoring](../tickets/authoring/SKILL.md) and is never prompted for.
2. **Check** — draft/paused/blocked picks are validated against their
   prospective `active` view without writing; failures report now.
3. **Launch** — each pick is reread and reclassified when reached, then
   preflighted, and only then activated. A pick not reached under
   `--max-tasks` stays untouched.

A picked blocked ticket with open asks resumes with the resolve-or-re-block
preamble and returns to `blocked` if the ask stays open; an ask-less one is
`skipped-unlaunchable`, as are terminal and unactivatable picks. The owner
flags only shape the offered list; confirmed picks run whatever their owner. A human
step is `skipped-human-gate` even under `--agent`. Explicit selections never
run the dependency drain, so they cannot expand into unpicked work.

## Order

Oldest first by each ref's first `coga/log.md` line (committed, so clones
agree). A sub-directory with at least one `<n>-` task runs as one block
anchored at its oldest task, numbered tasks by number (`02-` == `2-`, `10-`
after `9-`), then unnumbered siblings by age. Top-level tasks never form a
block; `2fa-login` is not numbered. `coga status --order-by created` shows the
same order; a selection filters it, so pick order never sets run order. `coga validate` warns `duplicate-task-number`.

## Dependency drain

After a bare sweep, megalaunch re-lists the blocked tickets inside the same
owner filter and directory scope. Draining another owner's tickets answers
nothing on their behalf: only blockers whose named dependency has finished
resolve, under the [dependency contract](../lifecycle/SKILL.md#dependencies-and-supersession).
The ticket and its open asks are recaptured as exact bytes before selecting
satisfied entries. Each selected entry gets an automatic answer naming its
finished dependency; other entries keep their asks and answers untouched.
Partial resolutions update the blocked ticket locally and consume no
launch attempt. After all asks are answered, the queue validates and
activates the ticket. A ticket that cannot activate keeps its remaining asks.
After a launch the drain restarts at the oldest blocked ticket.

## Budget, agent, scope, summary

`--max-tasks` counts launch attempts across sweep, drain, and selection; a
`skipped-*` reclassification at the exact reread consumes nothing, a real
attempt counts even if it fails. `--agent` must be configured and applies to
draft interviews plus each task's first launched step only. `DIR` scopes to
`tasks/<DIR>/` like `coga status <dir>`; an unknown directory fails loud.

The summary counts launched, drained, completed, canceled, blocked,
skipped-human-gate, skipped-unresolved-blocker, skipped-unlaunchable, and
failed, one row per task; one notification line follows. A failed start has a row naming the task. Any `failed` row exits 1; usage errors
exit 2.

## Editable implementation

The packaged `bootstrap/megalaunch/ticket.md` and sibling `ticket.py` select
`coga_edge.megalaunch`. The complete module owns picker, persistence, filters,
service-order selection, dependency policy, budgets, stop classification and
summary. It is a stateless script invocation, creating no tracking task or
agent for itself. Its child steps may run a script or an agent.

[Script tickets](../script-tickets/SKILL.md#stateless-command-help-and-interrupts)
owns help, argv and parent interrupt handling; framing remains on stderr.
Aliases that previously targeted the built-in `megalaunch` must instead target
`launch bootstrap/megalaunch --` with their queue arguments appended.
Full local forks and upgrade behavior: [edge code](../edge-code/SKILL.md).
