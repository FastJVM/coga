---
title: Add bootstrap/retro skill for knowledge extraction on done tickets
status: draft
mode: interactive
owner: nick
assignee: claude1
skill: bootstrap/ticket
---

## Description

When a ticket transitions to `done`, sweep its `ticket.md`, blackboard, and
log for things that should graduate into reusable knowledge — and surface
the proposal as a PR the human reviews like any other diff.

This is Relay's "cleanup" story for done tickets: not archival (git is the
archive), but **knowledge extraction**. Each completed ticket is a chance
to tune the next one.

## What the retro extracts

- **Contexts.** Domain facts the executor learned mid-task that aren't yet
  in any `relay-os/contexts/*.md`. Propose new context entries or
  additions to existing ones.
- **Skills.** Repeated step patterns that should be promoted to
  `relay-os/skills/*` (or tweaks to existing skills).
- **Mismatches.** Places where the workflow / contexts / assignee that
  `bootstrap/ticket` chose turned out wrong. These are signal for tuning
  future bootstrap decisions, not just this ticket.

## Shape

- New skill at `relay-os/skills/bootstrap/retro/SKILL.md`. The skill reads
  the done ticket + its blackboard + log, drafts proposals.
- **Output 1 — PR.** Skill emits diffs against `relay-os/contexts/` and
  `relay-os/skills/`, opens a branch `retro/<task-slug>`, pushes, opens a
  PR. The PR body links back to the source ticket.
- **Output 2 — Slack.** Posts a one-line summary + PR link to a
  configured channel. Config: `[notifications.slack]` in `relay.toml`,
  webhook URL via `env:SLACK_WEBHOOK` (per the secrets-in-local-toml rule
  in `vision.md`).
- **Trigger.** `relay bump` on transition to `done` auto-launches
  `bootstrap/retro` on the same task. The retro runs *after* the task
  lock is released — it's post-completion analysis, not part of execution.
- **Granularity.** One retro PR per task. Cheaper to review than a batched
  weekly diff, and each PR stays scoped to one ticket's lessons.

## Open questions

- Does retro run synchronously inside `relay bump`, or async via a
  background queue? Synchronous is simpler; async avoids stalling the
  human waiting for `bump` to return.
- Skip retro for trivially-small tickets? (e.g. fewer than N steps, or no
  blackboard activity.) Probably yes — retros on one-line tickets are
  noise.
- Where does the slack webhook config live in `relay.toml`? Suggest
  `[notifications.slack] webhook = "env:SLACK_WEBHOOK"` and a
  `channel_default` plus optional `channel_per_team` map.

## Out of scope

- Auto-merging retro PRs. Always human-reviewed.
- Cross-task retros / weekly digests. Defer until single-task retros are
  shipped and we know what patterns recur.

## Why now

Discussion thread on 2026-04-27: agreed git history is the archive (no
file pruning needed), but completed tickets are a knowledge source we're
currently throwing away. This is the post-`done` cleanup that actually
matters.
