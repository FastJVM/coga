---
title: Rename `relay feed` → `relay slack` and add `bump --message`
status: done
mode: interactive
owner: nick
human: nick
agent: claude1
assignee: claude1
---

## Description

Two small consolidations to the relay Slack surface, falling out of
a design discussion about which broadcasts the team actually needs.

### 1. Rename `relay feed` → `relay slack`

`feed` was named as if it were a generic "team feed" abstraction, but
the codebase is openly Slack-specific (`relay/slack.py`,
`[slack]` config table, `SLACK_WEBHOOK_URL` env var, `slack_enabled`
flag). The provider-agnosticism the name implied is fiction — better
to be honest. Rename the command to `relay slack` so what the command
does is obvious from its name.

### 2. Add `bump --message <text>`

Most "FYI" broadcasts an agent legitimately wants to send happen at
moments where it's also bumping the workflow step:

- **PR opened:** "advanced to step (pr) — PR opened: <link>"
- **Decision noted:** "advanced to step (implement) — talked to marc,
  skipping the cache invalidation step"

Today the agent has to either fire two messages (`bump` + a separate
`feed`/`slack` call) or attach the link to the blackboard and hope
the human checks. A `--message` arg on `bump` lets the agent
piggy-back the FYI onto the state-transition broadcast that already
fires.

## Why this shape (and what we ruled out)

We considered just **dropping `feed`/`slack` entirely** since most
state-machine transitions already broadcast (scaffolded, activated,
bumped, done, panicked, recurring scaffolded). The remaining cases:

- PR/deploy links mid-step → covered by `bump --message`.
- Soft blockers ("waiting on infra") → better expressed via a future
  `relay reassign` (out of scope for this ticket — see below) or
  `relay panic` if it really is blocking.
- Long-running script-mode progress → genuinely impossible to do
  cleanly from inside the agent's run; not worth designing for.
- **Manual-edit announcements** — the case that kept `feed`/`slack`
  alive. If a human hand-edits a ticket (reassigns, retitles, edits
  description), the team should know. The principle that "manual
  edits are first-class" rules out auto-watchers/audit hooks; the
  human's escape hatch is an explicit broadcast call. That's the
  command.

So `relay slack` survives, with a sharper purpose: **the manual
broadcast escape hatch** for both humans (after a hand-edit) and
agents (mid-step FYIs that don't fit a state transition).

## Implementation notes

- `commands/feed.py` → `commands/slack.py`. Update the Typer
  registration in `cli.py`. Existing code is small (one file, ~50
  LOC); the rename is mostly mechanical.
- `bump` gets an optional `--message` Typer arg. When set, append it
  to the existing Slack broadcast text in `commands/bump.py`. The
  three broadcast call sites in that file (no-workflow done, past-
  final-step done, step-advanced) all need the same treatment — keep
  the message arg consistent across them.
- Update `tests/test_commands.py` (current `feed` tests) to point at
  the new command name. Add tests covering `bump --message`.
- Update the base prompt block in `relay-os/prompt.md` (the section
  teaching agents about `feed`) — rename + reframe to "manual
  broadcast escape hatch" for non-transition events. Mention
  `bump --message` as the preferred path for transition-tied FYIs.
- Update `README.md` CLI surface section.
- Update `relay/cli` context (`relay-os/contexts/relay/cli.md`) — the
  command list, the "pick which command" decision tree, and the
  example `[aliases]` block (`feed` isn't aliased today, but the doc
  mentions it).
- `docs/spec.md` if it lists commands by name.

## Out of scope

- **`relay reassign`.** Came up in the same discussion as a softer
  alternative to `panic` for "I need someone else to take this."
  Needs its own design pass (does it require a `--reason`? does the
  new assignee become the owner? how does it differ from `panic` in
  who gets paged?). Separate ticket.
- **Auto-detecting hand-edits to ticket.md and broadcasting diffs.**
  Tempting but breaks "manual edits are first-class, no audit
  hooks." Not pursuing.
- **Multi-broadcast targets** (Discord, Teams, etc.). Codebase is
  Slack-specific by design today; if that ever changes the rename
  would need to be revisited.

## Acceptance

- `relay feed` is gone; `relay slack` exists with the same surface.
- `relay bump --message "..."` appends the text to the broadcast.
- Tests cover both commands.
- Prompt + README + CLI context reflect the new command name and
  the new `bump --message` arg.
