---
title: Move automerge sweep out of relay status into a recurring task
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

`relay automerge` currently runs as a silent side effect inside
`relay status`. That violates two things:

- **Read-only-command expectation.** `relay status` looks like a
  triage `cat` of the filesystem; users don't expect it to shell out
  to `gh pr view`, mutate ticket state, or post to Slack. It also
  makes the command network-dependent and slow, and it can fail in
  ways that aren't visible.
- **`relay/principles` fail-loud rule.** The status path explicitly
  swallows `gh` errors (missing CLI, unauthed, offline). The whole
  point of fail-loud is "the worst failure is silent-wrong-answer."
  An automerge sweep that quietly no-ops because `gh` isn't installed
  is exactly that failure shape.

Move the long-tail catch-up to a **recurring task** under
`relay-os/recurring/` whose body runs `relay automerge` and bumps
itself when done. Cron-driven via the existing
`relay-os/scripts/cron.sh` → `relay recurring check` path.

Tradeoff acknowledged: every scheduled firing scaffolds a fresh
ticket even when nothing has merged, so most runs are no-op tickets.
Nick chose this over a direct `cron.sh` hook so that runs are
*visible* (ticket + log + Slack line on bump), at the cost of some
inbox noise. Keep the schedule modest (e.g. once/day or once/hour
on weekdays) to keep the noise bounded.

## Cleanup

- Remove the opportunistic call from `commands/status.py`. After
  this change, `relay status` is once again pure filesystem read.
- Keep `relay automerge` (the explicit CLI surface) and the
  `post-merge` git hook unchanged — both remain the active-developer
  paths.

## Open questions

- **Schedule cadence for the recurring sweep.** Daily? Hourly on
  weekdays? Goal is "long-tail catch-up after teammate merges,"
  which doesn't need to be fast.
- **Should the recurring task self-delete on no-op runs?** If yes,
  noise stays bounded. If no, we get a clean log of every sweep.
  Probably no — Dream's validate-drift can later sweep stale done
  tickets if it becomes a problem.
- **Workflow shape.** Does this want a workflow at all? A single
  `script`-mode step that runs `relay automerge` and bumps to done
  is enough. No human review needed for a sweep that's almost always
  a no-op.

## Out of scope

- Targeted freshness check at `relay launch <slug>` time. That's the
  sibling ticket `verify-ticket-freshness-on-relay-launch` — same
  underlying motivation, different hook, ships independently.
- Changing the auto-bump Slack message or attribution shape — that
  was settled in `auto-bump-tickets-when-their-pr-merges`.
- Removing the `post-merge` git hook. It still covers the
  active-developer-pulls case and is the lowest-latency path.
- Replacing the explicit `relay automerge` command. It stays as
  the on-demand surface and the recurring task's entry point.

## Why now

Came up while running `relay status` mid-orient session and noticing
ticket state seemed to be changing as a side effect of a read-only
command. Nick flagged this as a smell.
