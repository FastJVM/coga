---
name: coga-dev/codebase
description: Overview of the Coga source tree and contribution rules, with links to the testing, packaging, extension, and editing-gotcha topics; read before editing Coga's own code.
---

# Coga codebase

The repo separates implementation from the OS it operates:

- **`src/coga/`**: the kernel package and CLI.
- **`src/coga_edge/`**: edge job implementations shipped in the same wheel;
  placement is owned by [coga-dev/microkernel](../microkernel/SKILL.md).
- **`coga/`** plus the configured contexts root (`docs/contexts/` in this
  repo): the Coga OS this repo operates on. Layout is owned by
  [coga/context-layout](../../coga/context-layout/SKILL.md).

## Source map

- `src/coga_edge/phone_home.py`: the default telemetry implementation behind
  the repo shim; [phone-home ticket](https://github.com/FastJVM/coga/blob/main/coga/recurring/phone-home/ticket.md) owns its contract.

- `src/coga/commands/`: one Typer entrypoint per command. Thin entrypoints
  with no business logic are the target; `init.py` still carries substantial
  logic. Launch's command adapter calls shared `coga.launch`. `update.py` (init's
  template-copy helpers) and `common.py` are shared helpers, not commands.
- `config.py` (shared/local TOML, fixed schema), `compose.py` (prompt layers),
  `tasks.py` / `taskfile.py` / `blackboard.py` (ticket IO),
  `workflow.py` / `bump.py` / `step_gate.py` / `mark.py` (steps, gates,
  status), `validate.py` (`coga validate`).
- `git.py`: the whole Git sync layer (`publish`, `refresh`,
  `prepare_control_checkout`, `state_lock`, public plumbing). Contract in [coga/sync](../../coga/sync/SKILL.md).
- `runner.py`: the fixed `coga run` registry; recipes live in focused modules
  (`open_pr.py`, `delete_task.py`, `autoclose.py`, `branchsweep.py`, ...).
- `launch.py` (launch API, preparation and supervision),
  `checkout_policy.py` (pure step-to-entry-checkout table) and
  `checkouts.py` (shared branch preparation for launch and the
  `prepare-checkout` chat recipe; [dev/checkouts](../../dev/checkouts/SKILL.md)),
  `launch_script.py` (reserved `ticket.py` phase), `task_env.py`
  (`COGA_TASK_*`), `repl_supervisor.py`, `megalaunch.py` plus
  `service_order.py` (drain), `recurring_runner.py`, `recurring_autofix.py`,
  `recurring_clone.py`.
- `branchcleanup.py` (per-checkout proofs), `checkout_disposal.py` (claim and
  disposal order), `retire_worklist.py` (`retires.md`).
- `dependencies.py` (external CLI manifest) and `agent_cli_setup.py` (agent
  CLI install and login offer, for `coga init` and `coga build`).
- `skill_manager.py` (`coga skill`), `notification/`,
  `text.py` (shared ANSI stripper), `reminders.py` (sweep harness for
  downstream scripts).
- `resources/`: prompt resources and the packaged Coga OS under
  `resources/templates/coga/`; see [coga-dev/packaging](../packaging/SKILL.md).
- `tests/` (`tests/test_*.py`, named after the command or module) and
  `tests/fixtures/seeded-repo/coga/`, the seeded end-to-end fixture.

Module-level seams a new caller must respect (operator resolution, the
`prepare_active` / `mark_active` split, blackboard writers, create guards) are
in [coga-dev/codebase/gotchas](gotchas/SKILL.md).

## Contribution rules

- **Microkernel.** Core holds only shared infra with two or more real
  consumers or a reviewed co-versioned command contract. The rule and its
  exceptions are owned by [coga-dev/microkernel](../microkernel/SKILL.md).
- **Style.** Python 3.11+, 4-space indentation,
  `from __future__ import annotations`, explicit type hints, `snake_case`
  modules and functions, `PascalCase` dataclasses and exceptions, standard
  library first, small command handlers. Keep projects, skills, contexts,
  workflows, and tasks distinct.
- **Fixtures.** Changes to prompt composition, workflow freezing, config
  loading, or task creation update `tests/fixtures/seeded-repo/` or related fixtures.
- **Docs travel with behavior.** A behavior change updates its owning topic in
  the same PR. One owner per fact; see
  [coga/knowledge](../../coga/knowledge/SKILL.md).
- **Twins.** Canonical topics and their packaged copies must stay
  byte-identical; see [coga-dev/packaging](../packaging/SKILL.md).
- **Commits and PRs.** Short factual subjects; a ticket prefix only when a
  ticket exists. A PR explains the behavior change, names fixture and doc
  touchpoints, and lists the exact verification commands and counts
  ([coga-dev/testing](../testing/SKILL.md)).
- **Legibility.** Changes that hide state, move logic into opaque services,
  or blur the correction loop are usually wrong
  ([coga/architecture](../../coga/architecture/SKILL.md)).

## Related topics

- [coga-dev/testing](../testing/SKILL.md): running the suite, environment
  pitfalls, CI posture, verification receipts.
- [coga-dev/packaging](../packaging/SKILL.md): bundled batteries, twins, wheel.
- [coga/releasing](https://github.com/FastJVM/coga/blob/main/coga/skills/coga/releasing/SKILL.md): PyPI release and install gate.
- [coga/skill-management](../../coga/skill-management/SKILL.md): skill shapes and
  `coga skill`.
- [dev/code](../../dev/code/SKILL.md): conventions for code tickets,
  checkouts, and PR linkage.
