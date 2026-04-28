---
title: Token-budget-aware idle execution of low-priority tickets
status: draft
mode: interactive
owner: nick
assignee: claude1
skill: bootstrap/ticket
---

## Description

A Claude session has a token budget. When the user's primary task is
done but tokens remain, that budget is otherwise lost — the session
ends and unused capacity is gone. Idea: when there's enough budget
left, opportunistically pull a low-priority ticket from a queue and
run it. Trades wasted capacity for cheap maintenance work.

## What this looks like

A new ticket status / tag like `idle-eligible`, plus a relay command
that picks one and launches it:

- `relay idle-pick [--min-tokens N]` — surveys `idle-eligible` tickets
  ordered by smallest-first (or by an explicit priority field), prints
  the slug to launch.
- The agent (Claude Code) checks remaining context at the natural
  end-of-task pause. If above threshold, runs `relay idle-pick` and
  launches the result.
- Tickets shaped for this should be small, well-scoped, and not
  require human interaction — the user already left.

## Candidate idle-eligible work

- `bootstrap/dream` sweep (broken refs, stale locks, gaps).
- `relay validate --json` and propose fixes to any errors.
- Retro extraction on done tickets that haven't had retros yet
  (depends on the retro ticket).
- Dependency / template drift check (was the `relay-os/.gitignore`
  drift catchable this way?).
- Open small cleanup PRs that have been sitting in a queue.

## Open questions

- **Where does the agent get its token budget from?** The session has
  a context window but no exposed counter. Options: rely on the agent
  self-reporting ("I have ~100k tokens left"), use a heuristic ("if
  fewer than N turns elapsed"), or a `claude` CLI flag we haven't seen.
  Possibly out of our control — may need to be advisory only.
- **What counts as "enough"?** A floor like 50k tokens? Per-ticket
  estimates so the agent picks tickets that fit?
- **How does the agent know it's at the natural pause?** A hook on
  task completion? An explicit `relay idle-pick` invocation in the
  human's prompt template?
- **Concurrency / lock semantics.** If the user comes back mid-idle,
  does the idle task get paused, abandoned, or finished?

## Out of scope

- Building a full priority queue / scheduler — start with the simplest
  thing (a flag on the ticket + first-match) and only add structure
  when needed.
- Cross-session continuation (a half-finished idle task carrying over
  to the next session). Probably wants a clean abandon-on-end policy
  for v1.

## Why now

We're building up a backlog of small maintenance tickets (retro
proposals, validate fixes, dream sweeps). Right now they only run
when a human explicitly schedules them. The token-budget angle is a
zero-effort path to chip away at that backlog. Worth at least
prototyping.
