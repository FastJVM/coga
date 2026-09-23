---
title: 'Gigantic refactor: move recurring recipes out of core'
status: draft
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (design)
---

## Description

The owner says the current pattern is an antipattern across the codebase (2026-09-23, in chat, while reviewing PR 880): deterministic work that belongs to one recurring ticket is written as a core module in `src/coga/`, registered in `runner.RECIPES`, and then called back from that ticket's `ticket.py` through `run_recipe`. Code with a single consumer should live next to its ticket as the ticket's own `ticket.py`, not in core.

PR 880 fixes the newest case (phone-home telemetry moves into `coga/recurring/phone-home/ticket.py`). This ticket covers the rest.

### Scope
- Go through every `runner.RECIPES` entry: `autoclose`, `blocker-reminders`, `branch-sweep`, `skill-update`, `validate-drift`, `cleanup-orphan-markers`, `recurring-scan`, `autofix-analyze`, `open-pr`, `delete-task`. For each, record its real consumers (other commands such as `coga autoclose`, the sweep, other recipes, tests). Anything with fewer than two real consumers and no package-private invariant moves next to its ticket.
- Rewrite the rule that currently permits this. `CLAUDE.md`, the base prompt's "Keep Coga small and legible" section, and `coga/codebase` (plus its packaged twins) all name "the recurring jobs" as a sanctioned class of `RECIPES`. Narrow or remove that allowance.
- Keep the failure-reporting floor that `run_recipe` gives a failing recipe (stderr written to the blackboard under `## Recipe Failure`) available to edge `ticket.py` code through a shared helper. PR 880 introduces that helper.
- Update tests, contexts, docs and `coga run` references to match.

### Depends on / related
- `ship-edge-ticket-py-code-upgrades-with-the-wheel`: moving code to the edge today means existing repos stop getting its fixes on upgrade. Decide the order of the two tickets at design time.
- `v2/cleanup-core-commands` (the parked design about what stays in core)
- `autoclose-should-be-script-only`
- `define-the-recipe-reporting-contract-report-durabi`

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
