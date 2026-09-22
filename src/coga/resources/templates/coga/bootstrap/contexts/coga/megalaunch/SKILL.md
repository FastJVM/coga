---
name: coga/megalaunch
description: How `coga megalaunch` selects, orders, gates, and runs queued work — the owner-scoped sweep, the `--pick`/`--relaunch` staged selection, drain order, the post-sweep dependency drain, `--max-tasks` accounting, `--agent`, and the run summary.
---

# Coga megalaunch

`coga megalaunch [DIR] [--pick | --relaunch] [--max-tasks N] [--agent <type>]`
runs launchable work one task at a time through the shared engine in
`src/coga/megalaunch.py`. It is on-demand only: no recurring template ships
for it. `pick` is the default alias for `megalaunch --pick`. For one task,
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

Megalaunch has no deterministic phase: it never runs a ticket's `ticket.py`
([script tickets](../script-tickets/SKILL.md)); each step is an agent
session composed directly.

## Bare sweep

Silently ignores tickets whose `owner` is not `current_user` (owner-less
included) and every status but `active`, `in_progress`, and `blocked`.
Blocked tickets and ones with open asks report `skipped-unresolved-blocker`;
a missing current step or an owner/unrouted step reports
`skipped-human-gate`. `in_progress` work resumes like `coga launch`. The queue
scan is only a hint: each launch rereads exact bytes and reapplies the owner,
status, blocker, and current-step gates to them. A task that vanished since
the scan is skipped without a row.

## Explicit selection

`--pick` offers every non-terminal task of any owner with no launchability
filter, displayed like default `coga status` (last updated first). Nothing
starts checked; arrows or `j`/`k` move, Space toggles, `a`/`n` all/none,
Enter confirms, `q`/Esc quits. The confirmed set is saved to
`.coga/megalaunch-selection.json` (machine-local). `--relaunch` replays it,
warning about and skipping vanished tasks; it cannot combine with `--pick`
or `DIR`. A selection runs in three stages:

1. **Prepare** — if the pick has drafts, one `[Y/n]` prompt offers the guided
   `coga ticket` interview for each; an authoring failure leaves the draft.
2. **Check** — draft/paused/blocked picks are validated against their
   prospective `active` view without writing; failures report now.
3. **Launch** — each pick is reread and reclassified when reached, then
   preflighted, and only then activated. A pick not reached under
   `--max-tasks` stays untouched.

A picked blocked ticket with open asks resumes with the resolve-or-re-block
preamble and returns to `blocked` if the ask stays open; an ask-less one is
`skipped-unlaunchable`, as are terminal and unactivatable picks. A human
step is `skipped-human-gate` even under `--agent`. Explicit selections never
run the dependency drain, so they cannot expand into unpicked work.

## Order

Oldest first by each ref's first `coga/log.md` line (committed, so clones
agree). A sub-directory with at least one `<n>-` task runs as one block
anchored at its oldest task, numbered tasks by number (`02-` == `2-`, `10-`
after `9-`), then unnumbered siblings by age. Top-level tasks never form a
block; `2fa-login` is not numbered. `coga status --order-by created` shows the
same order (`service_order.service_order`); a selection filters it, so pick
order never sets run order. `coga validate` warns `duplicate-task-number`.

## Dependency drain

After a bare sweep, `_drain_satisfied_blockers` re-lists the operator's
blocked tickets in the same scope. An open blocker whose text contains a
complete path-qualified task ref is satisfied when that task is `done` or was
seen earlier in the run and has since disappeared. The ticket is recaptured
as exact bytes, its activation prepared, and activation plus an automatic
blocker answer publish as one exact mutation before the launch claim; the
prompt therefore never carries the blocker preamble. An unactivatable ticket
keeps its ask and stays `blocked`; a lost publication restores it, an
uncertain one retains evidence. Each task drains at most once per run; after
any actual launch the walk restarts from the oldest blocked ticket, and a
pass without a launch ends it.

## Budget, agent, scope, summary

`--max-tasks` counts launch attempts across sweep, drain, and selection; a
`skipped-*` reclassification at the exact reread consumes nothing, a real
attempt counts even if it fails. `--agent` must be configured and applies to
draft interviews plus each task's first launched step only. `DIR` scopes to
`tasks/<DIR>/` like `coga status <dir>`; an unknown directory fails loud.

The summary counts launched, drained, completed, canceled, blocked,
skipped-human-gate, skipped-unresolved-blocker, skipped-unlaunchable, and
failed, one row per task; one notification line follows. Any `failed` row
exits 1; usage errors exit 2. Claims and recovery:
[launch claims](../internals/launch-claims/SKILL.md).
