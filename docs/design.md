# Coga — design decisions (M1)

Resolves the "must resolve before building" items flagged in `coga-spec-updated (2).md`.

---

## `coga create` / `coga ticket` — CLI + behavior

### CLI

```
coga create "<title>" [--mode interactive|auto|script]
coga ticket [<title-or-slug>] [--agent <type>]

Options
  --mode [interactive|auto|script]
                            Draft mode. Default: interactive.
  --agent TEXT              Ticket-authoring agent type (e.g. claude, codex).
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

### Raw creating and guided authoring are separate

`coga create` is intentionally mechanical — it creates the directory and
writes the raw default frontmatter.

The judgment about *which* workflow / contexts / assignee fit is in the
`bootstrap/ticket` skill (`coga-os/bootstrap/skills/bootstrap/ticket/SKILL.md`,
unless shadowed by a local skill under `coga-os/skills/`). A
human invokes that skill through `coga ticket`: with no argument it asks for
a title, with a title it drafts then edits, and with an existing slug it edits
that ticket in place at any lifecycle status. Editing leaves the status
unchanged; revising an `in_progress` or `done` ticket prints a heads-up first
but is not refused.

The creation skill treats `contexts:` as launch-prompt payload, not labels. It
should attach only context bodies that must be inlined for the future task run.
When one fact from a broad context is enough, that fact belongs in the ticket's
inline `## Context` body; repeated narrow needs should become smaller focused
contexts. Reusable process knowledge stays in workflow step `skill:` refs.

There's no `--suggest` flag. If you want the authoring flow, run `coga
ticket`. If you just want bytes on disk, call `coga create`.

### Skills at creation time

Confirmed: skills are **not** composed into the prompt at creation. They are loaded at launch time for the current workflow step. Ticket frontmatter never references skills. The workflow snapshot carries the per-step `skill:` references forward.

### `coga recurring`

Mechanism: naming convention on created tasks, not `last_run` in the template.

1. Walk `coga-os/recurring/<name>/ticket.md` template directories. Bare
   `recurring/<name>.md` files are a legacy shape and the scanner errors
   on them.
2. For each template, parse the cron-style `schedule` field (5 fields).
3. Compute the most recent scheduled firing time at or before now → a "period key":
   - Daily schedules → `YYYY-MM-DD`
   - Hourly → `YYYY-MM-DD-HH`
   - Weekly → `YYYY-WW` (ISO week)
   - Monthly → `YYYY-MM`
   - Fallback / other → the raw datetime `YYYYMMDDTHHMM`
4. Expected task ref: `recurring/<template-name>`, backed by
   `tasks/recurring/<template-name>/`. The `recurring/` group is the identity
   marker; the period key lives in the template blackboard.
5. **One live task per template.** Look for the generated grouped task
   `recurring/<template-name>` if it is `active` or `in_progress`. If it exists,
   it is *the* live run: launch/resume it (an `in_progress` orphan is resumed
   from its current step) and do **not** create a duplicate.
6. Only when none is live, consider the current period: if
   `last_serviced_period >= current period_key` in the blackboard region of
   `coga-os/recurring/<name>/ticket.md` and the task dir is gone, it's
   handled — skip. Otherwise create it using the template's frontmatter (mode,
   workflow, assignee, owner, contexts, description), write the high-water
   mark, and append human-readable history to the repo-global `coga-os/log.md`
   (tagged `recurring/<name>`).

This is idempotent — running `coga recurring` twice inside the same period is a no-op.
Across periods, a template does not start a new run while an older period run
is still `active`/`in_progress`: that stuck run is resumed first and **defers**
the next period until it reaches `done`/`paused`.

"Due" is implicit: a template is due when no live task exists for it and the
current period hasn't been handled. Launch order is orphaned `in_progress`
resumes first, then fresh launches, each most-overdue first.

---

## Status is the signal

There is no filesystem mutex. The ticket's `status` field is the only signal that a task is in flight.

- `draft` means unapproved, `active` means approved/queued, and `in_progress` means launched work.
- `coga launch` accepts `status: active` or `status: in_progress`. Launching active work marks it `in_progress`; launching already-in-progress work resumes it.
- `coga bump` moves only `in_progress` workflow tasks.
- Bootstrap tickets are stateless and exempt — they are re-entry points, not units of work.
- Dream's `validate-drift` skill flags tasks stuck in `in_progress` with no recent log activity. Recovery is human-initiated.

We tried a `task.lock` file-existence mutex first. It cost a module of acquisition/release logic, `--force` flags on `launch` and `delete`, orphan-cleanup machinery, and two "don't touch task.lock" lines in the base prompt — to guarantee something (two concurrent workers on the same slug) that almost never happened under one-task-one-worker. The failure mode without the mutex is two divergent blackboard edits and two PR branches; both are visible in git and recoverable by hand. Dropping the lock simplified six call sites and removed all of the above.

---

## Scope notes for the POC build

- Full Slack integration: webhook POST is implemented; offline/test mode falls back to stdout when no webhook is configured.
- `bootstrap/ticket` ships with SKILL.md content and templates, while Dream is a recurring task template (`coga-os/recurring/dream/`) whose body scans tickets and runs fixed housekeeping skills; `coga dream` is an alias that creates and launches it on demand. REM is the opt-in repo/user-specific recurring-maintenance template. Their actual agent flows are exercised manually during M7 smoke testing — we don't write automated tests for LLM behavior.
- `status` starts scoped to "one project per invocation"; cross-project scan lands in M3 if trivial, otherwise deferred.
