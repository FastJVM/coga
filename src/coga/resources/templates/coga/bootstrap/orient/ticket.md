---
title: Orient an agent in this coga/ repo
agent: claude
contexts:
  - coga/architecture
  - coga/principles
  - coga/cli
---

## Description

Stateless launch target. `coga launch bootstrap/orient` drops an agent
into a fully-composed coga-aware session — global rules, repo context,
and the orientation contexts (principles, architecture overview, cli index).
No ticket, no workflow, no lock.

The point: skip the "open `claude` in the repo and re-explain the
project" dance. Use this when the human wants to direct ad-hoc work —
triage, edits to coga/ itself, discussion — without committing to a
specific ticket up front. For ticket-bound work, exit and `coga launch
<slug>`; that loads the ticket's own contexts, workflow step, and skill.
There is no task-ownership lock — see `coga/architecture`.

## Context

What the agent should do once oriented:

- The composed prompt already includes three short orientation contexts
  (principles, the architecture overview, and the `coga/cli` command index)
  because this ticket's own `contexts:` list names them — a ticket loads only
  the contexts it lists. The overview and index link the focused topics
  (`coga/lifecycle`, `coga/launch`, `coga/sync`, ...) that own each detailed
  contract; those are not in this prompt. When the work needs one, read that
  topic's file from the configured contexts directory or the bundled package,
  and use `coga <command> --help` for exact syntax.
- Wait for the human to direct. Don't `coga create` or `coga ticket` of your own
  initiative.
- If asked for a triage view, run `coga status` and summarize.

This is a bootstrap ticket, not a `tasks/` ticket: stateless — no status,
no owner, no log, no lock — every launch is independent and concurrent
launches are safe. Don't edit this ticket except to swap `agent:` to
whichever agent type matches your `coga.toml`.
