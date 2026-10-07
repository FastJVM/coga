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
step: 1 (implement)
agent: claude
launch_generation: pending:707e5a27-c690-4b73-94e2-356fb18d42d1
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
