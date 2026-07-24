---
slug: make-sure-we-can-drop-new-recurring-tickets
title: make sure we can drop new recurring tickets
status: in_progress
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- coga/recurring
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 3 (open-pr)
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

## Dev

branch: recurring-promote
worktree: /home/n/Code/claude/coga-recurring-promote

## Plan (implement step)

1. `promote_task()` in `src/coga/recurring.py` + thin `coga recurring promote`
   head in `src/coga/commands/recurring.py`.
2. Schedule check in `validate.py::_check_recurring_templates`
   (`invalid-recurring-schedule`), reusing `recurring._validate_schedule`.
3. Docs in `coga/contexts/coga/recurring/SKILL.md` (live context only — no
   packaged copy exists; not adding one).
4. Tests in `tests/test_recurring.py` + `tests/test_validate.py`.

## Decisions (surfaced per ticket)

- **Promotable statuses:** refuse `in_progress` and `blocked` — those carry
  live step/blocker state that a template cannot hold, and silently discarding
  it would lose a running handoff. Everything else (`draft`, `active`,
  `paused`, `done`, `canceled`) promotes. No `--force`; the error tells you to
  `coga mark` first.
- **Template dir name:** defaults to the task's *leaf* slug (so `v2/foo` →
  `foo`), overridable with `--name`. Refuses `_`-prefixed and non-slug names.
- **Frontmatter transform:** keep `title, owner, assignee, watchers, contexts,
  secrets, script`; add `schedule` first. Drop `slug`, `status`, `step`
  (task-only), `human`/`agent` (task-launch fields, not template passthrough),
  and `skills:` (never copied into period tasks — promote warns and tells you
  to put them on workflow steps). A frozen `workflow:` dict collapses to its
  `name:`; absent stays absent (creator defaults to `direct/body`).
  `coga/period-task` is stripped from `contexts` (the creator re-appends it).
- **Blackboard:** reset to the template placeholder. Task scratch is one-run
  state and must not masquerade as cross-run recurring state; the old text
  stays recoverable in git.
- **Ordering:** validate cron → refuse if `coga/recurring/<name>/` exists →
  write + `Template.load()` verify → only then remove the source task. A bad
  schedule or an occupied name leaves the source ticket untouched.
- **Sibling `recurring-schedule-to-create-when-creating.md`:** empty draft,
  redundant — `coga create` + `coga recurring promote` is the create-then-
  schedule path, now documented as such. Closed with `coga delete` from the
  primary checkout (recoverable with `git restore`).

## What landed (commit 2890bd87 on `recurring-promote`)

- `src/coga/recurring.py` — `promote_task()` + `PromoteOutcome`,
  `_template_frontmatter()`, `_render_template_text()`. Deliberately not
  `Ticket.render()`: `schedule` is not a canonical *task* key, so that
  renderer would push it below the `# --- extensions ---` marker.
- `src/coga/commands/recurring.py` — `coga recurring promote <task>
  --schedule "<cron>" [--name <name>]`. One `git.sync_paths` covers the task
  removal and the new template, so no checkout ever sees the ticket in both
  places or neither.
- `src/coga/validate.py` — `invalid-recurring-schedule` (error) in
  `_check_recurring_templates`, reusing `recurring._validate_schedule` via a
  function-local import (`coga.recurring` imports `coga.validate`, so a
  top-level import would be circular).
- Docs: `coga/contexts/coga/recurring/SKILL.md` gains a "Dropping a new
  recurring task" section and the schedule-validation note; the packaged CLI
  context and `docs/reference.md` gain the subcommand. No packaged copy of
  the `coga/recurring` context exists and none was added.
- Tests: 7 promote tests in `tests/test_recurring.py` (including an end-to-end
  promote → `create_named` → real period task) and 3 schedule-validation tests
  in `tests/test_validate.py`.

## Verification

- `python -m pytest` in the worktree: 1504 passed, 1 skipped (re-run after
  rebasing onto `origin/main` 9775d5f9).
- Manual smoke on a copy of `example/coga/`: promoted a real ticket, inspected
  the resulting template, `coga validate` clean; then broke the cron and
  `coga validate --json` reported `invalid-recurring-schedule`.
- `coga validate --json` against this repo's 8 live templates: no new issues.

## Notes for review

- Promote does not notify Slack. It is a repo-authoring move like
  `coga delete`, not a task state transition, so it logs and syncs only.
- A directory-form task's siblings travel with it, except
  `.state-snapshot.json` (a period task's create-time baseline). A
  `script: <file>` template warns that companion script files are not
  materialized into period tasks.

## Peer review

`codex review --base main` ran after rebasing onto `origin/main` at
`cf2e4874`. The full suite was green (`1504 passed, 1 skipped`), but
adversarial probes retained three must-fix findings:

- validate the collapsed workflow before deleting the source ticket;
- preserve directory-form sibling symlinks instead of dereferencing and
  potentially committing their external targets;
- enforce the documented exactly-five-field cron contract before croniter.

The P3 suggestion to normalize the audit actor from `human` to
`human:<current_user>` is a consistency nit and is intentionally skipped in
this must-fix-only review step.

Applied in `1e200d11` after rebasing both feature commits onto current
`origin/main` (`7229e501`):

- the transformed workflow resolves before any destination is written or
  source ticket deleted;
- top-level and nested sibling symlinks are copied as symlinks, never
  dereferenced;
- `_validate_schedule` rejects aliases and six/seven-field crons before
  croniter, and the former year-scoped seven-field test now enforces the
  five-field contract.

Final verification after the last rebase: `python -m pytest` — 1518 passed,
1 skipped; scoped `coga validate --json --task
make-sure-we-can-drop-new-recurring-tickets` — task clean (only the worktree's
expected missing-local-user warning).

## PR

### Summary

- Add `coga recurring promote <task> --schedule "<cron>" [--name <name>]` to
  safely turn an existing ticket into a recurring template with deliberate
  frontmatter and blackboard transforms.
- Add static missing/malformed recurring schedule errors to `coga validate`,
  enforcing the documented five-field cron contract.
- Refuse unsafe promotion states and stale workflows, preserve sibling
  symlinks without dereferencing them, and document the complete authoring
  flow.

### Test plan

`python -m pytest` — 1518 passed, 1 skipped.

## Dream Skill: validate-drift

Generated: 2026-07-24T18:24:41+00:00
Command: `coga validate --json --fix`
Task: `make-sure-we-can-drop-new-recurring-tickets`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-24T18:27:33+00:00
Command: `coga validate --json --fix`
Task: `make-sure-we-can-drop-new-recurring-tickets`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-24T18:29:44+00:00
Command: `coga validate --json --fix`
Task: `make-sure-we-can-drop-new-recurring-tickets`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-24T18:31:13+00:00
Command: `coga validate --json --fix`
Task: `make-sure-we-can-drop-new-recurring-tickets`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-24T18:46:50+00:00
Command: `coga validate --json --fix`
Task: `make-sure-we-can-drop-new-recurring-tickets`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-24T19:06:26+00:00
Command: `coga validate --json --fix`
Task: `make-sure-we-can-drop-new-recurring-tickets`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-24T19:08:43+00:00
Command: `coga validate --json --fix`
Task: `make-sure-we-can-drop-new-recurring-tickets`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-24T21:33:20+00:00
Command: `coga validate --json --fix`
Task: `make-sure-we-can-drop-new-recurring-tickets`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.
