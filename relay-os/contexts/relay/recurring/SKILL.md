---
name: relay/recurring
description: How Relay's recurring task system works — recurring tasks as ticket-format directories under relay-os/recurring/, the creation contract, period-task naming, and where last-run state persists. Attach to any ticket that adds or changes a recurring task.
---

# Recurring tasks

Recurring tasks are machine-authored jobs that re-create on a schedule.
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
  it creates a period task.

A directory whose name starts with `_` (`_template/`, `_rem/`) is inert — the
scanner skips it. That is how the starter templates ship without firing.

- `relay recurring` (bare) — scans every recurring task, get-or-creates the
  stable instantiated task at `relay-os/tasks/recurring/<name>/`, records the
  current period as `last_serviced_period` in the template blackboard, and
  launches the ones still `active` or orphaned `in_progress`. **Launch order
  is phased, not alphabetical:** the
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
  stale leftover under `tasks/recurring/<name>/` is resumed before any new
  period work for that template; there is only one instantiated path per
  template. If a non-interactive launched task
  returns still unfinished, the sweep stops before the next due task. Before
  creating anything, the sweep also reaps leftover `*-dbg-*` debug scratch
  from a crashed `relay recurring --all` run — debug runs never commit task
  state, so this is a plain delete; it is the disposable-run analogue of the
  orphan-resume above.
- `relay recurring launch <name>` — creates one named recurring task now,
  ignoring its schedule. `<name>` is the directory name.

`ticket.md` frontmatter fields:

- `schedule` — a 5-field cron string. **Required**; a recurring task without
  it (or without `ticket.md`) is skipped with a stderr warning and an entry
  in the run's Slack summary.
- `mode` — `script`, `auto`, or `interactive`. Defaults to `auto`.
- `title` — the created period task's title (else the humanized name).
- `workflow` — optional. A template that names none creates with the
  one-step `direct/body` workflow, which runs the ticket body's ordered
  phases directly as the prompt; Dream is the canonical example. (The task is
  still workflow-carrying and bumpable — `direct/body` is the workflow.)
- `owner`, `assignee`, `watchers`, `contexts` — passed through to the
  created period task.

## Last-run state lives in the recurring task's blackboard

Each scheduled firing uses the stable instantiated task path
`relay-os/tasks/recurring/<name>/`, with its own fresh blackboard. That task
directory is deleted after completion and recreated later, so the run
blackboard does **not** carry over.

So a recurring task that needs continuity between runs (a last-processed
commit SHA, a cursor, a posted/skipped flag) keeps that state in **its own**
blackboard: `relay-os/recurring/<name>/blackboard.md`. The creator also
keeps the schedule high-water mark there as `last_serviced_period:
<period_key>`, overwriting the single line as periods advance.

When designing a recurring task that carries cross-run state, name in the
body *which* keys it persists (e.g. `last_commit`, a cursor section). You
do **not** need to re-teach the launched run *where* state lives — the
creator auto-attaches the `relay/period-task` context to every period
task, which carries that rule.

## The creation contract

- **Instantiated task ref** is `recurring/<name>`, backed by
  `relay-os/tasks/recurring/<name>/`. The `recurring/` task group is the
  identity marker. The period is not in the slug.
- **`last_serviced_period` in the template blackboard is the period
  high-water mark.** The period key buckets the firing: hourly →
  `YYYY-MM-DD-HH`, daily → `YYYY-MM-DD`, weekly → `YYYY-Www`, monthly →
  `YYYY-MM`. Bare `relay recurring` reads
  `relay-os/recurring/<name>/blackboard.md` before creating: if
  `last_serviced_period >= current period_key` and no instantiated task dir
  remains, that period has been handled — it is not re-created and not
  re-launched. The on-demand `relay recurring launch <name>` (and aliases like
  `relay dream`) bypass this skip: it's the explicit override.
- **The recurring template's `log.md` is append-only history.** The creator
  still appends a human-readable period line, but dedup does not depend on
  parsing the log. Logs are never composed into prompts, so history can grow
  without bloating the next run.
- Period tasks create **straight to `status: active`** — ready jobs, not
  drafts to triage. Because every active task must carry a workflow, a
  template that declares none creates with `direct/body` (it would otherwise
  be un-activatable and `relay validate` would flag it as a stuck task).
- `assignee` defaults to the repo's configured **default agent** when the
  recurring task omits it — never the human `owner`, which `relay launch`
  cannot resolve to an agent type.
- The period task's `## Description` is taken from the `ticket.md` body's
  `## Description` section: everything from that heading to the next
  top-level `## ` heading. **Convention:** keep every other heading in the
  body at `###` so the whole run instruction lands in the description.

## Dream is the recurring janitor

A finished period task is **not** deleted by the recurring command — it sits on
disk as an ordinary `status: done` ticket at `tasks/recurring/<name>/`. The
single deleter of done recurring period tickets is **Dream**: its Phase 4 retro
pass (`retro/done-ticket`) processes every eligible done ticket, and a done
`recurring/<name>` task is eligible like any other. Period tasks carry nothing
durable — their output is the notification post or PR they already produced —
so Retro extracts no new knowledge and **direct-deletes** them via `relay
delete recurring/<name>` (working-tree `git rm` plus a `Ticket:
recurring/<name> — deleted` commit), with no PR and no marker. The template's
`last_serviced_period` line is left untouched, so a completed period is not
re-created; deletion is idempotent (a ticket whose directory is already gone
is never a candidate).

Each Dream run is itself the `recurring/dream` task. Dream does **not** delete
itself mid-run: it marks itself `done` and stops, and the **next** Dream run's
retro pass cleans up the previous done Dream task — exactly like every other
done recurring period task. For real done recurring period tickets, there is no
self-delete and no recurring-command deletion; Dream-acting-on-`done` is the
only cleanup path. `relay recurring --all` debug scratch is still reaped by the
recurring command until the sibling redesign removes that debug path.

## Gotchas

- A stray top-level `## ` heading anywhere in the body — including inside a
  fenced code block — truncates the extracted description there. Indent
  example blocks or use `###`.
- Do not store last-run state in the instantiated task's blackboard under
  `relay-os/tasks/recurring/<name>/` — it is fresh for one run and deleted on
  cleanup. Use the recurring task's own
  `relay-os/recurring/<name>/blackboard.md`.

## What this context does NOT cover

The cron wiring in `scripts/cron.sh`, how to write a run's skill or body
logic, and notification posting mechanics (see `relay/sync`). Implementation lives
in `src/relay/recurring.py`.
