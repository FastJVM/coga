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

Coga drives an agent CLI but never installs one or says where to get one; an
interactive init offers only the supporting CLIs `git` and `gh`, notes a
missing `op`, and runs nothing without a yes. Init runs before any `coga.toml`
exists, so an interactive fresh init scans `PATH` for every agent CLI in
`coga.dependencies.AGENT_CLIS` and prints one row per agent, found or not. It
asks nothing.

That scan configures the new repo. When it found at least one agent, init
comments out (never deletes) the `[agents.*]` table of each supported agent it
did not find, so enabling one later is an uncomment. No `default_agent` key is
written: the default is the first table the file still declares, which is the
first agent found, and delivered tickets that named the template's default,
such as the onboarding ticket's `agent:`, are repointed at it. When the scan
found nothing, the packaged `coga.toml` stays as shipped, declaring every
supported agent, and the next steps say an agent-backed command needs one
installed. The rewrite is all or nothing: if the result would not parse back
to the expected declarations, init keeps the packaged file and warns. A
non-interactive init prints no scan and leaves the file as shipped. The clone
path never scans or rewrites `coga.toml`: it is committed team config.

After init, a configured agent CLI that cannot be found fails the launch with
`Agent CLI '<cli>' not found. Set \`cli\` in [agents.<name>] in coga.toml`:
the remedy is always that table, never an install by Coga.

## The operator's name

`user` in `coga.local.toml` is the name tickets and agents use for you. Init
writes it from `--user`, which must be non-empty with no `"` or `\`; Coga
never guesses it from Git or the OS, because a wrong guess fails quietly
against ticket `owner:` tokens. `user` is accepted only in the gitignored
`coga.local.toml`. Read-only surfaces such as `status`, `show`, `validate`,
`usage` and `--help` work without it and `coga validate` warns `missing-user`; every
command that creates or moves work fails with `Run coga init --user <name>`.
On a clone, init edits an existing `coga.local.toml` in place, preserving its
other keys and comments, and writes `user` only after the agent skill links
are wired, so a failed run can be retried.

## Configured contexts root

A fresh init scaffolds local contexts at `coga/contexts/`. It relocates them
only when the template's own `coga.toml` sets `[layout] contexts`; the shipped
template does not. The destination must not already exist: init refuses
before writing anything rather than merge into it, and a later failure removes
the relocated tree with the rest of the partial init. Moving the root in an
initialized repo is a manual change
([coga/context-layout](../context-layout/SKILL.md#moving-the-contexts-root)).

## Migrating existing definitions

Clone setup and package upgrades leave existing local definitions in place.
To adopt package fallbacks while preserving customization, activation and
saved state, follow the
[migration and rollback procedure](../recurring/templates/package-definitions-migration.md).
