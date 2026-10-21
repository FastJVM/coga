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

These tickets live under `coga/tasks/microkernel/` and are v1
scope: v1 ships with this table empty. Commands stay where they are until a
reviewed change settles their placement, and the tickets work toward the
kernel boundary below rather than replacing it. Shared helpers and launch-time
trust hooks retain their own kernel justification independently of the
user-facing heads that call them.

## Migrating a built-in to the edge

A stateless verb outside the launch closure and recipe table, with no
co-versioning proof, moves without changing semantics: keep shared parsers,
preflights, and declarative gates (such as `requires: pr` in `bump`) in core
when they have other consumers; keep tests pointed at the moved code with the
same failure behavior; expose the bootstrap target and add an alias only for a
stable spelling; never create a task per invocation.
