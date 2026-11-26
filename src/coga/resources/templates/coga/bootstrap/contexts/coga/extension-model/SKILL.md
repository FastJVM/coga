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
  examples; `retire` (`bootstrap/retire`) is a shipped writer example.
  The show, status, usage and recurring-list command tickets are editable
  readers using [read-only dispatch](../launch/SKILL.md#read-only-command-dispatch).
- **External tool**: an existing CLI (`git`, `gh`, `op`) that Coga shells out
  to and whose output it verifies.
- **Stateful ticket or workflow**: reviewable work that wants its own
  blackboard, log, and often a PR. Its deterministic half can be a `ticket.py`
  without a registry entry. State decides between ticket and command, not
  parameters: the `coga retire <slug>` command ticket creates a retire task
  for a canceled ticket because reviewing what to carry forward is agent
  work, and
  deletes a done ticket in place because that is not.

Everything else is Coga's kernel, changed only through Coga itself, not a home
a repo chooses.

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
  moment of use is kernel (launch injects secrets). Secret values never flow
  through tickets, prompts, blackboards, or Git.
  The human [secret query](../secrets/SKILL.md#coga-secret-get-ref) stays in
  the parent process; making a script read-only does not grant operator auth.
  [Uninstall recovery](../uninstall/SKILL.md#recovery-admission) also remains
  built-in because ordinary extension admission depends on the config it
  must be able to remove.

## `coga run <recipe> [args...]`

The recipe set is closed; [coga/cli](../cli/SKILL.md#aliases-and-recipes)
lists it. Nothing is discovered from skills, config, or entry points, and
ticket classification never extends it. An unknown name exits 2 and prints
the known set. Every token after the name is forwarded as an ordinary
argument, stdout and stderr pass through, inherited `COGA_TASK_*` metadata is
preserved, and the command exits with the recipe's integer code. A non-zero
exit also records a `## Recipe Failure` section; that reporting contract belongs
to [coga/recurring](../recurring/SKILL.md). `delete-task` takes a task ref. `autofix-analyze` is covered in
[coga/recurring/autofix](../recurring/autofix/SKILL.md). Git workflow scripts
are covered in [coga/git](../git/SKILL.md).

## Aliases

`[aliases]` in `coga.toml` maps one word to an expanded command; trailing
positional args forward to the expansion. The default aliases, which a repo
entry overrides, are listed with their expansions in
[coga/cli](../cli/SKILL.md). In `retire`'s expansion,
`launch bootstrap/retire --`, the `--` passes its options to the script.

Guardrails:

- **No worse Typer.** Aliases stay fixed rewrites; no conditionals, computed
  args, or validation in TOML.
- **Structural validation fails loud.** The `coga` entry point rejects an
  alias whose name collides with a built-in, that expands to nothing, or
  whose first token is not a built-in command (config load itself checks
  only that each entry is a non-empty string). The CLI exits 2 before running
  any ordinary command, so a bad alias takes down the CLI in that checkout.
  Only `coga init`, `coga uninstall`, and the cross-repo
  `coga recurring --all` parent dispatch on built-in defaults and survive it;
  that parent skips the broken repo rather than dispatching it.
