---
title: Skip inactive-repo recurring templates without strict validation
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 3 (open-pr)
contexts:
- coga/recurring/scheduling
- coga/recurring/templates
agent: claude
---

## Description

On an inactive repo, `scan_due` (src/coga/recurring.py) runs the strict `Template.load` before the inactivity skip. A stale non-exempt template (e.g. a pre-simplification `assignee:` key, seen on xpllm 2026-10-07) therefore errors and fires an --important alert for a repo the owner has stopped working on.

The full load exists only to read `run_when_inactive` (and the schedule for the table row). Change: on an inactive, non-forced sweep, read just those fields leniently; non-exempt templates get the normal `skip (repo inactive since …)` row with no strict validation and no alert. Exempt templates, active repos and `--force` keep full validation. Frontmatter that cannot be parsed at all still reports loudly.

Tradeoff accepted by the owner: a broken template on a dormant repo surfaces only when the repo wakes (or via `coga validate`).

Done when: the `## Repo inactivity` section of coga/recurring/scheduling ("Inactive templates are loaded and validated, then skipped") and the `run_when_inactive` bullet in coga/recurring/templates are updated, packaged twins stay in sync, and tests cover: inactive + rejected-key template → skip row, no scan error; inactive + exempt broken template → error; active broken template → error.

Out of scope (separate ticket if wanted): checking inactivity right after the fetch so a diverged inactive repo (thinkpick) is skipped instead of failing control catch-up.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: inactive-lenient-template-skip

Plan: in `recurring.scan_due`, on an inactive non-forced sweep call a new
lenient reader (`recurring._read_inactivity_fields`) before `Template.load`;
non-exempt → skip row, exempt → strict load as before.

### Implement handoff

Pushed `inactive-lenient-template-skip` (rebased on origin/main 4cb59f31c).

- `recurring.scan_due`: on `inactive_since is not None and not force`, calls
  new `recurring._read_inactivity_fields(path, now)` before `Template.load`.
  Non-exempt → `inactivity_skips` row, no strict load, no error/alert. Exempt
  → falls through to strict `Template.load` exactly as before.
- Lenient reader still raises (template error) for: missing ticket.md, no
  frontmatter, non-mapping frontmatter, non-bool `run_when_inactive` (the
  exemption is undecidable; keeps `test_run_when_inactive_must_be_boolean`).
- Decision: an invalid/missing schedule on a non-exempt inactive template is
  also skipped; `DueScan.inactivity_skips` firing became `datetime | None`,
  rendered as `-` in both `recurring_runner` scan table and
  `recurring_autofix.scan_lines_for_record`.
- Docs: `## Repo inactivity` in coga/recurring/scheduling and the
  `run_when_inactive` bullet in coga/recurring/templates, canonical + bootstrap
  twins updated identically.
- Tests (tests/test_recurring.py): `test_inactive_sweep_skips_broken_template_without_strict_load`
  (inactive rejected-key → skip row, run_recurring_scan exit 0, no notify;
  inactive exempt → error; active → error),
  `test_inactive_sweep_reports_unreadable_frontmatter`,
  `test_inactive_sweep_skips_template_with_bad_schedule`.
- Verification: full `python -m pytest` 3357 passed, 1 failed in
  test_edge_distribution (inventory sort order) which also failed on main and
  passes after rebasing onto #974 (pin-inventory-sort-collation);
  re-ran test_recurring + test_packaging + test_edge_distribution after rebase: green.

Implementation finding (resolved during peer review below): `Template.load` does not catch
`yaml.YAMLError`, and `recurring._template_period_targets` calls it first
inside `scan_due`, so a template with syntactically invalid YAML frontmatter
raises out of the whole scan (active or inactive) instead of becoming one
`## Template errors` entry. Repro: write `---\nschedule: [unclosed\n---\n`
into recurring/<name>/ticket.md and call `scan_due`. Fixed in the review commit.


## Peer review

`codex review --base main` returned successfully. The first sandboxed attempt
could not initialize its app-server; the unsandboxed retry completed. It found
one P2: falsey non-mapping YAML (`[]`, `false`, `0`) was coerced to `{}` and
silently skipped. Fixed by checking the decoded type before any fallback;
regression coverage includes these values and `null`.

Manual review also found the ledger pre-pass still strictly loaded dormant
non-exempt templates. It now applies the inactivity gate first; the regression
test fails if `Template.load` is called anywhere for that skipped template.
The shared source reader now converts malformed YAML to `RecurringError`, so
the sweep reports the template error and continues. Tests cover continued
scanning on inactive, active and forced sweeps, plus strict validation of
exempt and forced broken templates. Scheduling docs and the packaged twin
include this behavior. No unresolved must-fix findings or design changes.

No raw terminal loop, pager, prompt or Slack rendering changed. Captured scan
output verifies the inactivity skip row and absence of notifications; the
run-record test covers a bad schedule's missing firing. No interactive surface
requires a separate terminal exercise.

Rebased unconditionally with `git fetch origin main && git rebase FETCH_HEAD`.
Pushed `inactive-lenient-template-skip` with `--force-with-lease` at
`9bc1438f0` (two code commits ahead of control), then returned to clean `main`.

Verification (Python 3.12.12):
- `PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/test_recurring.py -q -k 'inactive or inactivity or malformed_yaml'`: 30 passed, 446 deselected.
- After rebase, `PYTHONPATH=$PWD/src .venv/bin/python -m pytest`: 3366 passed in 347.26s, including packaging twins and edge distribution.
- `git diff --check`: passed. Python 3.11 was not exercised.

## PR

Inactive repositories now skip non-exempt recurring templates before strict
validation, including the ledger pre-pass. Stale rejected keys therefore
produce the normal inactivity skip row without alerts. Active repositories,
exempt templates and `--force` retain full validation; invalid schedules on
skipped templates display `-` for their firing.

Unreadable or non-mapping YAML and non-boolean exemption flags remain reported
errors. Malformed YAML no longer aborts the whole sweep. Updated the recurring
scheduling and template contracts and their packaged twins, with regressions
for inactive, exempt, active, forced and malformed-frontmatter cases.

Test plan: `PYTHONPATH=$PWD/src .venv/bin/python -m pytest` — 3366 passed on Python 3.12.12; `git diff --check` passed.
