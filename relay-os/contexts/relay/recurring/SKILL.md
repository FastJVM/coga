---
name: relay/recurring
description: How Relay's recurring task system works — recurring tasks as ticket-format directories under relay-os/recurring/, the scaffold contract, period-task naming, and where last-run state persists. Attach to any ticket that adds or changes a recurring task.
---

# Recurring tasks

Recurring tasks are machine-authored jobs that re-scaffold on a schedule.
Each one re-runs every period; `relay recurring` turns due ones into real
per-period tasks.

## A recurring task is a ticket-format directory

A recurring task lives under `relay-os/recurring/<name>/` and has the same
shape as any task directory:

- `ticket.md` — YAML frontmatter (`schedule`, `mode`, `title`, …) plus the
  run body. This is the recurring task's definition.
- `blackboard.md` — **persists across every run.** This is where a recurring
  task stores last-run state.
- `log.md` — append-only run history; `relay recurring` adds a line each time
  it scaffolds a period task.

A directory whose name starts with `_` (`_template/`, `_rem/`) is inert — the
scanner skips it. That is how the starter templates ship without firing.

- `relay recurring` (bare) — scans every recurring task, get-or-creates the
  current period's task for each, and launches the ones still `active` or
  orphaned `in_progress`. **Launch order is phased, not alphabetical:** the
  cleanup template — Dream, the recurring janitor (see below) — is sorted
  **last** so its retro pass acts on the period tickets the *same* sweep just
  drove to `done`, instead of trailing them by a full sweep. Among the
  non-cleanup templates the existing order holds — orphaned `in_progress`
  resumes first, then fresh launches, each most-overdue first — and a resuming
  Dream orphan still sorts last (cleanup-after-the-rest wins for the janitor
  itself). Run from `scripts/cron.sh`. A current-period task
  left `in_progress` by a sweep whose supervisor died mid-run (laptop sleep,
  SSH drop) is **relaunched and resumed from its current step**, not skipped:
  `relay launch` re-composes it from `step:`. If an interactive launch returns
  unfinished, the sweep pauses it before continuing, so a frozen `in_progress`
  period task can still mean "dead run's orphan" rather than "human parked it".
  `done` (finished work) and `paused` (a human parked it) stay skipped. A
  *prior*-period stuck task is the human's problem in `relay status` — it does
  not block the new period's scaffold. If a non-interactive launched task
  returns still unfinished, the sweep stops before the next due task. Before
  scaffolding anything, the sweep also reaps leftover `*-dbg-*` debug scratch
  from a crashed `relay recurring --all` run — debug runs never commit task
  state, so this is a plain delete; it is the disposable-run analogue of the
  orphan-resume above.
- `relay recurring launch <name>` — scaffolds one named recurring task now,
  ignoring its schedule. `<name>` is the directory name.

`ticket.md` frontmatter fields:

- `schedule` — a 5-field cron string. **Required**; a recurring task without
  it (or without `ticket.md`) is skipped with a stderr warning and an entry
  in the run's Slack summary.
- `mode` — `script`, `auto`, or `interactive`. Defaults to `auto`.
- `title` — the scaffolded period task's title (else the humanized name).
- `workflow` — optional. A workflow-less recurring task runs its body
  directly as the prompt; Dream is the canonical example.
- `owner`, `assignee`, `watchers`, `contexts` — passed through to the
  scaffolded period task.

## Last-run state lives in the recurring task's blackboard

Each scheduled firing scaffolds a **fresh** per-period task under
`relay-os/tasks/recurring-<name>-<period_key>/`, with its own fresh blackboard. That
per-period blackboard does **not** carry over — it is gone next period.

So a recurring task that needs continuity between runs (a last-processed
commit SHA, a high-water mark, a cursor) keeps that state in **its own**
blackboard: `relay-os/recurring/<name>/blackboard.md`.

When designing a recurring task that carries cross-run state, name in the
body *which* keys it persists (e.g. `last_commit`, a cursor section). You
do **not** need to re-teach the launched run *where* state lives — the
scaffolder auto-attaches the `relay/period-task` context to every period
task, which carries that rule.

## The scaffold contract

- **Period task slug** is `recurring-<name>-<period_key>`. The `recurring-`
  prefix is the identity marker (`_RECURRING_PREFIX` in
  `src/relay/recurring.py`) that lets the scaffolder find a template's live
  task. `period_key` buckets the firing: hourly → `YYYY-MM-DD-HH`, daily →
  `YYYY-MM-DD`, weekly → `YYYY-Www`, monthly → `YYYY-MM`. Scaffolding is
  idempotent within a period: two runs in the same period converge on one
  period task.
- **The recurring template's `log.md` is the period ledger.** Bare
  `relay recurring` reads it before scaffolding: a period whose log already
  records a `scaffolded <slug>` line and whose task directory is now gone
  (a later Dream run deletes the done period ticket — see "Dream is the
  recurring janitor" below; a human `relay delete` is the other case) has been
  handled — it is not re-scaffolded and not re-launched. The on-demand
  `relay recurring launch <name>` (and aliases like `relay dream`) bypass this
  check: it's the explicit override.
- Period tasks scaffold **straight to `status: active`** — ready jobs, not
  drafts to triage. (A workflow-less one could not otherwise be activated:
  `relay mark active` refuses workflow-less tickets.)
- `assignee` defaults to the repo's configured **default agent** when the
  recurring task omits it — never the human `owner`, which `relay launch`
  cannot resolve to an agent type.
- The period task's `## Description` is taken from the `ticket.md` body's
  `## Description` section: everything from that heading to the next
  top-level `## ` heading. **Convention:** keep every other heading in the
  body at `###` so the whole run instruction lands in the description.

## Dream is the recurring janitor

A finished period task is **not** deleted by the recurring command — it sits on
disk as an ordinary `status: done` ticket. The single deleter of done recurring
period tickets is **Dream**: its Phase 4 retro pass (`retro/done-ticket`)
processes every eligible done ticket, and a `recurring-<name>-<period>` ticket
is eligible like any other. Period tickets carry nothing durable — their output
is the notification post or PR they already produced — so Retro extracts no new
knowledge and **direct-deletes** them via `relay delete <slug>` (working-tree
`git rm` plus a `Ticket: <slug> — deleted` commit), with no PR and no marker.
The template's `log.md` period-ledger line is left untouched, so a completed
period is not re-scaffolded; deletion is idempotent (a ticket whose directory
is already gone is never a candidate).

Each Dream run is itself a `recurring-dream-<period>` ticket. Dream does **not**
delete itself mid-run: it marks itself `done` and stops, and the **next** Dream
run's retro pass cleans up the previous one — exactly like every other done
recurring period ticket. For real done recurring period tickets, there is no
self-delete and no recurring-command deletion; Dream-acting-on-`done` is the
only cleanup path. `relay recurring --all` debug scratch is still reaped by the
recurring command until the sibling redesign removes that debug path.

## Gotchas

- A stray top-level `## ` heading anywhere in the body — including inside a
  fenced code block — truncates the extracted description there. Indent
  example blocks or use `###`.
- Do not store last-run state in the per-period task's blackboard under
  `relay-os/tasks/` — it is fresh each period. Use the recurring task's own
  `relay-os/recurring/<name>/blackboard.md`.

## What this context does NOT cover

The cron wiring in `scripts/cron.sh`, how to write a run's skill or body
logic, and notification posting mechanics (see `relay/sync`). Implementation lives
in `src/relay/recurring.py`.
