---
slug: cli-extension-model/move-the-recurring-scan-into-a-dream-shaped-task
title: Move the recurring scan into a Dream-shaped task
status: in_progress
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

Two places the move line cuts *through* shared code — the design must place
them explicitly:
- `create_named` / `_create_at_slug` (get-or-create) are shared by the bare
  scan **and** `recurring launch <name>` (hence `coga dream`). Decide where
  they land so neither path duplicates the other.
- The control-branch git sync of recurring creates
  (`_land_recurring_create_on_control_branch`, `last_serviced_period` merging,
  restore/reconcile — roughly half of `commands/recurring.py`) is sync
  infrastructure, not scan logic. Decide whether it moves with the scan, stays
  shared, or is out of scope.

**Guardrails** (from `coga/extension-model`): *no inversion* — the scan,
period-dedup, and get-or-create logic is deterministic, tested Python; relocate
it unchanged into script steps, never rewrite it as agent judgment. *No worse
Typer* — no transient launch-time parameters; anything the scan needs must be
in files on disk (templates, blackboard `last_serviced_period`) as it already
is.

**Design step must settle first:** the bootstrapping question — the scan is
what *creates and launches* recurring runs, so a scan-as-recurring-task can't
be launched by itself. This has two layers:
- *Invocation:* what invokes the scan task — cron calling `coga launch` on a
  stateless target, or the `coga recurring` verb staying as a thin head that
  launches the script?
- *Shape:* if the scan were itself a recurring *template*, something would
  have to scan it — the scanner can't get-or-create its own run. So the
  design may conclude the scan is a **stateless bootstrap-style script
  target** with no period dedup of its own, not a recurring template.
  "Dream-shaped" in the title is a working framing, not a commitment.

**This ticket leads the command-head-launches-script design** (owner decision,
2026-07-02): its design step settles the thin-head-launches-script shape, and
`move-read-views-to-tickets-as-scripts` inherits that pattern for `show` /
`status` rather than inventing a second one.

Known constraints the design must work within (don't rediscover these):
- `launch.py:267-268` hard-refuses script launches on stateless
  bootstrap-style tickets — a stateless scan target hits this check; the
  design either relaxes it (still a hard check, different rule) or picks a
  shape that avoids it.
- `autonomy: auto` launches are currently frozen, and `recurring.py` enforces
  the same freeze — the relocated scan must preserve that enforcement.
- The scan launches agent sessions; as a script step it does so from inside a
  launched session. The `COGA_DONE_SENTINEL` session-id matching exists to
  keep nested launches from tearing down parents — verify the nested
  PTY-supervisor path (including `_stop_if_unfinished_after_launch` idle/max
  timeouts) survives the move.

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
  unblocked). **This ticket designs the shared head pattern first; the reads
  ticket inherits it.**
- The scan's command flags today: bare `coga recurring` takes `--interactive`
  and `--all`; `recurring launch` takes `<name>` and `--interactive`. Per "no
  worse Typer" these stay at the thin head's Typer layer.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
