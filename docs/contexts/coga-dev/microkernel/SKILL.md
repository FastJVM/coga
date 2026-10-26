---
name: coga-dev/microkernel
description: "Coga core placement: the microkernel rule, open command placement decisions, and moving built-ins to the edge."
---

# Coga microkernel boundary

## The microkernel rule

Code earns a permanent home in `src/coga/` in two ways. Existing command
heads awaiting that decision are recorded under “Open command placements” below.

1. **Shared infra with at least two real consumers**: compose, config,
   task/ticket IO, the launch machinery, shared parsers and gates (for example
   the `## Dev` parsers and `gh` helpers in `autoclose.py`).
2. **A reviewed, co-versioned command contract**: a function in the fixed
   `runner.RECIPES` registry, or a command whose contract names the
   package-private invariant or atomic transaction that an edge implementation
   using stable CLI and filesystem interfaces could not preserve. Python logic,
   operands, validation, or already living in `src/coga/` rule out alias sugar
   but do not by themselves prove a core home.

Everything else stays at the edge. A single-consumer helper lives beside the
ticket or skill that uses it, or in the wheel-distributed `src/coga_edge/`
package, and imports only appropriate shared core infra. Edge shipping does
not confer kernel status. Production `src/coga/` never imports or path-loads
`coga_edge` or ticket/skill implementations; repo shims choose their imports.
Distribution, upgrades and overrides are owned by
[coga/edge-code](../../coga/edge-code/SKILL.md). Skills are invocation contracts and
never executable launch plugins.

- **Count callers of one symbol, not copies of one body.** Three
  byte-identical private `append_report` helpers (`skill_update.py`,
  `dream_validate_drift.py`, `dream_cleanup_orphan_markers.py`) are three
  single-consumer copies. A helper earns a shared home only when the change
  that adds it migrates the existing duplicates onto it in the same PR.
- **The consumer test can keep a symbol in core.** When an implementation
  moves to the edge, any helper it shares with another core consumer stays.

## Open command placements

`megalaunch` is not the only in-package command whose permanent home is
unsettled. The following command heads have no `runner.RECIPES` entry or
ratified command-specific co-versioning proof. Their existing package
residence is provisional; registration as a built-in, Python logic, side
effects, or calling shared infrastructure does not settle their placement.

| Command surface | Open decision | Cleanup ticket |
| --- | --- | --- |
| `megalaunch`, `slack` | Placement of queue orchestration and the user-facing notification head | `work-orchestration-commands-to-tickets` |
| `ticket` | Whether the authoring coordinator requires co-versioning or can live at the edge | `residual-command-surfaces` |
| `show`, `status`, `validate`, `usage`, `recurring list` | Placement of the read/report heads, separately from shared rendering and validation infrastructure | `read-report-commands-as-ticket-workflows` |
| `secret get`, `uninstall` | Placement of acquisition/inspection and removal tooling, separately from launch-time secret injection | `support-commands-boundary` |
| `skill *` | Explicit tooling classification; excluded from the current migration push, without a ratified permanent package-home proof | `residual-command-surfaces` |
| `owner` | Placement of the ticket-owner reassignment head (a `mark`-shaped locked write of `owner:`) | `lifecycle-verbs-to-ticket-operations` |
| `recurring promote` | Placement of the task-to-template move | none yet |

These tickets live under `coga/tasks/microkernel/` and are v1
scope: v1 ships with this table empty. Commands stay where they are until a
reviewed change settles their placement, and the tickets work toward the
kernel boundary below rather than replacing it. Shared helpers and launch-time
trust hooks retain their own kernel justification independently of the
user-facing heads that call them.

The `owner` head's claim to core is its package-private transaction: it holds
`git.state_lock` across the read, prospective validation, local byte
comparison, write, audit, and strict publication with the original ticket
bytes as `expect`. A concurrent local edit is preserved. A definite
publication failure restores only the command's own ticket bytes and retracts
its audit; an uncertain push keeps the write for reconciliation. Both exit 75
to suppress the generic sweep. With Git disabled or unavailable through a
documented soft-skip, the local write remains the result
([publish primitive](../internals/state-publication/publish/SKILL.md)).

## The `ticket.py` script phase

The user contract is [coga/script-tickets](../../coga/script-tickets/SKILL.md).
Owner-accepted design (2026-08-18, PR #700); do not re-argue it without
engaging these reasons:

- **Agent work is deduced from completion, not declared.** Whether the agent
  half runs depends only on whether the script completed its own step, never
  on a static signal such as "the step declares skills". A forgotten
  completion fails toward running the agent (visible, costs tokens, skips
  nothing), never toward silently skipping it. For the same reason launch
  never advances a step on the script's behalf.
- **`ticket.py`, not `run.py`.** A task directory also holds attachments, and
  a `run.py` repro script is a likely accidental trigger; nobody attaches a
  `ticket.py` by accident. The executable bit is ignored because `ls`, GitHub
  and zips do not show or keep it.
- **A stat, not a plugin host.** PR #670's objection ("no plugin host, no
  recursive discovery") does not apply: this is one `stat()` at one fixed path
  inside the target's own directory, affecting only that target, with no scan
  or registry, and core subprocesses the file rather than importing it.
- **Trust caveat, recorded rather than hidden.** A `ticket.py` is a
  git-tracked file reviewed in the PR that adds it, but it runs arbitrary code
  at launch. In a repo where `coga/tasks/**` is granted or reviewed more
  loosely than `src/coga/**`, adding it widens who can cause code to execute
  during launch. Coga's own trust model treats both as "anyone who can write
  this repo", so its threat model does not move; a team that splits those
  permissions should know it.

Source map: `launch_script.script_entry_point` is the classifier;
`run_script_phase` runs one phase (secrets via `build_launch_env`) and
`run_script_chain` chains phases with agent steps. Exit 75 is
`git.RETRY_WITHOUT_SWEEP_EXIT_CODE`. Attribution reads
`task_env.is_script_task`; `task_env.TASK_ENV_KEYS` is the namespace,
cleared by `apply_task_env` and set by `build_task_env`.

## Migrating a built-in to the edge

A stateless verb outside the launch closure and recipe table, with no
co-versioning proof, moves without changing semantics: keep shared parsers,
preflights, and declarative gates (such as `requires: pr` in `bump`) in core
when they have other consumers; keep tests pointed at the moved code with the
same failure behavior; expose the bootstrap target and add an alias only for a
stable spelling; never create a task per invocation.

## The kernel tier and its edges

The kernel is launch/compose and what launch calls mid-flight (`mark`, `bump`,
secret injection, notify dispatch), what must exist before any launch
(`create`, fresh `init`), the `block`/`unblock` state transitions, the fixed
`runner.RECIPES`, thin heads over a fixed recipe (`delete` over `delete-task`,
bare `recurring` over `recurring-scan`), and proven co-versioned commands.
[coga/extension-model](../../coga/extension-model/SKILL.md) owns the tiers a
repo chooses from.

- **No inversion.** Moving logic out of the kernel moves the substance
  unchanged: deterministic Python stays Python (a recipe or `ticket.py`),
  never agent judgment.
- **`prepare-checkout` is a recipe, not shared infra alone.** It is the one
  in-chat consumer of the branch preparation in `src/coga/checkouts.py` that
  ordinary launch also calls, so those mechanics are shared infra. The recipe
  is registered because its argv, report and 0/2/75 exits must agree with
  launch's private live-chat receipt. It is not a Typer head, alias, ticket
  plugin, or general phase registry.
- **Skill provenance at use is unbuilt.** Compose does not verify loaded
  skills against a provenance digest; that launch-time trust hook would be
  kernel when built.
- **Keep the bad-alias escape hatch.** `aliases.validate_aliases` failing
  makes `cli.main` exit 2 before ordinary commands. `uninstall` dispatches
  before alias validation runs; `init` and the `recurring --all` parent catch
  the error, warn, and fall back to `aliases.DEFAULT_ALIASES`. Keep both seams
  when tightening validation.

## Edge packaging invariants

`src/coga_edge/` ships in the same wheel as `src/coga/`. Edge modules may
import shared `coga` infrastructure; core never imports edge implementations.
`coga_edge/__init__.py` has no eager job imports or side effects. Phone-home's
module imports only stdlib and shared `coga.*`, never relative or sibling
edge modules, and carries both normal and private `--worker` dispatch behind
`__main__`; its worker executes that same file, including when copied to a
local fork. Preserve these constraints when refactoring it.
