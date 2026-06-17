---
title: Verify recurring templates reliably instantiate under unattended cron
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/recurring
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
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

**Fix the one cron-path gap the v1 recurring verification surfaced.** This was
a verification gate over PR #357's create-path restructure (templates
get-or-create a stable task at `relay-os/tasks/recurring/<name>/` straight to
`status: active`). The verification is done — three of the four failure modes
hold, but one is a real v1 launch blocker:

**A present-but-malformed `schedule` wedges the entire sweep.** `scan_due`
resolves `_last_firing(template.schedule, now)` at `recurring.py:242`, which is
*outside* the `try/except RecurringError` guard (line 271). `croniter` raises
`CroniterBadCronError` (a `ValueError`, not a `RecurringError`), so it
propagates uncaught and kills the whole `relay recurring` run — under cron,
every *other* due template then silently fails to instantiate and no human is
watching. `Template.load` validates that `schedule` is *present* but never that
it parses.

Deliverable:

1. Make a bad `schedule` a per-template skip, not a sweep-killer. Cleanest fix:
   validate the cron in `Template.load` (raise `RecurringError` if it can't
   parse) so every entry point that loads through `Template.load` inherits the
   guard — `scan_due` and `list_templates` land the bad template in
   `DueScan.errors` / `TemplateStatus.error`; `create_named` / `create_template`
   surface a clean `RecurringError` to their caller instead of a raw crash.
   Two implementation notes the narrow "CroniterBadCronError" framing can hide:
   catch the **`CroniterError`** base (croniter validates lazily and can raise
   other subclasses), and build the validator the same way `_last_firing` does —
   `croniter(schedule, now)` then probe a firing — so a lazily-parsed bad input
   can't slip past load-time validation.
2. Add the missing failure-mode tests to `tests/test_recurring.py`: a malformed
   `schedule` skips that template and lets the rest of the sweep create/launch;
   and a template directory with **no `ticket.md`** is skipped (today only
   missing-*frontmatter* is tested, via `test_scan_due_skips_bad_template`).
3. One-line note in this ticket's `## Context` recording that the cron create
   path is verified once the fix lands.

## Context

- **Verified covered (no work needed):** no-TTY sweep instantiates **and**
  launches script-mode tasks (`test_bare_recurring_scans_and_launches_due`,
  `test_bare_recurring_skips_interactive_without_tty_and_continues`);
  `_`-prefixed inert dirs skipped (`test_scan_due_skips_underscore_template`);
  same-period dedup via `last_serviced_period`
  (`test_scan_due_idempotent`, `test_scan_due_recognizes_blackboard_high_water`,
  `test_scan_due_does_not_recreate_after_period_task_deleted`).
- **The gap:** malformed `schedule` → uncaught `CroniterBadCronError` at
  `src/relay/recurring.py:242`. `Template.load` (lines 43–64) is the natural
  place to validate.
- `relay-os/scripts/cron.sh` is just `exec relay recurring` (no TTY) — no
  change needed there; the fix is in the Python create/scan path.
- Reframed from a stale bug stub to a verification gate (owner decision,
  2026-06-16); verification performed 2026-06-17 and found the above.
- Pairs with `wire-recurring-sweep-into-system-cron` and
  `enforce-mode-auto-for-recurring-templates` (the other v1 cron tickets).
