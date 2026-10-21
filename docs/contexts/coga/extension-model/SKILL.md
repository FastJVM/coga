---
name: coga/extension-model
description: Choosing repo capability homes, parameter and trust boundaries, fixed recipes, and command aliases.
---

# Extending a Coga repo

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
  JSON block. With the exact sibling `ticket.py` it runs that script with the
  trailing argv as its operands and no agent; its `ticket.md` owns the verb's
  contract. Repo-local definitions win over packaged ones.
  `resolve-conflicts` and `address-pr-comments` are the shipped agent
  examples; `retire` (`bootstrap/retire`) is the shipped script example.
- **External tool**: an existing CLI (`git`, `gh`, `op`) that Coga shells out
  to and whose output it verifies.
- **Stateful ticket or workflow**: reviewable work that wants its own
  blackboard, log, and often a PR. Its deterministic half can be a `ticket.py`
  without a registry entry. State decides between ticket and command, not
  parameters: the `coga retire <slug>` command ticket creates a retire task
  for a canceled ticket because the retro is multi-step reviewed work, and
  deletes a done ticket in place because that is not.
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
`autofix-analyze`, `skill-update`, `open-pr`, `delete-task`,
`publish-state`, `prepare-checkout`. Nothing is
discovered from skills, config, or entry points, and the ticket classifier
never extends the table. An unknown name exits 2 and prints the known set.
Every token after the name is forwarded as an ordinary `list[str]`, stdout and
stderr pass through, inherited `COGA_TASK_*` metadata is preserved, and the
command exits with the recipe's integer code. `runner.run_recipe` also records
a `## Recipe Failure` section on non-zero exit; that reporting contract belongs
to [coga/recurring](../recurring/SKILL.md). `open-pr` and `delete-task` take a
task ref; see [PR publication](../pr-publication/SKILL.md) and
[coga/checkouts](../checkouts/SKILL.md). `autofix-analyze` is covered
in [coga/recurring/autofix](../recurring/autofix/SKILL.md). `publish-state`
is the strict, exit-coded form of the state sweep for a handoff that must know
its files reached control (`build/onboarding`); its contract is in
[coga/state-publication/sweep](../state-publication/sweep/SKILL.md).
`prepare-checkout` is the one in-chat consumer of the shared branch
preparation (`src/coga/checkouts.py`) that ordinary launch also calls, so the
mechanics are shared infra; the recipe is a registered contract because its
argv, report, and 0/2/75 exits must agree with launch's private live-chat
receipt. It is not a Typer head, alias, ticket plugin, or general phase
registry; its contract is in [coga/checkouts/chat](../checkouts/chat/SKILL.md).

## Aliases

`[aliases]` in `coga.toml` maps one word to an expanded command; trailing
positional args forward to the expansion. `aliases.DEFAULT_ALIASES` registers
ten defaults that dispatch even when `coga.toml` omits them (user entries
override): `chat`, `dream`, `build`, `skill-update`, `autoclose`, `pick`,
`open-pr` (`run open-pr`), `resolve-conflicts`, `address-pr-comments`,
`retire` (`launch bootstrap/retire --`; the `--` passes its options to the
script). The
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
