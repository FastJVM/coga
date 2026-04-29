---
name: relay/cli
description: The relay CLI surface — what each command does, the flags that matter, and which command to reach for when. Loaded by ticket-less bootstrap shims so an oriented agent doesn't have to discover commands by trial.
---

# Relay CLI

Eight commands. Everything else is a flag or subcommand. The model
beneath them lives in `relay/architecture` — read that for primitives
and prompt composition. This context is just the operator's reference.

## relay init [PATH] [--update]

Scaffold `relay-os/` in `PATH` (default `.`), or with `--update` refresh
the relay-managed bits in the current repo.

- `relay init mycompany` — fresh scaffold; refuses if `relay-os/` exists.
- `relay init --update` — pull latest CLI + `_*` templates + `bootstrap/`
  + `skills/bootstrap/` from upstream. Leaves `relay.toml`, `rules.md`,
  user contexts, and user skills untouched.

## relay create "\<title\>"

Scaffold a `draft` ticket and auto-launch `bootstrap/ticket` to fill in
workflow / contexts / assignee / body. Human entry point.

- `-d "<one-liner>"` — seed the description.
- `--no-launch` — scaffold only; for scripted use.
- `--check-recurring` — scan `recurring/` and scaffold any due tasks
  (cron entrypoint; calling form for `scripts/cron.sh`).

## relay launch \<target\> [title]

Compose every relevant file (rules + repo context + ticket contexts +
current step's skill + blackboard + ticket body) into one prompt and
start the configured agent. Acquires `task.lock`.

- `relay launch <slug>` — accepts any unique prefix (git-short-SHA-style).
- `relay launch <slug> --force` — break a stale lock.
- `relay launch bootstrap/<name>` — stateless shim; no lock, concurrent
  launches safe. With a title arg, acts as a factory: scaffolds a new
  ticket from the shim's frontmatter and launches on it.

Agent type comes from the ticket's `assignee`, resolved through
`[assignees.<user>]` and `[agents.<type>]` in `relay.toml`.

## relay status [--all]

List tasks in the repo. Defaults to non-terminal (`draft`, `active`,
`paused`); `--all` includes `done`. Bootstrap shims have no status and
don't appear here.

## relay bump --task \<slug\>

Advance a workflow-bound task one step. Updates `step:`, appends a log
entry. Bumping past the last step marks the task `done`. The workflow
is frozen into the ticket at create time, so step semantics don't drift
mid-task. Errors cleanly on tickets without a workflow.

## relay panic --task \<slug\> --reason "..."

Agent gives up. Writes a blocker to the ticket, @-mentions the owner in
Slack, releases the lock. Exits non-zero. Reserved for genuinely stuck
states, not routine handoffs.

## relay feed --task \<slug\> --message "..."

Post a short FYI to the team Slack channel without changing task state.
Falls back to stderr if `[slack].webhook` isn't configured.

## relay --version

Package version + the upstream commit SHA `.relay/` was vendored from.
Useful for "is this fixed in your copy?" questions.

## Pick which command

- Starting a fresh task → `relay create "<title>"`.
- Continuing a known task → `relay launch <slug>`.
- Stateless/orientation session → `relay launch bootstrap/<name>`.
- Advancing a workflow-bound task → `relay bump`.
- Triage view → `relay status`.
- Surfacing a non-blocker note → `relay feed`.
- Surfacing a blocker → `relay panic`.

## What this context does NOT cover

- The mental model behind these commands (primitives, planes, prompt
  composition, locking) — see `relay/architecture`.
- Where source lives + how to test changes — see `relay/codebase`.
- Reference contracts (config schemas, frontmatter shapes, error
  tables) — see `docs/spec.md`.
