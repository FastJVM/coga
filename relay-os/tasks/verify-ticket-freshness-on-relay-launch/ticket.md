---
title: Verify ticket freshness at the start of relay launch (auto-bump if PR merged)
status: draft
mode: interactive
owner: nick
human: nick
agent: claude1
assignee: claude1
contexts:
- relay/architecture
- relay/principles
- relay/cli
- relay/codebase
- dev/code
---

## Description

Before `relay launch <slug>` composes the prompt and spawns an agent
against an active ticket, verify the ticket is still where the
filesystem says it is. Specifically: if the ticket has a PR link
under `## Dev` in its blackboard and that PR has merged on GitHub,
auto-bump the ticket *first*, then proceed against the new state
(or exit cleanly if the bump moved it to `done`).

This is the targeted analogue of the broader sweep tracked in
`move-automerge-out-of-relay-status`. They share the underlying
problem (ticket state drifting from PR state) but hit it from
opposite directions:

- The sweep covers tickets nobody is touching.
- This check covers the ticket someone is *about to touch* —
  exactly the moment stale state matters most.

The two ship independently. This one is small.

## Why this is the right hook

- **Cheap.** One `gh pr view` for the slug being launched. Not a
  full sweep across all active tickets.
- **Fail-loud-compatible.** The user is actively waiting for the
  agent to start, so a `gh`-missing or `gh`-unauthed warning is
  appropriate and visible — unlike the silent swallow inside
  `relay status`.
- **Composes with the harness loop.** `relay launch` already
  continues through consecutive agent steps in fresh processes
  (per `relay/cli`); this check is just an extra "is the starting
  state still correct?" before that loop begins.
- **Catches the failure mode that hurts most.** Spinning up an agent
  on a `step: review` ticket whose PR has already merged is exactly
  the wasted-token / wrong-action scenario the auto-bump system
  exists to prevent.

## Shape (sketch)

In `commands/launch.py` (or wherever `launch` resolves the ticket
ref), after loading the ticket but before composing the prompt:

1. Skip if the ticket isn't `active` or has no `## Dev` PR link.
2. Skip if the ticket isn't on its final workflow step (or has no
   workflow). Mid-workflow PR merges are intentionally left alone
   per the existing automerge scope.
3. Call into the `auto_bump_merged` helper (extracted in
   `auto-bump-tickets-when-their-pr-merges`) but scoped to a single
   ticket — likely a new `auto_bump_one(cfg, slug)` that the broader
   sweep can also call.
4. If the bump moved the ticket to `done`, print a clear message
   ("ticket already merged on PR #N, marked done — nothing to
   launch") and exit non-error.
5. If the bump advanced a step but the ticket is still active,
   continue the launch against the new step.
6. If `gh` is missing or unauthed, warn loudly with a one-line hint
   (`run \`gh auth login\``) and continue without bumping. Don't
   block launch on a missing dev tool.

## Open questions

- **Hard fail vs warn-and-continue when `gh` is unavailable?**
  Leaning warn-and-continue — not every contributor will have `gh`
  set up, and blocking launch on it would be hostile. Fail-loud is
  satisfied by the visible warning.
- **Skip flag.** Should `relay launch <slug> --no-verify` exist for
  the offline / known-stale-but-I-want-to-edit-anyway case? Probably
  yes — small surface, prevents the check from being a footgun.
- **Bootstrap shims.** They have no status, no PR link, no workflow.
  The check should no-op on shims by virtue of step 1 above, but
  worth adding an explicit early-return.

## Out of scope

- The recurring sweep that catches tickets nobody launches —
  tracked in `move-automerge-out-of-relay-status`.
- Changing the auto-bump Slack message or attribution — settled in
  `auto-bump-tickets-when-their-pr-merges`.
- Pre-launch checks for *non-merge* drift (e.g. PR closed without
  merging, branch deleted). Different problem, different ticket if
  it ever matters.

## Why now

Came up in the same orient session that produced
`move-automerge-out-of-relay-status`. Nick wanted the targeted
launch-time check called out explicitly so it can ship on its own
cadence rather than waiting on the recurring-sweep design.
