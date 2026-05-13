---
title: Split control plane into `relay mark`; decouple launch and bump from status
status: done
mode: interactive
owner: nick
human: nick
agent: claude1
assignee: claude1
contexts:
- relay/codebase
- relay/architecture
- relay/principles
- dev/code
---

## Description

The CLI today conflates two planes:

- **Control plane** (`status`: draft / active / paused / done) — owned
  by `relay launch` (sets active) and `relay bump` (sets done on the
  final step).
- **Workflow plane** (`step`) — owned by `relay bump` (advances steps).

Plus: `relay create` is an alias for `relay launch bootstrap/ticket`,
which scaffolds + activates + opens the agent harness in one
indivisible operation.

This ticket separates the planes. Each command does one thing.

**Depends on `rewrite-slack-messages` being merged first.** The format
strings used here all ship from that ticket; this one reuses them and
re-routes which command emits which.

## New command surface

| Command | Does | Slacks |
|---|---|---|
| `relay create "title"` | scaffold ticket in `draft` (replaces the bootstrap-factory alias) | ✨ created |
| `relay mark active <slug>` | status `draft|paused → active` | 🚀 activated |
| `relay mark paused <slug>` | status `active → paused` | ⏸️ paused |
| `relay mark done <slug> [--message …]` | status `active → done` | 🎉 finished |
| `relay launch <slug>` | open agent harness; errors if status != active | silent |
| `relay bump <slug>` | advance one step; errors past last step or no-workflow | 👉 advanced |
| `relay panic / slack / status / recurring check` | unchanged | unchanged |
| `relay automerge` | unchanged externally; routes through mark-done internally | 🎉 finished (automerge variant) |

`mark` is a Typer namespace with three subcommands. Verb is the literal
`status` value — direct mapping to the frontmatter field, no
grammatical drift.

## Behaviors

- **`relay launch <slug>`** no longer changes status. On a `draft`
  ticket: error with
  `error: ticket is draft. run \`relay mark active <slug>\` first.`
  No 🚀 / ✨ Slack posts from launch — those move to `mark active` and
  `create` respectively.
- **`relay bump <slug>`** no longer marks done. On the last step or a
  no-workflow ticket: error with
  `already on final step. run \`relay mark done <slug>\` to finish.`
- **`relay automerge`** routes through the same `mark done` code path
  used by manual finish, so all "done" events flow through one
  function. The Slack message keeps the automerge-specific shape (no
  actor, PR link) — that's a format-time branch in the formatter, not
  a separate post path.
- **`relay create "title"`** becomes a real Typer command in
  `src/relay/commands/create.py`. Scaffolds the ticket directory in
  `draft` and posts ✨. No agent launched. Today's
  `[aliases].create = "launch bootstrap/ticket"` line is removed from
  `relay-os/relay.toml`.
- **Bootstrap `ticket` factory shim.** Decide during implementation:
  delete it (preferred — `relay create` replaces its only use), or
  keep it as a deprecated path with a warning. Suggest: delete.
- **No new aliases** (`relay activate`, etc.). The consistency of
  `relay mark <state>` is the value; aliases would defeat that.
  Agents type the longer form without complaining.
- **No `--launch` shortcut on `relay create`.** Three explicit steps
  to start fresh work: `create` → `mark active` → `launch`. Verbose
  but each command does one thing.

## Slack messages

All format strings come from ticket #1 (`rewrite-slack-messages`).
This ticket only re-routes which commands fire which strings:

- The 🚀 activated post moves from `commands/launch.py` to
  `commands/mark.py` (the `active` subcommand).
- The ✨ created post moves from `commands/launch.py` to
  `commands/create.py`.
- The 🎉 finished post (manual) moves from the `bump` final-step path
  to `commands/mark.py` (the `done` subcommand).
- The 🎉 finished post (automerge) keeps firing from `automerge.py`,
  but via the shared mark-done code path.
- The 👉 advanced post stays in the bump path; the "→ done" branch
  inside that formatter goes away (bump can no longer transition to
  done).

After this ticket lands, the format strings shipped in #1 that handle
"bump → done" become dead code and should be removed in this ticket's
PR.

## Tests

- New `tests/test_mark.py`:
  - `mark active` on a draft ticket → status becomes active, 🚀 posts
  - `mark active` on a paused ticket → status becomes active, 🚀 posts
  - `mark active` on an already-active ticket → no-op or error (decide)
  - `mark paused` on an active ticket → status becomes paused, ⏸️ posts
  - `mark paused` on a draft / done / paused ticket → error
  - `mark done` on an active ticket → status becomes done, 🎉 posts
  - `mark done` on a draft / paused ticket → error (must be active)
  - `--message` piggybacks on done correctly
- Update `tests/test_launch.py`: launch on draft errors with the
  expected hint; launch on active opens the harness silently (no Slack
  post fires).
- Update `tests/test_bump.py`: bump past last step errors; bump on a
  no-workflow ticket errors; mid-workflow bump still posts 👉.
- Update `tests/test_automerge.py`: verify the mark-done path is
  invoked (status flips, lock releases, Slack fires with automerge
  shape).
- New `tests/test_create.py`: `relay create "title"` scaffolds a
  draft ticket directory, posts ✨, does not launch the agent, does
  not flip status.

## Documentation

- `README.md` — replace the command list with the new surface.
- `docs/spec.md` — update the CLI section, status transition
  semantics, error messages, and the `[aliases]` example (remove the
  `create` alias).
- `relay-os/contexts/relay/cli.md` — canonical agent-loaded reference;
  rewrite the "Pick which command" section and the `relay launch`,
  `relay bump`, `relay create` entries.
- `relay-os/contexts/relay/architecture.md` — confirm the two-plane
  model is reflected accurately (it already names control vs data, but
  the command examples may need refresh).
- `example/` fixture — update if any seeded tickets demonstrate the
  old `relay launch` activation pattern.

## Files likely touched

- `src/relay/commands/mark.py` (new — Typer namespace with three subcommands)
- `src/relay/commands/create.py` (new — replaces the alias)
- `src/relay/commands/launch.py` (drop activate logic + scaffold logic
  + their Slack posts; add draft-error path)
- `src/relay/commands/bump.py` (drop done logic; add past-last-step
  error)
- `src/relay/bump.py` (refactor — `mark_done` core moves to a
  mark-module helper, `advance_step` stays)
- `src/relay/automerge.py` (call the new mark-done helper instead of
  the old `bump.mark_done`)
- `src/relay/cli.py` (register `mark` and `create` commands)
- `relay-os/relay.toml` (drop the `create` alias)
- `relay-os/bootstrap/ticket/` (delete; documented above)
- `tests/`

## Out of scope

- Aliases for the new commands (`relay activate`, etc.) — see above.
- A `--launch` shortcut on `relay create`.
- Rewinding (`active → draft`, `paused → draft`) — left as hand-edit.
- Auto-finish convenience (e.g. final bump auto-marking done) —
  explicitly rejected; the whole point is one command per concern.
- Human vs agent role tagging in messages — separate ticket if/when
  the code can tell them apart reliably.

## Why now

Surfaced during the same chat orient session that produced ticket #1.
With the message rewrite making transitions explicit, the conflation
of planes inside `launch` and `bump` becomes obviously wrong: a single
command changing both `status` and `step` (or both `status` and
"open the harness") muddies what the team sees and what the docs have
to explain. Splitting them simplifies both the CLI and the agent
contexts that document it.

## Knock-on cleanup once this lands

- The `bootstrap/ticket` shim is gone, but `bootstrap/orient` and any
  others stay — verify the bootstrap pattern docs still make sense
  with one fewer example.
- `relay validate` may have checks that assume the old aliases — sweep
  and update.
- The `[slack].gifs` config still applies to the moved 🎉 / 🚨 posts;
  no config change needed.
