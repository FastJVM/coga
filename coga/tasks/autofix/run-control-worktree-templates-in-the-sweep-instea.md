---
title: Run control-worktree templates in the sweep instead of dropping them
status: in_progress
owner: nicktoper
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 3 (pr)
agent: claude
launch_generation: 54ff7016-95f4-4ec1-8749-b3d7768054b6
---

## Description

When the operator's primary checkout is not on the control branch, the
recurring sweep services the repo from a temporary control worktree. There,
agent-backed templates (no `ticket.py`) are deliberately refused. That
refusal is correct, but the run record hides it: the refused templates get
no `## Scan` row, show up only under `## Template errors` with wording that
reads like success ("serviced from a temporary control worktree because …"),
and the summary still says `problems: 0` / "No recurring tasks due".

Refiled from the `multiply` repo (its ticket
`autofix/run-control-worktree-templates-in-the-sweep-instea`, canceled in
favour of this one, since every line to change is here).

### Observed (multiply bare sweep, 2026-10-06 10:36)

- `templates scanned: 4` of six under `coga/recurring/`; `autoclose-merged`
  (`0 8 * * *`) and `blocker-reminders` (`0 10 * * *`) were both due but had
  no scan row.
- `## Template errors` listed both with: "serviced from a temporary control
  worktree because /home/n/Code/codex/multiply does not have 'main' checked
  out; agent phases need a durable checkout on the control branch."
- `tasks run: 0`, no period task created for either, yet `problems: 0`.
  That period's merged-ticket autoclose and blocker reminders silently
  didn't happen.

## Fix

Keep the off-control refusal (deterministic phases only off control is a
design decision; see `coga/internals/recurring-temp-worktrees`). Make it
visible ("refuse it" option):

1. Every template gets a `## Scan` row with a due/skip decision even off
   control, e.g. `skip (control branch not checked out)` for a refused
   agent-backed template.
2. Every `scan_errors` entry counts toward `problems:`; a run record with a
   non-empty `## Template errors` never reports `problems: 0` or
   "No recurring tasks due".
3. Reword the refusal so it says the template was **not run** (drop
   "serviced", which `_sweep_all` also uses for a successful deterministic
   run).
4. Regression test in `tests/`: off-control checkout plus a due
   agent-backed template; assert the scan row exists and the template is
   counted as a problem.

## Context

Code path (checked at `origin/main` `a1a356aa2`):

- `src/coga/recurring_runner.py`, `_control_worktree_agent_refusal`: builds
  the "serviced from a temporary control worktree …" text; the recurring
  scan entry point passes it to `scan_due(..., agent_unavailable_reason=...)`
  when servicing from a control worktree.
- `src/coga/recurring.py`, `scan_due`: puts agent-backed templates refused
  for that reason into `scan_errors` instead of a scan row.
- `src/coga/recurring_autofix.py`, `RunRecord.render`: `problems:` counts
  only `self.problems + self.scan_problems`, never `scan_errors`; this is why
  the record said `problems: 0` and "No recurring tasks due".
- `src/coga/recurring_runner.py`, `_sweep_all`: uses the same "serviced"
  phrase for a successful deterministic run.

Separate from autoclose-agent recipe fixes: here the template never reaches
an agent at all, and `blocker-reminders` is affected too.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/966
branch: recurring-control-worktree-refusal-rows

Plan ("refuse it" option, per the multiply diagnosis):

- `scan_due` records agent-unavailable refusals in a new `DueScan.agent_refusals`
  (template, last firing, reason) instead of `errors`, so every template gets a
  `## Scan` row: `skip (control branch not checked out)` in a control-worktree
  run, `skip (agent needs a TTY)` headless.
- Control-worktree refusals are counted in `problems:` (scan_problems, exit 2);
  headless TTY skips stay a documented warning (scheduling topic), row only.
- Real `## Template errors` (load/ledger/create failures) count in `problems:`.
- Reword `_control_worktree_agent_refusal` so it says "not run", not "serviced".
- "No recurring tasks due." only when nothing was refused or errored.

## Handoff (implement, 2026-10-06)

Commit `5f1818141` on `recurring-control-worktree-refusal-rows`, pushed, rebased on
`origin/main`. No PR yet.

What changed:

- `src/coga/recurring.py`: new `AgentUnavailableError(RecurringError)`, raised by
  `create_template` wherever it refused an agent phase. `scan_due` catches it into
  new `DueScan.agent_refusals` `(template, last_fire, reason)` plus
  `DueScan.agent_refusal_label` (new `agent_unavailable_label` kwarg, default
  `"agent needs a TTY"`); the forced-paused refusal path goes there too. These are
  no longer in `scan.errors`.
- `src/coga/recurring_runner.py`: `_control_worktree_agent_refusal` now reads
  "agent phases are not run from a temporary control worktree: … Check out 'main'
  in <host> …" (never "serviced"). `run_recurring_scan` passes label
  `control branch not checked out` in a control-worktree run and adds each refusal
  to `record.scan_problems` as "due but not run: …" → exit 2. Headless TTY skips
  stay a non-problem row (documented warning). "No recurring tasks due." becomes
  "No due recurring tasks could be launched." when refusals/errors exist.
  `_print_table` and the Slack "scan skipped" alert include refusals.
- `src/coga/recurring_autofix.py`: `RunRecord.problem_count` includes
  `scan_errors`; `scan_lines_for_record` emits refusal rows.
- Topics (canonical + packaged twins): `coga/recurring/scheduling`,
  `coga/internals/recurring-temp-worktrees`.

Decisions:

- Genuine template errors count in `problems:` but do **not** change the exit code
  (`test_bare_recurring_skips_malformed_schedule_and_continues` pins exit 0).
- A control-worktree refusal does exit 2, so `coga recurring --all` lists that
  repo as failed rather than "serviced from a temporary control worktree".
  Deliberate: the period really didn't happen. Self-QA/review may want to weigh
  that noise against honesty.

Tests: `python -m pytest`: 3275 passed, 1 failed. The failure is
`tests/test_edge_distribution.py::test_documented_legacy_adoption_preserves_state_and_reconciles_callers`,
which also fails on clean `main` (an ordering assertion on recurring `ticket.py`
paths), so it isn't from this change. Updated TTY-refusal tests to read
`agent_refusals`; strengthened
`test_control_worktree_run_names_agent_templates_and_the_real_reason` (row,
`problems: 1`, no "serviced", exit 2); added two `RunRecord` tests in
`tests/test_recurring_autofix.py`.

## Self-QA (2026-10-06)

Review form: `/code-review` (Skill tool, forked) against `main...branch`, plus a
manual read of the diff. **The review returned** (8 findings); `/simplify` ran as
4 parallel reviewers (reuse, simplification, efficiency, altitude), all returned.
Commit `9d708a028`, pushed. No terminal-only surface touched.

Fixed:

- Must-fix: `create_template` refused a non-launchable current period (canceled,
  blocked, ...) in a non-force scan, so a control-worktree sweep reported it
  "due but not run" and exited 2 every sweep. Now non-force scans never refuse
  in that branch (`not replace_done`); test
  `test_headless_scan_does_not_refuse_unlaunchable_current_period`; scheduling
  topic + twin updated.
- "No due recurring tasks could be launched." no longer fires for template
  errors alone (they may not be due) → "No recurring tasks launched; see
  template errors."
- Refusal reason and its scan-row label chosen in one `if/elif`.

Left for the human reviewer (not fixed):

- Implement decisions kept: control-worktree refusal exits 2 and `--all` lists
  the repo as failed; `problems:` counts template errors without changing exit.
- Forced control-worktree run counts done/paused periods as "due but not run"
  (forced = asked-for, so a non-run is real; wording says "due").
- Prior-period paused refusal row shows the current firing label (nit).
- `/simplify` design suggestions skipped as out of scope: carry the label with
  each refusal / merge skip kinds into one `DueScan` list, and dedupe the
  skip-row loops shared by `_print_table` and `scan_lines_for_record` (the
  duplication predates this branch).

Tests: `.venv/bin/python -m pytest`: 3277 passed, 1 failed, and the failure is
`test_edge_distribution.py::test_documented_legacy_adoption_preserves_state_and_reconciles_callers`.
It also fails on clean `main`. (System `python` lacks `tomlkit`; use `.venv`.)
