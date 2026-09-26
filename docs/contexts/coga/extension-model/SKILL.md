---
name: coga/extension-model
description: The settled rules for where a Coga capability lives (kernel, stateful ticket, stateless command ticket, external tool) and the fixed `coga run` recipe and `[aliases]` surfaces; read before adding a command, recipe, or alias.
---

# Coga extension model

The Python package (`src/coga/`) is a microkernel. Everything else user-facing
is a ticket, a command ticket, a skill describing how to invoke something, or
an external tool. Aliases are argv sugar, not a home. The dated verb-by-verb
inventory is in `docs/design/cli-extension-audit.md`;
the unshipped external-surface proposal (verify-at-compose, extraction) is in
`docs/design/cli-external-surface.md`. Neither is settled rule.

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
ticket or skill that uses it and imports only shared core infra. Core never
imports from a ticket or skill directory. Skills are invocation contracts and
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

| Command surface | Open decision | Parked cleanup review |
| --- | --- | --- |
| `megalaunch`, `retire`, `slack` | Placement of queue orchestration, retire-task creation/launch, and the user-facing notification head | `work-orchestration-commands-to-tickets` |
| `ticket` | Whether the authoring coordinator requires co-versioning or can live at the edge | `residual-command-surfaces` |
| `show`, `status`, `validate`, `usage`, `recurring list` | Placement of the read/report heads, separately from shared rendering and validation infrastructure | `read-report-commands-as-ticket-workflows` |
| `secret get`, `uninstall` | Placement of acquisition/inspection and removal tooling, separately from launch-time secret injection | `support-commands-boundary` |
| `skill *` | Explicit tooling classification; excluded from the current migration push, without a ratified permanent package-home proof | `residual-command-surfaces` |

These reviews live under `coga/tasks/v2/cleanup-core-commands/`, off the
execution path per `coga/tasks/v2/README.md`. Commands stay where they are
until a reviewed change settles their placement. The parked drafts are dated
proposals, not authority to migrate them or to replace the current kernel
boundary below. Shared helpers and launch-time trust hooks retain their own
kernel justification independently of the user-facing heads that call them.

## Choosing a home

Reach for the lowest tier the shape allows:

- **Alias**: a fixed argv rewrite (`dream = "recurring launch dream"`). It owns
  no logic. A verb whose whole body starts a launch is an alias however it is
  spelled, never a Typer command with logic.
- **Registered recipe**: a repository-independent deterministic command whose
  argv, stdout/stderr and integer exit are part of Coga's contract. Adding a
  name is a reviewed kernel change.
- **Command ticket**: repo-extensible stateless behavior, defined by
  `bootstrap/<name>/ticket.md` with no `status:` or `workflow:`. It runs in
  place and creates no task, blackboard, or broadcast. With only `ticket.md`
  it launches an agent that receives trailing argv as a `## Launch arguments`
  JSON block. With the exact sibling `ticket.py` it runs that script with no
  operands and no agent. Repo-local definitions win over packaged ones.
  `resolve-conflicts` and `address-pr-comments` are the shipped examples.
- **External tool**: an existing CLI (`git`, `gh`, `op`) that Coga shells out
  to and whose output it verifies.
- **Stateful ticket or workflow**: reviewable work that wants its own
  blackboard, log, and often a PR. Its deterministic half can be a `ticket.py`
  without a registry entry. State decides between ticket and command, not
  parameters: `coga retire <slug>` creates a retire task because the retro is
  multi-step reviewed work.
- **Kernel**: launch/compose and what launch calls mid-flight (`mark`, `bump`,
  secret injection, notify dispatch), what must exist before any launch
  (`create`, fresh `init`), the `block`/`unblock` state transitions, the fixed
  recipes, and proven co-versioned commands.

Launch-script dispatch (the reserved `ticket.py`, exit-code meaning, reruns)
is owned by [coga/script-tickets](../script-tickets/SKILL.md). Recurring
`delegate:` targets only agent-backed command tickets; see
[coga/recurring/delegation](../recurring/delegation/SKILL.md).

## Parameters and trust boundaries

- A parameter materialized into a ticket at creation is state (the
  `coga ticket` and `retire` heads do this). A stateful workflow must not use
  launch arguments as hidden mutable input.
- Trust boundaries straddle: acquisition is external (`gh skill` installs
  skills; `op` or the environment resolves secrets), while enforcement at the
  moment of use is kernel (launch injects secrets). Compose does not yet verify
  loaded skills against a provenance digest; that hook is unbuilt. Secret
  values never flow through tickets, prompts, blackboards, or Git.

## `coga run <recipe> [args...]`

`runner.RECIPES` is closed: `autoclose`, `blocker-reminders`, `branch-sweep`,
`validate-drift`, `cleanup-orphan-markers`, `recurring-scan`,
`autofix-analyze`, `skill-update`, `open-pr`, `delete-task`. Nothing is
discovered from skills, config, or entry points, and the ticket classifier
never extends the table. An unknown name exits 2 and prints the known set.
Every token after the name is forwarded as an ordinary `list[str]`, stdout and
stderr pass through, inherited `COGA_TASK_*` metadata is preserved, and the
command exits with the recipe's integer code. `runner.run_recipe` also records
a `## Recipe Failure` section on non-zero exit; that reporting contract belongs
to [coga/recurring](../recurring/SKILL.md). `open-pr` and `delete-task` take a
task ref; see [dev/dev-record](../../dev/dev-record/SKILL.md) and
[dev/checkouts](../../dev/checkouts/SKILL.md). `autofix-analyze` is covered
in [coga/recurring/autofix](../recurring/autofix/SKILL.md).

## Aliases

`[aliases]` in `coga.toml` maps one word to an expanded command; trailing
positional args forward to the expansion. `aliases.DEFAULT_ALIASES` registers
nine defaults that dispatch even when `coga.toml` omits them (user entries
override): `chat`, `dream`, `build`, `skill-update`, `autoclose`, `pick`,
`open-pr` (`run open-pr`), `resolve-conflicts`, `address-pr-comments`. The
packaged `coga.toml` spells out only `chat`, `build`, `pick`, and `dream`.

Guardrails:

- **No worse Typer.** Aliases stay fixed rewrites; no conditionals, computed
  args, or validation in TOML.
- **Structural validation fails loud.** `aliases.validate_aliases` raises
  `ConfigError` when a name collides with a built-in, expands to nothing, or
  targets a first token outside `aliases.BUILTIN_COMMANDS`. `cli.main` exits 2
  before running any ordinary command, so a bad alias takes down the CLI in
  that checkout. Only `coga init`, `coga uninstall`, and the cross-repo
  `coga recurring --all` parent dispatch on built-in defaults and survive it;
  keep that escape hatch when tightening validation.
- **No inversion.** Moving logic out of the kernel moves the substance
  unchanged: deterministic Python stays Python (a recipe or `ticket.py`),
  never agent judgment.

## Migrating a built-in to the edge

A stateless verb outside the launch closure and recipe table, with no
co-versioning proof, moves without changing semantics: keep shared parsers,
preflights, and declarative gates (such as `requires: pr` in `bump`) in core
when they have other consumers; keep tests pointed at the moved code with the
same failure behavior; expose the bootstrap target and add an alias only for a
stable spelling; never create a task per invocation.
