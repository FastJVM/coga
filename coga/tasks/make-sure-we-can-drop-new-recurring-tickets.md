---
slug: make-sure-we-can-drop-new-recurring-tickets
title: make sure we can drop new recurring tickets
status: draft
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
  - coga/recurring
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

Make it reliable and obvious to "drop" a new recurring ticket. A recurring
template lives at `coga/recurring/<name>/ticket.md` and needs a valid
`schedule:` cron to fire, but today the authoring path has two gaps:

1. **No promote path.** Turning an existing real ticket into a recurring one
   is hand work — you manually move `coga/tasks/<slug>.md` into
   `coga/recurring/<name>/`, strip `status:`, and add a `schedule:`. Add a
   `coga recurring promote <slug> --schedule "<cron>"` command that does this
   move: relocates the ticket into `coga/recurring/<name>/ticket.md`, requires
   and validates the `--schedule` cron up front, transforms task-only
   frontmatter into template frontmatter, and leaves a valid recurring
   template. The full task→template frontmatter transform is part of the work
   (see Context) — not just dropping `status:`.
2. **No static schedule validation.** `coga validate` checks a recurring
   template's workflow/skill references but does **not** re-validate its
   `schedule:` cron — a missing or malformed schedule only fails later at scan
   time. Add a `coga validate` check so a bad/missing `schedule:` on any
   `coga/recurring/<name>/ticket.md` is caught before it ever fires.

Then **explain it**: update the `coga/recurring` context so the promote flow
and the schedule + validation requirement are documented for anyone dropping a
new recurring ticket.

Done = `coga recurring promote` moves a real ticket into a validated recurring
template, `coga validate` flags a missing/invalid recurring `schedule:`, the
`coga/recurring` context documents both, and tests cover the new paths.

## Context

The recurrence engine already exists — this is closing the authoring gap, not
building recurrence from scratch. Key code:

- `src/coga/recurring.py` — `Template.load`, `_validate_schedule`
  (croniter-based, runs at load/scan time), `create_template`, period-key
  helpers. Reuse `_validate_schedule` for the promote command and the new
  `coga validate` check so cron validation stays in one place. Note it's
  module-private (not in `__all__`), raises `RecurringError`, and takes a `now`
  arg — validate.py will import the private symbol and translate the exception
  into an `Issue`.
- `src/coga/commands/recurring.py` — Typer command heads (`coga recurring`,
  `recurring launch`, `recurring list`). Add the `promote` subcommand here.
- `src/coga/validate.py` — `_check_recurring_templates` (validate.py:~802)
  emits `broken-recurring-template-skill`; add the schedule check alongside it
  (e.g. an `invalid-recurring-schedule` issue). Note it currently does NOT
  validate the cron.
- `src/coga/tasks.py` / the create path — for how tickets are moved/created and
  which frontmatter fields are task-only (`status`, `step`) vs template fields.
- Templates carry no `status:`; a template needs `schedule:` (5-field cron),
  optional `workflow:` (defaults to `direct/body`), and passes through
  `title`, `owner`, `assignee`, `watchers`, `contexts`, `secrets`, `script`.
- Tests: extend `tests/test_recurring.py`; add validate coverage where the
  recurring-template validation tests live.

Frontmatter transform (the part that's easy to get wrong):

- Templates carry **no** `status:` or `step:` — drop both.
- `slug:` identifies a task; a template is identified by its directory name, so
  the old `slug:` must not linger in template frontmatter. Decide: drop it, or
  rewrite it to the template name.
- `skills:` is deliberately NOT copied into period tasks (per `coga/recurring`)
  — reconcile a promoted ticket's `skills:` accordingly rather than leaving it.
- Documented template passthrough fields are `title, owner, assignee,
  watchers, contexts, secrets, script`; `workflow:` defaults to `direct/body`
  if unset. `human`/`agent` are task-launch fields — decide keep vs drop.
- The moved blackboard is one-run task scratch; a template blackboard holds
  durable cross-run state (e.g. `last_serviced_period`). Reset/clear the
  blackboard on promote so scratch notes don't masquerade as recurring state.

Scope / gotchas:

- Documentation is the **live context only** (`coga/contexts/coga/recurring/
  SKILL.md`). There is no packaged copy of this context — packaged coga
  contexts (`src/coga/resources/templates/coga/bootstrap/contexts/coga/*`) are
  architecture/cli/period-task/etc., not `recurring`. (Note: recurring
  *templates* like dream/digest do live under `src/coga/resources/templates/
  coga/recurring/` — don't conflate them with the context.) If you think the
  context *should* be packaged, raise it as a deliberate decision, don't
  silently add a second copy.
- `coga recurring promote` should refuse (not overwrite) if
  `coga/recurring/<name>/` already exists, and validate the cron before moving
  anything so a bad schedule leaves the source ticket untouched.
- Decide during implementation whether an already-`active`/`in_progress` ticket
  can be promoted, or only a `draft`/`done` one, and whether the template dir
  name should default to the slug or be overridable — surface both choices.
- Sibling empty draft `recurring-schedule-to-create-when-creating.md` overlaps
  this; fold or close it as part of the work if it's redundant.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
