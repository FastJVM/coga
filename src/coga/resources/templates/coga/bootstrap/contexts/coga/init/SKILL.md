---
name: coga/init
description: What `coga init` does for a fresh repo versus a clone of a repo that already uses Coga — what it writes and seeds, how its agent CLI scan configures the `[agents.*]` tables, how it records the operator's `user`, and when it relocates the contexts root.
---

# Initialize Coga

Run `coga init --user NAME` in the project directory. It creates the
`coga/` workspace, a local identity, and the agent discovery links. It
can initialize a directory with or without a Git repository. Review and
commit the shared files when ready if you use Git.

In an existing Coga workspace without a configured machine-local user,
the same invocation writes the local identity and repairs agent skill
links. It preserves the shared configuration. If the project directory
is empty, the scaffold supplies the first-run `coga build` ticket.

Init also creates the machine-local run-state areas `coga/.coga/data/` and
`coga/.coga/tmp/` (both idempotently). They live inside `.coga/`, which the
managed ignore blocks in the host `.gitignore` and `coga/.gitignore` already
list, so repos initialized earlier need no ignore change and Git never sees
the state. [coga/launch](../launch/SKILL.md#run-state) owns their contract.

## Agent CLIs and `coga.toml`

Agent-backed commands such as `coga build`, `coga launch`, and `coga ticket`
require an agent CLI. Init can finish without one and leaves finding and
installing it to you. Interactive init may offer to install the supporting
CLIs `git` and `gh` with your confirmation. It prints a note if `op` is missing.

Before writing `coga.toml`, an interactive fresh init checks `PATH` for
each supported agent CLI and reports which ones it found. When it finds at
least one, init comments out the shipped `[agents.*]` tables for agents it
couldn't find. To enable one later, uncomment its table. With the shipped
template, the first remaining table sets the default without a `default_agent`
key. If the default changes, delivered tickets that named the template's
default, including the onboarding ticket if seeded, are updated to use it.

If the scan finds no agent CLI, init copies the packaged config with all its
agent tables enabled and reports the prerequisite for agent-backed commands.
If the table rewrite fails, init warns and keeps the packaged agent tables.
Non-interactive init skips the displayed scan and keeps the packaged agent
tables. Clone setup uses the shared `coga.toml` as it stands.

If launch cannot resolve the configured executable, its error names the
missing CLI and points to the `cli` key in `[agents.<name>]` in `coga.toml`.
Set that key to the name or path of your agent CLI.

## The operator's name

`user` in `coga.local.toml` is the name tickets and agents use for you. Init
writes it from `--user`, which must be non-empty with no `"` or `\`; Coga
never guesses it from Git or the OS, because a wrong guess fails quietly
against ticket `owner:` tokens. `user` is accepted only in the gitignored
`coga.local.toml`. Read-only surfaces such as `status`, `show`, `validate`,
`usage` and `--help` work without it. `coga validate` reports a `missing-user`
warning. Commands that require the local identity, such as `coga create` and
`coga bump`, report how to set it with `coga init --user NAME`.
On a clone, init edits an existing `coga.local.toml` in place, preserving its
other keys and comments, and writes `user` only after the agent skill links
are wired, so a failed run can be retried.

## Configured contexts root

A fresh init scaffolds local contexts at `coga/contexts/`, the default in the
shipped template. A template can set `[layout] contexts` in its own
`coga.toml` to move that scaffold to a different root. The new destination
must be absent. Init checks it before scaffolding and cleans up the relocated
tree if a later initialization step fails. Moving the root in an initialized
repo is a manual change
([coga/context-layout](../context-layout/SKILL.md#moving-the-contexts-root)).

## Migrating existing definitions

Clone setup and package upgrades leave existing local definitions in place.
To adopt package fallbacks while preserving customization, activation and
saved state, follow the
[migration and rollback procedure](../recurring/templates/package-definitions-migration.md).
