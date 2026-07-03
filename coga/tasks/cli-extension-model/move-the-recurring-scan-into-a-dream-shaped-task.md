---
slug: cli-extension-model/move-the-recurring-scan-into-a-dream-shaped-task
title: Move the recurring scan into a Dream-shaped task
status: in_progress
mode: agent
owner: nicktoper
human: nicktoper
agent: codex
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
secrets: null
script: null
step: 4 (peer-review)
---

## Description

`coga recurring` is still carrying too much substance in the Typer command
layer. A bare recurring sweep currently parses command flags, scans
`coga/recurring/`, get-or-creates due period tasks, advances each template's
`last_serviced_period` high-water mark, reconciles recurring creates onto the
control branch, prints/broadcasts scan results, and launches due tasks
sequentially from `src/coga/commands/recurring.py`.

Per `coga/extension-model`, that deterministic sweep body belongs behind a
script-shaped target, not in a command head. The scanner cannot be a normal
recurring template because it is the thing that creates and launches recurring
templates; making it scan itself would add a bootstrap loop. The right shape is a
stateless bootstrap-style script target: it has no `schedule:`, no workflow
state, and no `last_serviced_period` of its own. It runs the same deterministic
Python the command runs today, then exits.

The public invocation remains `coga recurring`. The command head keeps Typer's
parameter parsing for `--interactive` and `--all`, then launches the stateless
scan script with those parsed values in an explicit script-env contract. Cron and
operators can keep calling the existing command spelling; the packaged
`bootstrap/recurring-scan` target exists as the script home, not as a new user
workflow to manage.

This preserves the two extension-model guardrails. There is no inversion: the
scan, get-or-create, high-water dedup, sync, and launch orchestration stay tested
Python. There is no worse Typer: runtime flags stay at the command head, and
recurring state still comes from files on disk (`coga/recurring/<name>/ticket.md`,
period task directories, and template blackboards).

## Acceptance Criteria

- Bare `coga recurring` is reduced to a thin head: load config, parse
  `--interactive` / `--all`, invoke the packaged stateless scan script target,
  and surface its exit code. It no longer contains direct scan, sync, table,
  Slack, or sequential-launch logic.
- A packaged stateless script target exists, for example
  `bootstrap/recurring-scan`, with a sibling Python script that imports the
  recurring runner module directly. The target is package-backed like
  `bootstrap/orient`, not materialized into live repos by `coga init`.
- `coga launch bootstrap/recurring-scan` can run a bootstrap ticket-owned script
  without status flips, workflow advancement, task log writes, or Slack
  "started" notifications. Existing bootstrap agent launches remain stateless and
  unchanged.
- `coga recurring --interactive` and `coga recurring --all` preserve today's
  behavior. Their values are passed only from the command head to the scan
  script, not through a generic launch-time parameter channel.
- `create_named`, `create_template`, `_create_at_slug`, period-key calculation,
  and `last_serviced_period` helpers remain shared deterministic Python used by
  both the bare scan and `coga recurring launch <name>`. Neither path duplicates
  get-or-create behavior.
- Recurring create sync moves out of `src/coga/commands/recurring.py` into a
  shared recurring runner/sync module. The bare scan script and
  `recurring launch <name>` both use it, preserving control-branch landing,
  high-water merging, restored-control-task reconciliation, global-log handling,
  and forced-run repair behavior.
- `recurring launch <name>` remains a normal command surface for `coga dream` and
  similar aliases, but its implementation is thin and delegates to the same
  shared create/sync/launch helpers as the scan script.
- The temporary `autonomy: auto` freeze is preserved: agent-backed recurring
  templates still fail/skip exactly as they do today, while script-backed
  templates remain launchable.
- Nested launches from inside the scan script preserve the existing PTY
  supervisor behavior: `COGA_DONE_SENTINEL` session-id matching does not tear
  down the parent script launch, idle/max-session limits are still passed to
  child `coga launch` calls, and `_stop_if_unfinished_after_launch` still records
  unfinished interactive exits, watchdog timeouts, and unattended stuck tasks
  with today's semantics.
- The implementation updates the durable docs/contexts that describe recurring
  and bootstrap script targets, including local `coga/contexts/coga/*` copies and
  packaged `src/coga/resources/templates/coga/bootstrap/contexts/coga/*` copies
  when both exist.
- Tests cover the moved surface without relying on live dogfooded state:
  `tests/test_recurring.py` for scan/get-or-create/sync/launch behavior,
  launch-script tests for bootstrap script support, CLI-head tests for
  `--interactive` / `--all` parameter threading, and packaging/init tests for the
  new packaged bootstrap target.

## Proposed Shape

1. Keep the recurring model in `src/coga/recurring.py`.

   This module should remain the shared deterministic library for recurring
   template parsing and period task creation: `Template`, `DueTask`, `DueScan`,
   `scan_due`, `create_named`, `create_template`, `_create_at_slug`,
   `_period_key`, and the `last_serviced_period` helpers. The functions may move
   mechanically if the implementer finds a cleaner module split, but the
   behavior and tests should move with them. The important design line is that
   both the bare scan and `recurring launch <name>` call one shared get-or-create
   implementation.

2. Extract recurring orchestration from the Typer command.

   Add a non-command module such as `src/coga/recurring_runner.py` for the sweep
   body:

   - `run_recurring_scan(cfg, *, force: bool, interactive: bool) -> int`
   - `run_recurring_named(cfg, name: str, *, interactive: bool) -> int`

   Move the current bare-scan sequence into `run_recurring_scan`: call
   `scan_due`, sync/broadcast created tasks, print the scan table, select
   `scan.due` vs `scan.forced`, launch each task sequentially through
   `coga.commands.launch.launch`, and call `_stop_if_unfinished_after_launch`
   after each child launch.

   Move the current on-demand sequence into `run_recurring_named`: call
   `create_named`, sync the create, skip if the control branch already handled
   it, then launch/resume only `active` or `in_progress` tasks.

3. Put control-branch sync in shared infrastructure, not in the command head.

   Move `_sync_recurring_create` and its helper stack out of
   `src/coga/commands/recurring.py`, either into `recurring_runner.py` if the
   implementer keeps one module or into `src/coga/recurring_sync.py` if the size
   warrants a split. This sync code is not "scan logic" in the product sense, but
   it is required by every recurring create path, so it moves with the recurring
   runner and remains shared by bare scan and named launch.

   Keep the semantics unchanged: take-max `last_serviced_period` merge,
   control-branch overlay landing, feature-only template handling, existing
   control-task restore, forced-run snapshot repair, and union-safe global-log
   behavior.

4. Add a stateless bootstrap script target for the bare scan.

   Add package resources such as:

   - `src/coga/resources/templates/coga/bootstrap/recurring-scan/ticket.md`
   - `src/coga/resources/templates/coga/bootstrap/recurring-scan/run.py`

   The ticket should declare a ticket-owned script (`script: run.py`) and explain
   that it is stateless: no status, no workflow, no schedule, no high-water mark
   of its own. The script should load config, read a narrow env contract written
   by the `coga recurring` head (for example `COGA_RECURRING_FORCE=1` and
   `COGA_RECURRING_INTERACTIVE=1`), call `run_recurring_scan`, and return that
   exit code. Direct `coga launch bootstrap/recurring-scan` can run the default
   non-forced scan with no env variables.

5. Teach script launch how to run bootstrap scripts statelessly.

   Relax the current `launch.py` bootstrap-script refusal by replacing it with a
   narrower rule: bootstrap tickets may run ticket-owned scripts, but they do not
   enter task lifecycle bookkeeping. `run_script_mode` can either accept a
   `stateless=True` flag or delegate to a new helper that shares script
   resolution and environment construction while skipping:

   - `mark_in_progress`
   - task append-log writes
   - post-run `advance_step` / `mark_done`
   - task Slack lifecycle notifications

   Normal task script launches must keep their existing lifecycle behavior.

6. Thin `src/coga/commands/recurring.py`.

   Leave `recurring list` in place for now; it belongs to
   `cli-extension-model/move-read-views-to-tickets-as-scripts`. For this ticket,
   keep only:

   - the Typer group and option definitions,
   - `main(... --interactive, --all)` launching the stateless scan target with
     explicit env,
   - `launch(name, --interactive)` delegating to `run_recurring_named`, and
   - `list_recurring()` plus its read-view helpers until the sibling ticket moves
     them.

7. Update docs and tests with the move.

   Update `coga/extension-model`, `coga/architecture`, and the command-reference
   context/docs that describe `coga recurring`, bootstrap targets, and script
   launches. Keep local and packaged copies in sync where the repo carries both.
   Adjust existing recurring tests so deep behavior targets
   `coga.recurring_runner` / `coga.recurring_sync` instead of
   `coga.commands.recurring`, then leave only thin CLI tests on the command file.

   Verification for the implementation should include at least:

   ```bash
   PYTHONPATH=$PWD/src python3.12 -m pytest tests/test_recurring.py tests/test_commands.py tests/test_launch.py tests/test_init.py tests/test_packaging.py
   PYTHONPATH=$PWD/src python3.12 -m pytest tests/test_period_state.py tests/test_autoclose_sweep.py tests/test_dream_worker_templates.py
   PYTHONPATH=$PWD/src python3.12 -m coga.validate --task cli-extension-model/move-the-recurring-scan-into-a-dream-shaped-task
   ```

## Out of Scope

- Moving `recurring list`; that read view belongs to
  `cli-extension-model/move-read-views-to-tickets-as-scripts`.
- Replacing or renaming the public `coga recurring launch <name>` surface, the
  `dream` alias, or other recurring-launch aliases.
- Building a generic external script/service mechanism, plugin surface, or TOML
  shim system.
- Changing the `create` or `launch` kernel primitives, secret injection, or
  state-write ownership for normal tasks.
- Re-enabling unattended `autonomy: auto` agent launches or designing a cron
  installer/cloud scheduler.
- Rewriting deterministic recurring behavior as agent judgment, Dream skill
  discovery, or prompt-only instructions.
- Changing recurring retention/deletion policy; Dream remains the cleanup owner
  for done recurring period tickets.

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

## Design Notes (2026-07-02, Codex)

Read the ticket, the umbrella blackboard in
`cli-extension-model/move-command-logic-to-tickets`, `docs/vision.md`,
`coga/principles`, and the relevant recurring/launch code. The umbrella
blackboard says PR #491 superseded the old TOML shim idea; the pattern to carry
forward is an irreducible command head plus deterministic script-shaped Python.

Design choice recorded in the body: the recurring scanner is **not** itself a
recurring template. It becomes a stateless bootstrap script target launched by
the thin `coga recurring` head, with the head keeping `--interactive` and `--all`
at Typer's parameter layer. `create_named` / `_create_at_slug` stay shared by
bare scan and `recurring launch <name>`, while control-branch recurring-create
sync moves out of the Typer command into shared recurring runner/sync
infrastructure.

## Open Questions

None for review-design at the moment. The design deliberately settles the
bootstrapping fork in favor of a stateless bootstrap script target plus a thin
command head.

## Dev

branch: codex/recurring-scan-bootstrap
worktree: /tmp/coga-recurring-scan-bootstrap

Implementation plan: extract the bare recurring sweep and named launch
orchestration into shared recurring runner/sync modules; make the public
`coga recurring` command only parse flags and launch the stateless
`bootstrap/recurring-scan` script target with an explicit env contract; allow
that bootstrap ticket-owned script to run without normal task lifecycle writes;
update focused tests plus local/package contexts that describe the new shape.

Implementation result: `src/coga/recurring_runner.py` now owns the scan,
get-or-create, control-branch sync, high-water, reporting, and due-task launch
orchestration. `src/coga/commands/recurring.py` is the thin command head:
bare `coga recurring` launches `bootstrap/recurring-scan` with
`COGA_RECURRING_FORCE` / `COGA_RECURRING_INTERACTIVE`; `recurring launch
<name>` calls the shared named runner; `recurring list` stays read-only.
Bootstrap script tickets now run through `launch_script` with stateless
lifecycle semantics, and contexts/docs/tests were updated to match.

Verification:
- `PYTHONPATH=/tmp/coga-recurring-scan-bootstrap/src python3.12 -m py_compile src/coga/commands/recurring.py src/coga/recurring_runner.py src/coga/commands/launch.py src/coga/commands/launch_script.py src/coga/resources/templates/coga/bootstrap/recurring-scan/run.py`
- `PYTHONPATH=/tmp/coga-recurring-scan-bootstrap/src python3.12 -m pytest tests/test_recurring.py tests/test_commands.py tests/test_launch.py tests/test_init.py tests/test_packaging.py` → 288 passed, 1 skipped
- `PYTHONPATH=/tmp/coga-recurring-scan-bootstrap/src python3.12 -m pytest tests/test_period_state.py tests/test_autoclose_sweep.py tests/test_dream_worker_templates.py` → 39 passed
- `PYTHONPATH=/tmp/coga-recurring-scan-bootstrap/src python3.12 -m pytest` → 1032 passed, 1 skipped
- `PYTHONPATH=/tmp/coga-recurring-scan-bootstrap/src python3.12 -m coga.validate --task cli-extension-model/move-the-recurring-scan-into-a-dream-shaped-task` → All good

## Usage

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":1350272,"cli":"codex","input_tokens":198664,"model":"gpt-5.5","output_tokens":17638,"provider":"openai","schema":1,"session_id":"019f2419-7eb8-77b0-a56d-bd96ac8ac612","slug":"cli-extension-model/move-the-recurring-scan-into-a-dream-shaped-task","step":"design","title":"Move the recurring scan into a Dream-shaped task","ts":"2026-07-02T18:37:22.262989Z","usage_status":"ok"}

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":14083072,"cli":"codex","input_tokens":540615,"model":"gpt-5.5","output_tokens":47514,"provider":"openai","schema":1,"session_id":"019f264f-0123-7731-a54a-b4619b44371e","slug":"cli-extension-model/move-the-recurring-scan-into-a-dream-shaped-task","step":"implement","title":"Move the recurring scan into a Dream-shaped task","ts":"2026-07-03T05:11:47.402279Z","usage_status":"ok"}

{"agent":"claude","cache_creation_input_tokens":null,"cache_read_input_tokens":null,"cli":"claude","input_tokens":null,"model":null,"output_tokens":null,"provider":"anthropic","schema":1,"session_id":"b3fc6274-7432-4e51-affc-3e61a59e122b","slug":"cli-extension-model/move-the-recurring-scan-into-a-dream-shaped-task","step":"peer-review","title":"Move the recurring scan into a Dream-shaped task","ts":"2026-07-03T05:56:11.321206Z","usage_status":"unknown"}
