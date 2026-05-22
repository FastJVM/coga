---
name: relay/recurring
description: How Relay's recurring task system works — templates under relay-os/recurring/, the scaffold contract, period-task naming, and the body-as-instruction convention. Attach to any ticket that adds or changes a recurring template.
---

# Recurring tasks

Recurring tasks are machine-authored jobs that re-scaffold on a schedule.
Each one is a template file; `relay recurring` turns due templates into
real tasks.

## How templates run

Templates live in `relay-os/recurring/*.md`. A file whose name starts with
`_` (`_template.md`, `_rem.md`) is inert — the scanner skips it. That is how
the starter template ships without ever firing.

- `relay recurring check` — scans every template, get-or-creates the current
  period's task for each, and launches the ones still `active`. Run from
  `scripts/cron.sh`.
- `relay recurring scaffold <name>` — scaffolds one named template now,
  ignoring its schedule. `<name>` is the file stem.

Each template is YAML frontmatter + a markdown body. Frontmatter fields:

- `schedule` — a 5-field cron string. **Required**; a template without it is
  skipped with a stderr warning and an entry in the run's Slack summary (one
  bad template never blocks the rest).
- `mode` — `script`, `auto`, or `interactive`. Defaults to `auto`.
- `title` — the scaffolded task's title (else the humanized file stem).
- `workflow` — optional. A workflow-less recurring task runs its body
  directly as the prompt; Dream is the canonical example.
- `owner`, `assignee`, `watchers`, `contexts` — passed through to the
  scaffolded task.

## The scaffold contract

- **Task slug** is `<template-stem>-<period_key>`. `period_key` buckets the
  firing: hourly → `YYYY-MM-DD-HH`, daily → `YYYY-MM-DD`, weekly →
  `YYYY-Www`, monthly → `YYYY-MM`. Scaffolding is idempotent within a
  period: two runs in the same period converge on one task directory.
- Recurring tasks scaffold **straight to `status: active`** — they are ready
  jobs, not drafts to triage. (A workflow-less one could not otherwise be
  activated: `relay mark active` refuses workflow-less tickets.)
- `assignee` defaults to the repo's configured **default agent** when the
  template omits it — never the human `owner`, which `relay launch` cannot
  resolve to an agent type.
- The scaffolded task's `## Description` is taken from the template body's
  `## Description` section: everything from that heading to the next
  top-level `## ` heading. **Convention:** keep every other heading in the
  body at `###` so the whole run instruction lands in the description.
  Dream and `relay-dev-update` both rely on this.

## Gotchas

- **No built-in cross-period state.** Each period gets a fresh task with a
  fresh blackboard. A recurring task that needs continuity (a high-water
  mark, a last-processed SHA) must locate its predecessor's task directory
  (`<stem>-<previous period_key>`) and read it.
- A stray top-level `## ` heading anywhere in the body — including inside a
  fenced code block — truncates the extracted description at that point.
  Indent example blocks or use `###`.

## What this context does NOT cover

The cron wiring in `scripts/cron.sh`, how to write a run's skill or body
logic, and Slack posting mechanics (see `relay/sync`). Implementation lives
in `src/relay/recurring.py`.
