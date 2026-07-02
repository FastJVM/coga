---
slug: cli-extension-model/move-the-recurring-scan-into-a-dream-shaped-task
title: Move the recurring scan into a Dream-shaped task
status: draft
autonomy: interactive
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/extension-model
- coga/architecture
- coga/codebase
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (design)
---

## Description

**Group 2 of `cli-extension-model/move-command-logic-to-tickets` (Pass 2 of the
extension-model externalization).** Per `coga/extension-model`, the `coga
recurring` scan/orchestration body is a move target: it should live as a
Dream-shaped recurring task that calls the `create` + `launch` kernel
primitives, not as hand-written `commands/recurring.py` logic. The mechanism
already exists — Dream is exactly this shape (a recurring template whose body
orchestrates over kernel primitives), and `autoclose-merged/sweep` /
`digest/post` are the shipped precedents for deterministic logic running as
script steps.

What moves: the scan-templates → get-or-create-current-run → dedup
high-water-mark (`last_serviced_period`) → sequential-launch orchestration in
`src/coga/recurring.py` (819 lines) + its command head in
`src/coga/commands/recurring.py` (1480 lines). What does NOT move: `recurring
list` (a read view — belongs to
`cli-extension-model/move-read-views-to-tickets-as-scripts`), the `create` /
`launch` primitives themselves (kernel), and `recurring launch <name>`'s
alias-facing surface (`dream`, etc. — see `add-recurring-launch-aliases`).

**Guardrails** (from `coga/extension-model`): *no inversion* — the scan,
period-dedup, and get-or-create logic is deterministic, tested Python; relocate
it unchanged into script steps, never rewrite it as agent judgment. *No worse
Typer* — no transient launch-time parameters; anything the scan needs must be
in files on disk (templates, blackboard `last_serviced_period`) as it already
is.

**Design step must settle first:** the bootstrapping question — the scan is
what *creates and launches* recurring runs, so a scan-as-recurring-task can't
be launched by itself. What invokes the scan task (cron calling `coga launch`
on a stateless target? the `coga recurring` verb staying as a thin head that
launches the script, per the `show` precedent in
`move-read-views-to-tickets-as-scripts`)? Coordinate with that reads ticket on
one command-head-launches-script shape rather than inventing two.

Done = design reviewed, then the scan logic relocated unchanged with tests
intact, `coga recurring` (bare scan) reduced to a thin head or alias, and the
seeded `example/` fixture still representative.

## Context

- Origin + full reconciliation trail: the blackboard of
  `cli-extension-model/move-command-logic-to-tickets`.
- The fused-head precedent for "command head stays, substance moves": PR #491
  (`coga.authoring` + `coga/ticket/finalize`).
- Sibling with the same parameterization/head crux:
  `cli-extension-model/move-read-views-to-tickets-as-scripts` (draft,
  unblocked).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
