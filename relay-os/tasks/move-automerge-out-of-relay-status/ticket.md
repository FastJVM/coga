---
title: Move automerge sweep out of relay status into a recurring task
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/architecture
- relay/principles
- relay/cli
- relay/codebase
- dev/code
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
  - name: open-pr
    skills:
    - code/open-pr
  - name: review
    assignee: owner
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

The fix is narrow: remove that side effect so `relay status` is once
again a pure filesystem read. `relay automerge` stays as the explicit
catch-up command — it already sweeps the right ticket states and bumps
only on a merged PR.

> **Design pivot (2026-05-21):** the original plan moved the sweep to
> a recurring task. That was dropped. A cron-driven sweep is still the
> intended long-tail mechanism, but it is a separate future ticket.
> See the blackboard design note for the agreed three-ticket split.

## Cleanup

- Remove the opportunistic call from `commands/status.py`. After
  this change, `relay status` is once again pure filesystem read.
- `relay automerge` (the explicit CLI surface) is left unchanged.
  The `post-merge` git hook removal is split into the sibling ticket
  `remove-post-merge-automerge-hook`.

## Resolved

The three original open questions (cadence, self-delete, workflow
shape) are moot — they all belonged to the recurring-task approach,
which was dropped. A cron-driven sweep is planned as its own future
ticket. See the blackboard design note.

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
