---
name: coga/recurring
description: How Coga's recurring task system works — recurring tasks as ticket-format directories under coga/recurring/, the creation contract, period-task naming, and where last-run state persists. Attach to any ticket that adds or changes a recurring task.
---

# Recurring tasks

Recurring tasks are machine-authored jobs that re-create on a schedule.
Each one re-runs every period; `coga recurring` turns due ones into real
per-period tasks.

## A recurring task is a ticket-format directory

A recurring task lives under `coga/recurring/<name>/` and has the same
shape as any task directory:

- `ticket.md` — YAML frontmatter (`schedule`, `title`, …) plus the
  run body. This is the recurring task's definition.
- the **blackboard region** (in `ticket.md`, below the
  `<!-- coga:blackboard -->` fence) — **persists across every run.** This is
  where a recurring task stores last-run state.

Append-only run history is not beside the template: `coga recurring` adds a
line to the repo-global `coga/log.md` (tagged `recurring/<name>`) each time
it creates a period task.

Templates deliberately live outside `tasks/`. Anything holding a `ticket.md`
under `coga/tasks/` *is* a task — discovered, status-carrying, launchable —
with no exceptions, and a template is none of those: it carries no `status:`,
is never launched directly, and must survive across periods. Its instances
are the opposite — ordinary tasks the scanner deletes and recreates each
period. Keeping the two in separate directories keeps the task-tree invariant
exception-free (no "unless it's a template" branch in status, validate, or
megalaunch) and makes the instance path itself the marker: the `recurring/`
prefix under `tasks/` says "machine-generated, safe to reap and regenerate",
which is what licenses the scan to replace a prior-period `done` task and
Dream's retro pass to direct-delete finished period tasks without a PR. A
hand-authored task never gets that treatment.

A directory whose name starts with `_` is inert — the scanner skips it. That
is how you park a live template without deleting it: rename `foo/` to
`_foo/`. There is no starter template directory; the whole mechanism is
"non-underscore directory under `coga/recurring/` with a `schedule:` in its
`ticket.md`", and the frontmatter shape is documented in this context (see
the example under "Extend recurring with a task-specific workflow").

- `coga recurring` (bare) — the public command head parses `--interactive`
  and `--force`, then launches the package-backed `bootstrap/recurring-scan`
  script target with those values in `COGA_RECURRING_INTERACTIVE` and
  `COGA_RECURRING_FORCE`. That target scans every recurring task,
  get-or-creates the stable instantiated task at
  `coga/tasks/recurring/<name>/`, records the current period as
  `last_serviced_period` in the template blackboard, and launches the ones
  still `active` or orphaned `in_progress`. **Launch order is phased, not
  alphabetical:** the
  cleanup template — Dream, the recurring janitor (see below) — is sorted
  **last** so its retro pass acts on the period tickets the *same* sweep just
  drove to `done`, instead of trailing them by a full sweep. Among the
  non-cleanup templates the existing order holds — orphaned `in_progress`
  resumes first, then fresh launches, each most-overdue first — and a resuming
  Dream orphan still sorts last (cleanup-after-the-rest wins for the janitor
  itself). Invoke it directly from whatever operator-owned scheduler exists
  outside Coga. A current-period task
  left `in_progress` by a sweep whose supervisor died mid-run (laptop sleep,
  SSH drop) is **relaunched and resumed from its current step**, not skipped:
  `coga launch` re-composes it from `step:`. If an interactive launch returns
  unfinished, the sweep pauses it before continuing, so a frozen `in_progress`
  period task can still mean "dead run's orphan" rather than "human parked it".
  `done` from the *current* period (finished work) and `paused` (a human
  parked it) stay skipped. A `done` run left over from a **prior** period —
  finished but never reaped by Dream's retro pass — is **deleted before a
  fresh task is created** from the current template. The new task starts
  `active` at workflow step 1 with a fresh blackboard, a re-baselined state-key
  snapshot, and an advanced `last_serviced_period`; reactivating a terminal
  task would preserve stale run instructions and residue. A live
  stale leftover under `tasks/recurring/<name>/` is resumed before any new
  period work for that template; there is only one instantiated path per
  template. If a script-launched task returns still unfinished, the sweep
  stops before the next due task.
- `coga recurring --force` — ignores schedule and status filters and attempts
  the real period task for every template, reactivating `done` and `paused`
  runs. A `canceled` task remains terminal: the runner reports a controlled
  refusal for it, continues through later templates, and exits non-zero after
  the sweep. Deleting that canceled period task is the explicit prerequisite
  for a fresh run.
- `coga recurring --all <path>` — discovers every Coga repo below an explicit
  parent directory, pruning dependency/tool-state and `_`-prefixed directory
  trees, and runs the ordinary due sweep in each configured target,
  sequentially. A missing local `user` or another intentional Coga config guard
  makes a scratch checkout an unconfigured non-target: these are omitted from
  dispatch, summarized once by count, and do not make the parent fail. Each
  selected repo runs in a fresh CLI process so its config, launch supervision,
  and end-of-command git sync stay repo-local. TOML parse errors and failures
  after dispatch are reported without preventing later repos from running; the
  parent command exits non-zero after the sweep. `--force` may be combined with
  `--all <path>` to force every template in every selected repo.
- `coga recurring launch <name>` — creates one named recurring task now,
  ignoring its schedule. `<name>` is the directory name. Unless
  `--interactive` is set, the launched REPL receives the same concrete
  `idle_timeout` / `max_session` limits the scheduled sweep would pass, so the
  in-process launch path never relies on Typer option sentinels.

`ticket.md` frontmatter fields:

- `schedule` — a 5-field cron string. **Required**; a recurring task without
  it (or without `ticket.md`) is skipped with a stderr warning and an entry
  in the run's Slack summary.
- there is no `mode` field: whether a run is a script or an agent session is
  deduced (the template's `script:`, or a script-backed workflow step 1 →
  script; else agent). Agent templates need a TTY and run under the REPL
  supervisor; script templates run deterministic code directly and are the
  right shape for unattended schedulers.
- `title` — the created period task's title (else the humanized name).
- `workflow` — optional. A template that names none creates with the
  one-step `direct/body` workflow, which runs the ticket body's ordered
  phases directly as the prompt; Dream is the canonical example. (The task is
  still workflow-carrying and bumpable — `direct/body` is the workflow.)
- `owner`, `assignee`, `watchers`, `contexts`, `secrets` — passed through to
  the created period task.
- `script` — optional ticket-owned script setting, also passed through. An
  inline script travels in the copied body; a companion script file beside the
  template is not copied into the period task, so file-backed recurring logic
  belongs in a script-backed workflow skill.

## Extend recurring with a task-specific workflow

Yes: recurring templates are not restricted to Dream or the shipped janitor
shape. At materialization time, a template may name any resolvable workflow
that an ordinary task in the repo can use and may attach any resolvable set of
contexts. There is no separate registry of recurring-capable workflows. That
is structural support, not a promise that every workflow shape can finish in a
scheduled sweep; shape the run around the dispatch constraints below.

On each firing, the recurring creator routes the template through the ordinary
task creator. That path resolves and freezes the named `workflow:`, validates
its step-skill and `contexts:` references, copies the template body into the
period task, and appends `coga/period-task` to its contexts. The resulting
`coga/tasks/recurring/<name>/` ticket uses the normal launch, per-step
assignee, script dispatch, bump, blocker, and completion machinery. A bare
scheduled sweep adds post-launch handling for unfinished runs, described
below.

To schedule a task-specific workflow:

1. Define the workflow and any skills or contexts through their ordinary Coga
   paths.
2. Create a non-underscore directory such as
   `coga/recurring/weekly-deliverability/` with a `ticket.md` — copy an
   existing template (e.g. `skill-update/`) or start from the example below.
3. Set the template's `schedule:`, explicit `workflow:`, `contexts:`, and role
   fields, then replace its `## Description` with the per-firing instructions.
4. Run `coga validate --json`, then use
   `coga recurring launch weekly-deliverability` for an explicit real run or
   `coga recurring` for the scheduled sweep.

For example:

```yaml
---
schedule: "0 9 * * 1"
title: "Weekly deliverability review"
workflow: deliverability/weekly-review
owner: nick
assignee: claude
contexts:
  - email/deliverability
  - customers/current-campaigns
---

## Description

Run the weekly deliverability review; this scheduled workflow must reach
`done` in the current launch.

<!-- coga:blackboard -->

The cross-run state for this recurring task goes here.
```

This extension seam has six important constraints:

- **One instantiated task per template.** Every firing uses the stable ref
  `recurring/<name>` at `coga/tasks/recurring/<name>/`. A still-live prior run
  is resumed before new-period work; recurring does not create overlapping
  period tickets or a backlog under different slugs.
- **The period task is fresh each firing.** Its blackboard is scratch space for
  that run and is deleted with the task. Put cursors and other cross-run state
  in the recurring template's own blackboard, optionally naming them in
  `state_keys:` so completion warns when a run forgets to advance one.
- **Script resolution is step-first.** If the current workflow step has exactly
  one script-backed skill, that skill's script runs; otherwise a ticket-level
  `script:` runs. A ticket script therefore makes every remaining non-scripted
  step dispatch as a script, but it does not override a scripted step skill.
  Avoid declaring both forms unless that precedence is intentional. The
  self-contained ticket form is `script: inline`; template companion files are
  not materialized into the period task.
- **A headless script run must finish in one step.** This limit applies whether
  the script belongs to the ticket or the first step's skill: after an entry
  script succeeds, `coga launch` advances once and returns. If another step
  remains, the bare recurring sweep sees an unfinished script task, stops
  before later templates, and leaves the run `in_progress`. Use an exactly
  one-step workflow with no `requires:` gate for an unattended recurring job.
  An attended workflow may instead start with an agent and mix later
  script-backed skill steps into the supervised agent chain.
- **A scheduled agent run must reach `done` in one launch.** When a bare
  `coga recurring` sweep gets control back from an unfinished agent launch, it
  pauses the period task before continuing. That includes an intermediate
  human or unassigned handoff and a task that invoked `coga block`; the paused
  run is skipped by later sweeps and cannot use ordinary `bump` / `unblock`
  from that state. Do not put human gates or expected blockers in a scheduled
  agent workflow. Use the on-demand `coga recurring launch <name>` path (then
  drive the ordinary ticket handoff) or an ordinary task when a run needs
  those intermediate states.
- **Agent work needs a TTY; complete scripts can be headless.** An agent-backed
  template needs stdin and stdout TTYs and runs under the REPL supervisor; a
  TTY-less sweep skips it with a warning. A one-step script-backed template
  runs directly without a TTY and is the appropriate shape for an unattended
  scheduler.

The creator performs a deliberate template-to-ticket transform, not an
arbitrary frontmatter clone. Use the recurring fields documented above. In
particular, put process skills on workflow steps: ticket-level `skills:` and
repo-defined extension-field values are not copied from the template into the
period task.

## Last-run state lives in the recurring task's blackboard

Each scheduled firing uses the stable instantiated task path
`coga/tasks/recurring/<name>/`, with its own fresh blackboard. That task
directory is deleted after completion and recreated later, so the run
blackboard does **not** carry over.

So a recurring task that needs continuity between runs (a last-processed
commit SHA, a cursor, a posted/skipped flag) keeps that state in **its own**
blackboard region: the part of `coga/recurring/<name>/ticket.md` below the
fence. The creator also keeps the schedule high-water mark there as `last_serviced_period:
<period_key>`, overwriting the single line as periods advance.

When designing a recurring task that carries cross-run state, name in the
body *which* keys it persists (e.g. `last_commit`, a cursor section). You
do **not** need to re-teach the launched run *where* state lives — the
creator auto-attaches the `coga/period-task` context to every period
task, which carries that rule.

## The creation contract

- **Instantiated task ref** is `recurring/<name>`, backed by
  `coga/tasks/recurring/<name>/`. The `recurring/` directory is the
  identity marker. The period is not in the slug.
- **`last_serviced_period` in the template blackboard is the period
  high-water mark.** The period key buckets the firing: hourly →
  `YYYY-MM-DD-HH`, daily → `YYYY-MM-DD`, weekly → `YYYY-Www`, monthly →
  `YYYY-MM`. Bare `coga recurring` reads the blackboard region of
  `coga/recurring/<name>/ticket.md` before creating: if
  `last_serviced_period >= current period_key` and no instantiated task dir
  remains, that period has been handled — it is not re-created and not
  re-launched. The on-demand `coga recurring launch <name>` (and aliases like
  `coga dream`) bypass this skip: it's the explicit override.
- **Run history goes to the repo-global `coga/log.md`** (tagged
  `recurring/<name>`). The creator still appends a human-readable period line,
  but dedup does not depend on
  parsing the log. Logs are never composed into prompts, so history can grow
  without bloating the next run.
- Period tasks create **straight to `status: active`** — ready jobs, not
  drafts to triage. Because every active task must carry a workflow, a
  template that declares none creates with `direct/body` (it would otherwise
  be un-activatable and `coga validate` would flag it as a stuck task).
- `assignee` defaults to the repo's configured **default agent** when the
  recurring task omits it — never the human `owner`, which `coga launch`
  cannot resolve to an agent type.
- `coga validate` resolves every workflow-step skill referenced by each
  materialized recurring template, before a period task exists. Missing refs
  report the local and bundled paths checked; the removed bundled
  `coga/megalaunch/run` ref instead gives its migration directly: megalaunch
  is on-demand only, so delete the leftover recurring template and workflow.
- The period task's `## Description` is taken from the `ticket.md` body's
  `## Description` section: everything from that heading to the next
  top-level `## ` heading. **Convention:** keep every other heading in the
  body at `###` so the whole run instruction lands in the description.

## REM is user-space recurring maintenance

REM is repo/user-specific recurring maintenance — the place for operational
checks meaningful to this repo, team, or user: product or operations health
checks; customer, email, payment, or deployment follow-ups; repo-specific
context audits; domain-specific recurring reports; reminders that depend on
this repo's tasks and blackboards. A REM task is an ordinary template authored
with the recipe above; it owns its own cadence, ticket scan, skill order,
output conventions, and review gates.

REM is not Dream. Dream is Coga's generic ticket cleanup pass; generic Coga
cleanup does not belong in a REM pass, and neither does branch hygiene unless
the REM task is explicitly a dev maintenance loop. Have each run write one
concise summary to its period task's blackboard, listing any PRs opened,
tickets created, or human gates.

## Dream is the recurring janitor

A finished current-period task normally sits on disk as an ordinary
`status: done` ticket at `tasks/recurring/<name>/` until Dream runs at the end
of the same sweep. Dream's Phase 4 retro pass processes each eligible done
ticket; recurring period tasks carry nothing durable, so Retro direct-deletes
them via `coga delete recurring/<name>` with no PR or marker.

The scheduler is the liveness fallback. If any completed recurring task
survives into a later period, it deletes that stale artifact before creating
the fresh task at the stable path. This is also how Dream's own completed task
is removed: Dream marks itself `done` and stops, then the next firing's scan
deletes that prior-period task before creating the new Dream run. Git history
is the audit trail; the template's `last_serviced_period` remains persistent.

## Gotchas

- A stray top-level `## ` heading anywhere in the body — including inside a
  fenced code block — truncates the extracted description there. Indent
  example blocks or use `###`.
- Do not store last-run state in the instantiated task's blackboard under
  `coga/tasks/recurring/<name>/` — it is fresh for one run and deleted on
  cleanup. Use the recurring task's own blackboard region in
  `coga/recurring/<name>/ticket.md`.

## What this context does NOT cover

Scheduler wiring, how to write a run's skill or body
logic, and notification posting mechanics (see `coga/sync`). Implementation lives
in `src/coga/recurring.py` and `src/coga/recurring_runner.py`.
