---
name: coga/recurring/templates
description: How to author or promote a recurring template — fields, parking, the template-to-period transform, first-firing behavior, cross-run state surfaces, and the ticket.py completion and reporting contract.
---

# Recurring templates

A template is `coga/recurring/<name>/ticket.md` (frontmatter plus run body) and
optional siblings. Its blackboard region, below `<!-- coga:blackboard -->`,
persists across every run. A non-underscore directory with a valid `schedule:`
is live; rename `foo/` to `_foo/` to park it (the scanner and validation skip
it). There is no starter directory — copy an existing template.

## Fields

- `schedule` — required 5-field cron. Missing or malformed: the sweep skips the
  template with a warning and a summary entry; `coga validate` reports
  `invalid-recurring-schedule`.
- Execution is **deduced, never declared**: a reserved sibling `ticket.py` means
  a deterministic phase runs first; no `ticket.py` means agent-backed. There is
  no `mode:` field; a leftover `recipe:` key is inert. A `ticket.py` template's
  step still says `assignee: agent` — that is the agent a hybrid run falls
  through to, not an error.
- `delegate: bootstrap/<name>` — optional, mutually exclusive with `ticket.py`;
  see [delegation](../delegation/SKILL.md).
- `workflow` — optional; none means the one-step `direct/body` workflow, which
  runs the body's ordered phases (Dream is the canonical case). Any workflow an
  ordinary task can resolve is allowed; there is no recurring-capable registry.
- `title` (else the humanized name), `owner`, `agent`, `contexts`, `secrets` —
  passed to each period task. `agent` omitted means the repo default agent.
- `state_keys` — list of parent-blackboard keys a run must advance (see
  [coga/period-task](../../period-task/SKILL.md)).
- Rejected: top-level `slug`, `human`, `assignee`, `watchers`
  (`bad-recurring-template`, before any period is created or reused) and
  `period_generation`, which is creator-owned period state.

## The template-to-period transform

`recurring._create_at_slug` routes each firing through the ordinary task
creator. It:

- creates directory-form at `recurring/<name>` straight to `status: active`,
  freezing the workflow and selecting the main agent as activation would;
- copies the body above the fence verbatim and starts a fresh blackboard. Only
  `## Description` and `## Context` are composed into the prompt, so keep every
  other heading in the run instructions at `###`; a stray top-level `## `
  (even inside a fenced example) ends the Description there;
- appends `coga/period-task` to `contexts:` (idempotently, always);
- freezes `delegate:` and stamps a fresh `period_generation`;
- copies only the reserved `ticket.py`; other siblings stay with the template;
- writes a `state_keys` snapshot when keys are declared.

Ticket-level `skills:` and repo extension-field values are not copied into a
period task; put process skills on workflow steps. `coga validate` resolves
every step skill of each template and compiles its `ticket.py` before a period
exists.

## Promotion

`coga recurring promote <task> --schedule "<cron>" [--name <name>]`
(`recurring.promote_task`) moves a task to `coga/recurring/<name>/ticket.md` —
also the "recurring from creation" path (`coga create`, write the body,
promote). The body above the fence travels verbatim; the blackboard resets to
cross-run state. `status`, `step`, `period_generation` drop; a frozen workflow
collapses to its name (none stays none); `title`, `owner`, `agent`, `contexts`
(minus `coga/period-task`), `secrets` and extension fields pass through;
ticket `skills:` drop with a warning. Directory-form attachments are copied
except `.state-snapshot.json`. It refuses: an existing destination, a bad cron
or name (checked before anything moves), an unresolvable workflow, and an
`in_progress` or `blocked` task. The template is reloaded before the source is
deleted.

## First firing is retroactive

The scan takes the schedule's last firing strictly before now. A new template
has no ledger line, so its first sweep services the most recent past firing —
an annual template enabled in September runs for last March. There is no
seeding field. Keep it parked with `_` until after the intended firing, or
write the body to no-op on an already-handled period. Never `coga mark
canceled` an unwanted run: a canceled task at the stable path blocks the
template until deleted.

## Cross-run state surfaces

The period task and its blackboard are deleted each period. Durable output goes
to one of: the template blackboard (cursors, `state_keys`); a machine-written
template sibling in a fixed shape (`autoclose-merged/retires.md`, owned by
`src/coga/retire_worklist.py`, `merge=union`, CAS-written; rules in the
`coga/autoclose/sweep` skill); or one-line facts in `coga/log.md`. The schedule
high-water mark lives only in the log (see [scheduling](../scheduling/SKILL.md)).
A repo initialized before `retires.md` shipped needs `**/retires.md
merge=union` in `coga/.gitattributes` (fresh `coga init` writes it) and
refreshed local copies of the packaged `autoclose-merged` template and
`workflows/autoclose-merged/sweep.md`, whose prose composes into every period;
behavior comes from the upgraded package. Backfill line shape is in the skill.

## `ticket.py` completion and reporting

The script runs as `[sys.executable, "<task>/ticket.py"]` with no operands and
must close its own step: shell out to `coga bump` / `coga mark done` (via
`python -m coga.cli`, not the Typer function), or `coga block` for a missing
prerequisite. Chaining is specified in [coga/script-tickets](../../script-tickets/SKILL.md).
Outcomes: closed step — done, no agent; non-zero exit — period stays
`in_progress` and the sweep reports it; **exit 0 with the step open hands the
same period to an agent**, which an unattended sweep cannot run — the commonest
authoring mistake. Exiting non-zero to keep a period visible works but fails
every sweep until fixed; `coga block` records the ask instead.

The period blackboard (`COGA_TASK_BLACKBOARD`, `task_env.blackboard_from_env`)
is a per-run report surface: it reaches the sweep's run record and any autofix
`run-log.md`, then is deleted. Successful runs owe no report. On a non-zero exit
or escaping exception, `runner.run_recipe` appends a `## Recipe Failure`
section (recipe, exit, task, stderr tail) because the sweep discards child
stderr; shims call `run_recipe(load_config(), "<name>", [])` for that reason.
Do not duplicate that write; add structured detail on top. Never write secrets.

The `COGA_TASK_*` variables a script and recipe receive are specified in
[coga/script-tickets](../../script-tickets/SKILL.md).

## Shipped templates in the Coga source repo

Shipped templates have a packaged twin under
`src/coga/resources/templates/coga/recurring/<name>/`; edit both, since the body
is the run prompt `coga init` installs (`tests/test_packaging.py` enforces it;
see [coga/packaging](../../packaging/SKILL.md)). Downstream and promoted
templates need no twin. A job that force-pushes a reused branch must resolve the
remote tip at push time (`git ls-remote`) rather than lease against a possibly
stale tracking ref, as `src/coga/skill_manager.py` does.

## Weekly usage battery

`phone-home` is ticket-owned code, not a registered recipe: its reserved
`ticket.py` holds the whole snapshot, with a one-step `phone-home/run`
workflow. Its changing parent marker, bounded delivery, production suppression
and opt-out contract belong to [coga/telemetry](../../telemetry/SKILL.md).
