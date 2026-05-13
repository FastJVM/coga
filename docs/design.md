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

`relay create` is intentionally mechanical — it scaffolds the directory and writes whatever frontmatter the caller passes. The judgment about *which* workflow / contexts / assignee fit is in the `bootstrap/ticket` skill (`relay-os/skills/bootstrap/ticket/SKILL.md`). A human invokes that skill ("make me a task for X"), the skill interviews, calls `relay create` to scaffold, then edits the ticket frontmatter to fill in the rest.

The creation skill treats `contexts:` as launch-prompt payload, not labels. It
should attach only context bodies that must be inlined for the future task run.
When one fact from a broad context is enough, that fact belongs in the ticket's
inline `## Context` body; repeated narrow needs should become smaller focused
contexts. Reusable process knowledge stays in workflow step `skill:` refs.

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

## Status is the signal

There is no filesystem mutex. The ticket's `status` field is the only signal that a task is in flight.

- `relay launch` requires `status: active` and refuses anything else, pointing the operator at `relay mark active <slug>`. It does not flip status itself.
- Status transitions are owned by `relay mark active | paused | done` exclusively. The control plane (`status`) and the data plane (`step`) never share a writer.
- Bootstrap shims are stateless and exempt — they are re-entry points, not units of work.
- Dream's `validate-drift` skill flags tasks stuck on `active` with no recent log activity. Recovery is human-initiated.

We tried a `task.lock` file-existence mutex first. It cost a module of acquisition/release logic, `--force` flags on `launch` and `delete`, orphan-cleanup machinery, and two "don't touch task.lock" lines in the base prompt — to guarantee something (two concurrent workers on the same slug) that almost never happened under one-task-one-worker. The failure mode without the mutex is two divergent blackboard edits and two PR branches; both are visible in git and recoverable by hand. Dropping the lock simplified six call sites and removed all of the above.

---

## Scope notes for the POC build

- Full Slack integration: webhook POST is implemented; offline/test mode falls back to stdout when no webhook is configured.
- `bootstrap/ticket` ships with SKILL.md content and templates, while `relay dream` creates an ad-hoc Relay cleanup task whose body scans tickets and runs fixed housekeeping skills. REM is the opt-in repo/user-specific recurring-maintenance template. Their actual agent flows are exercised manually during M7 smoke testing — we don't write automated tests for LLM behavior.
- `status` starts scoped to "one project per invocation"; cross-project scan lands in M3 if trivial, otherwise deferred.
