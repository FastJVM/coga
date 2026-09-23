---
name: coga/codebase
description: Overview of the Coga source tree and contribution rules, with links to the testing, packaging, extension, and editing-gotcha topics; read before editing Coga's own code.
---

# Coga codebase

The repo has two halves with different review bars:

- **`src/coga/`**: the Python package and CLI.
- **`coga/`** plus the configured contexts root (`docs/contexts/` in this
  repo): the Coga OS this repo operates on. Layout is owned by
  [coga/context-layout](../context-layout/SKILL.md).

## Source map

- `src/coga/commands/`: one thin Typer entrypoint per command. No business
  logic.
- `config.py` (shared/local TOML, fixed schema), `compose.py` (prompt layers),
  `tasks.py` / `taskfile.py` / `blackboard.py` (ticket IO),
  `workflow.py` / `bump.py` / `step_gate.py` / `mark.py` (steps, gates,
  status), `validate.py` (`coga validate`).
- `git.py`: the whole Git sync layer (`publish`, `refresh`, `state_lock`,
  public plumbing). Contract in [coga/sync](../sync/SKILL.md).
- `runner.py`: the fixed `coga run` registry; recipes live in focused modules
  (`open_pr.py`, `delete_task.py`, `autoclose.py`, `branchsweep.py`, ...).
- `launch_script.py` (reserved `ticket.py` phase), `task_env.py`
  (`COGA_TASK_*`), `repl_supervisor.py`, `megalaunch.py` plus
  `service_order.py` (drain), `recurring_runner.py`, `recurring_autofix.py`.
- `branchcleanup.py` (per-checkout proofs), `checkout_disposal.py` (claim and
  disposal order), `retire_worklist.py` (`retires.md`).
- `skill_manager.py` (`coga skill`), `notification/`,
  `text.py` (shared ANSI stripper), `reminders.py` (sweep harness for
  downstream scripts).
- `resources/`: prompt resources and the packaged Coga OS under
  `resources/templates/coga/`; see [coga/packaging](../packaging/SKILL.md).
- `tests/` (`tests/test_*.py`, named after the command or module) and
  `example/coga/`, the seeded end-to-end fixture.

Module-level seams a new caller must respect (operator resolution, the
`prepare_active` / `mark_active` split, blackboard writers, create guards) are
in [coga/codebase/gotchas](gotchas/SKILL.md).

## Contribution rules

- **Microkernel.** Core holds only shared infra with two or more real
  consumers or a reviewed co-versioned command contract. The rule and its
  exceptions are owned by [coga/extension-model](../extension-model/SKILL.md).
- **Style.** Python 3.11+, 4-space indentation,
  `from __future__ import annotations`, explicit type hints, `snake_case`
  modules and functions, `PascalCase` dataclasses and exceptions, standard
  library first, small command handlers. Keep projects, skills, contexts,
  workflows, and tasks distinct.
- **Fixtures.** Changes to prompt composition, workflow freezing, config
  loading, or task creation update `example/` or related fixtures.
- **Docs travel with behavior.** A behavior change updates its owning topic in
  the same PR. One owner per fact; see
  [coga/knowledge](../knowledge/SKILL.md).
- **Twins.** Canonical topics and their packaged copies must stay
  byte-identical; see [coga/packaging](../packaging/SKILL.md).
- **Commits and PRs.** Short factual subjects; a ticket prefix only when a
  ticket exists. A PR explains the behavior change, names fixture and doc
  touchpoints, and lists the exact verification commands and counts
  ([coga/testing](../testing/SKILL.md)).
- **Legibility.** Changes that hide state, move logic into opaque services,
  or blur the correction loop are usually wrong
  ([coga/principles](../principles/SKILL.md)).

## Related topics

- [coga/testing](../testing/SKILL.md): running the suite, environment
  pitfalls, CI posture, verification receipts.
- [coga/packaging](../packaging/SKILL.md): bundled batteries, twins, wheel.
- [coga/releasing](../releasing/SKILL.md): PyPI release and install gate.
- [coga/skill-management](../skill-management/SKILL.md): skill shapes and
  `coga skill`.
- [dev/code](../../dev/code/SKILL.md): conventions for code tickets,
  checkouts, and PR linkage.
