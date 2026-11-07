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
  [coga/context-layout](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/context-layout/SKILL.md).

## Source map

- `src/coga_edge/phone_home.py`: the default telemetry implementation behind
  the repo shim; [phone-home ticket](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/recurring/phone-home/ticket.md) owns its contract.

- `src/coga/commands/`: one Typer entrypoint per command. Thin entrypoints
  with no business logic are the target; `init.py` still carries substantial
  logic. Launch's command adapter calls shared `coga.launch`. `update.py` (init's
  template-copy helpers) and `common.py` are shared helpers, not commands.
- `config.py` (shared/local TOML, fixed schema; ticket secret refs in
  `parse_inline_secrets`, `select_launch_secrets`, `build_launch_env`,
  `scrub_op_auth_env`), `compose.py` (prompt layers),
  `tasks.py` / `taskfile.py` / `blackboard.py` (ticket IO),
  `workflow.py` / `bump.py` / `step_gate.py` / `mark.py` (steps, gates,
  status), `validate.py` (`coga validate`).
  `config.load_config` rejects unknown keys through `_reject_unknown_keys`,
  `_reject_unknown_sections` and the per-table parsers; removed or misplaced
  keys get tailored errors first. Adding a config key means adding it to its
  table's allowlist and the [coga/configuration](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md)
  table in the same change. Only `_resolve_secret_value` runs `env:`
  indirection, for the two Slack webhook keys.
- `git.py`: the whole Git sync layer (`publish`, `refresh`,
  `prepare_control_checkout`, `state_lock`, public plumbing). Contract in [coga/state-publication](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md).
- `review_conflict.py`: the human-review PR a lifecycle command opens for an
  unrankable ticket status conflict, and its merged/closed/open return path;
  shared by lifecycle commands through `commands/common.reconcile_lifecycle_ticket`
  (`coga-dev/internals/git-regressions`).
- `runner.py`: the fixed `coga run` registry; recipes live in focused modules
  (`open_pr.py`, `delete_task.py`, `autoclose.py`, `branchsweep.py`, ...).
- `oscompat.py`: per-user lock paths and descriptor locks for publication
  and chat, and owned process trees for both recurring runners and the
  Windows agent supervisor. POSIX uses flock/process groups; Windows uses
  byte-range locks and Job Objects. Its interactive mode runs
  `_nt_session_wrapper.py`, a stdlib-only script run by path under the base
  interpreter.
- `launch.py` (launch API, preparation and supervision),
  `checkout_policy.py` (pure step-to-entry-checkout table) and
  `checkouts.py` (shared branch preparation for launch and the
  `prepare-checkout` chat recipe; [coga/checkouts](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md)),
  `launch_script.py` (reserved `ticket.py` phase), `task_env.py`
  (`COGA_TASK_*`), `repl_supervisor.py` with its native Windows backend
  and command planner `repl_supervisor_nt.py` (imported only on Windows by
  the shared entry), `megalaunch.py` plus
  `service_order.py` (drain), `recurring_runner.py`, `recurring_autofix.py`,
  `recurring_clone.py`. `recurring.py` also owns the effective recurring
  catalog (`iter_template_sources`, `resolve_template_source`, `jobs.toml`
  selection); `recurring_state.py` classifies parent directories and owns
  state-only carriers (`parent_state_path`, `ensure_parent_state`), so
  definition lookup and repo-local state writes stay separate. Definition
  resolution for other refs (`resolve_skill_path`, `local_definition_entry`)
  is in `paths.py`.
- `branchcleanup.py` (per-checkout proofs), `checkout_disposal.py` (claim and
  disposal order), `retire_worklist.py` (`retires.md`).
- `dependencies.py` (supporting-tool install manifest, supported agent CLI
  scan order, and the shared missing-agent requirement).
- `skill_manager.py` (`coga skill`; `gh_skill_repo` decides GitHub-backed
  membership, `classify_gh_update_output` maps `gh` output to outcomes; a
  legacy digest that includes machine-local directories may still prove a
  tree unchanged, and status reuses update's comparisons without writing),
  `notification/`,
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
  [coga/knowledge](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/knowledge/SKILL.md).
- **Twins.** Canonical topics and their packaged copies must stay
  byte-identical; see [coga-dev/packaging](../packaging/SKILL.md).
- **Commits and PRs.** Short factual subjects; a ticket prefix only when a
  ticket exists. A PR explains the behavior change, names fixture and doc
  touchpoints, and lists the exact verification commands and counts
  ([coga-dev/testing](../testing/SKILL.md)).
- **Legibility.** Changes that hide state, move logic into opaque services,
  or blur the correction loop are usually wrong
  ([coga/architecture](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md)).

## Related topics

- [coga-dev/testing](../testing/SKILL.md): running the suite, environment
  pitfalls, verification tiers (no hosted CI), receipts.
- [coga-dev/packaging](../packaging/SKILL.md): bundled batteries, twins, wheel.
- [coga/releasing](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/bootstrap/skills/coga/releasing/SKILL.md): PyPI release and install gate.
- [coga/skill-management](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/skill-management/SKILL.md): skill shapes and
  `coga skill`.
- [coga/checkouts](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md): code-ticket checkouts and
  the `## Dev` linkage.
