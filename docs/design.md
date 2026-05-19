# Relay — design decisions (M1)

Resolves the "must resolve before building" items flagged in `relay-spec-updated (2).md`.

---

## `relay draft` / `relay ticket` — CLI + behavior

### CLI

```
relay draft "<title>" [--mode interactive|auto|script]
relay ticket [<title-or-slug>] [--agent <nickname>]

Options
  --mode [interactive|auto|script]
                            Draft mode. Default: interactive.
  --agent TEXT              Ticket-authoring agent nickname.
```

### Frontmatter generation

**Set automatically (not from CLI args):**

- `workflow` — full frozen snapshot (name + steps with per-step skill refs) resolved from `--workflow`. Workflow file is read once and baked into the ticket.
- `step` — `1 (<first-step-name>)` if `--workflow` was provided, else the field is omitted.
- No `id` field. The task directory path is the unique identifier.

**From CLI args (all optional in frontmatter):**

- `title`, `status`, `mode`, `owner`, `assignee`, `watchers`, `contexts`

### Duplicate context refs

Deduplicated silently, order preserved (first occurrence wins). If any context ref doesn't resolve on disk, the command errors and lists every unresolved ref. No task is created.

### Raw scaffolding and guided authoring are separate

`relay draft` is intentionally mechanical — it scaffolds the directory and
writes the raw default frontmatter. `relay create` remains a compatibility
spelling for that raw operation.

The judgment about *which* workflow / contexts / assignee fit is in the
`bootstrap/ticket` skill (`relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md`,
unless shadowed by a local skill under `relay-os/skills/`). A
human invokes that skill through `relay ticket`: with no argument it asks for
a title, with a title it drafts then edits, and with an existing draft/active
slug it edits that ticket in place. It refuses `in_progress` and `done`
tickets by default.

The creation skill treats `contexts:` as launch-prompt payload, not labels. It
should attach only context bodies that must be inlined for the future task run.
When one fact from a broad context is enough, that fact belongs in the ticket's
inline `## Context` body; repeated narrow needs should become smaller focused
contexts. Reusable process knowledge stays in workflow step `skill:` refs.

There's no `--suggest` flag. If you want the authoring flow, run `relay
ticket`. If you just want bytes on disk, call `relay draft`.

### Skills at creation time

Confirmed: skills are **not** composed into the prompt at creation. They are loaded at launch time for the current workflow step. Ticket frontmatter never references skills. The workflow snapshot carries the per-step `skill:` references forward.

### `--check-recurring`

Mechanism: naming convention on created tasks, not `last_run` in the template.

1. Walk `relay-os/recurring/*.md`.
2. For each template, parse cron-style `schedule` field (5 fields).
3. Compute the most recent scheduled firing time at or before now → a "period key":
   - Daily schedules → `YYYY-MM-DD`
   - Hourly → `YYYY-MM-DD-HH`
   - Weekly → `YYYY-WW` (ISO week)
   - Monthly → `YYYY-MM`
   - Fallback / other → the raw datetime `YYYYMMDDTHHMM`
4. Expected task slug: `<template-name>-<period-key>` in the template's `project`.
5. If no task exists with that slug, create it using the template's frontmatter (mode, workflow, assignee, owner, contexts, description).

This is idempotent — running `--check-recurring` twice inside the same period is a no-op.

"Due" is implicit in the period-key check: if the current period's task doesn't exist yet, it's due.

---

## Status is the signal

There is no filesystem mutex. The ticket's `status` field is the only signal that a task is in flight.

- `draft` means unapproved, `active` means approved/queued, and `in_progress` means launched work.
- `relay launch` accepts `status: active` or `status: in_progress`. Launching active work marks it `in_progress`; launching already-in-progress work resumes it.
- `relay bump` advances only `in_progress` workflow tasks.
- Bootstrap shims are stateless and exempt — they are re-entry points, not units of work.
- Dream's `validate-drift` skill flags tasks stuck in `in_progress` with no recent log activity. Recovery is human-initiated.

We tried a `task.lock` file-existence mutex first. It cost a module of acquisition/release logic, `--force` flags on `launch` and `delete`, orphan-cleanup machinery, and two "don't touch task.lock" lines in the base prompt — to guarantee something (two concurrent workers on the same slug) that almost never happened under one-task-one-worker. The failure mode without the mutex is two divergent blackboard edits and two PR branches; both are visible in git and recoverable by hand. Dropping the lock simplified six call sites and removed all of the above.

---

## Scope notes for the POC build

- Full Slack integration: webhook POST is implemented; offline/test mode falls back to stdout when no webhook is configured.
- `bootstrap/ticket` ships with SKILL.md content and templates, while `relay dream` creates an ad-hoc Relay cleanup task whose body scans tickets and runs fixed housekeeping skills. REM is the opt-in repo/user-specific recurring-maintenance template. Their actual agent flows are exercised manually during M7 smoke testing — we don't write automated tests for LLM behavior.
- `status` starts scoped to "one project per invocation"; cross-project scan lands in M3 if trivial, otherwise deferred.
