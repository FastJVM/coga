# Relay — design decisions (M1)

Resolves the "must resolve before building" items flagged in `relay-spec-updated (2).md`.

---

## `relay create` — CLI + behavior

### CLI

```
relay create [OPTIONS]

Options
  --project TEXT            Project name from relay.toml. Required unless --check-recurring.
  --title TEXT              Human-readable title. Required unless --check-recurring.
  --workflow TEXT           Workflow name (e.g. code/with-review). Optional.
  --context TEXT            Context ref (e.g. email/payment-flow). Repeatable. Optional.
  --mode [interactive|auto|script]
                            Default: interactive.
  --owner TEXT              Default: current user from relay.local.toml.
  --assignee TEXT           Default: owner.
  --watcher TEXT            Additional watcher. Repeatable.
  --status TEXT             Default: project's default_status from relay.toml.
  --check-recurring         Instead of creating a new task, scan recurring templates and create any due tasks.
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

### Authoring lives in a skill, not the CLI

`relay create` is intentionally mechanical — it scaffolds the directory and writes whatever frontmatter the caller passes. The judgment about *which* workflow / contexts / assignee fit is in the `meta/create` skill (`relay-os/skills/meta/create/SKILL.md`). A human invokes that skill ("make me a task for X"), the skill interviews, calls `relay create` to scaffold, then edits the ticket frontmatter to fill in the rest.

There's no `--suggest` flag. If you want the authoring flow, run the skill. If you just want bytes on disk, call `relay create` directly with the flags above.

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

## Lock lifecycle

### Acquisition

- `relay launch` acquires `task.lock` at start. Writes `holder: <assignee>` and `acquired: <ISO-8601 UTC>`.
- If the lock exists, error with holder + age. `--force` overrides (prints a warning).
- `relay create`, `relay step`, `relay feed`, `relay panic` do **not** acquire the lock. They're short writes; the one-task-one-worker invariant and the running `relay launch` are sufficient serialization for the POC.

### Release

Three paths, all of which release:

1. **Normal exit** — `relay launch` installs a try/finally and signal handlers (SIGINT, SIGTERM) that delete `task.lock` on exit. Covers interactive Ctrl+C, auto run completion, script exit.
2. **Terminal step** — `relay step` on the last step releases as a safety net (status flipping to `done` implies nothing else should hold the lock).
3. **Panic** — `relay panic` releases. The agent is stopping; holding the lock blocks a human relaunch.

### Script mode

Acquires the lock. Same one-task-one-worker invariant applies — a long-running script must not overlap with another process touching the task dir.

### Stale detection

POC threshold: **24 hours**. Any lock with `acquired` older than 24h is flagged by the dream/drift validation script. Humans clear stale locks with `--force` on relaunch or by deleting the file. No automatic clearing.

### Lock file format

```
holder: claude1
acquired: 2025-01-14T10:32:00Z
```

Two keys, newline-separated. Parsed leniently (strip whitespace).

---

## Scope notes for the POC build

- Full Slack integration: webhook POST is implemented; offline/test mode falls back to stdout when no webhook is configured.
- `meta/create` and `meta/dream` skills ship with SKILL.md content and templates, but their actual agent flows are exercised manually during M7 smoke testing — we don't write automated tests for LLM behavior.
- `status` starts scoped to "one project per invocation"; cross-project scan lands in M3 if trivial, otherwise deferred.
