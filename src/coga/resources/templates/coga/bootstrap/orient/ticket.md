---
title: Orient an agent in this coga/ repo
agent: claude
contexts:
  - coga/architecture
  - coga/cli
---

## Description

Stateless launch target. `coga launch bootstrap/orient` (`coga chat`) drops
an agent into a coga-aware session with the architecture overview and the
cli index, without a ticket, workflow, or status. Use it when the human wants
to direct ad-hoc work — triage, edits to coga/ itself, discussion — without
committing to a ticket up front. For ticket-bound work, exit and `coga launch
<slug>`; that loads the ticket's own contexts, workflow step, and skill.

## Context

- The overview and index link the focused topics that own each detailed
  contract; those are not composed here. When the work needs one, read it
  from the configured contexts directory or the bundled package, and use
  `coga <command> --help` for exact syntax.
- Wait for the human to direct. Don't `coga create` or `coga ticket` of your own
  initiative.
- If asked for a triage view, run `coga status` and summarize.
- Discussion stays on `main`. Before the first edit, follow the
  **Checkout (runtime)** notice; `coga/checkouts/chat` owns the chat's branch
  and its one-chat-per-checkout guard.

Launch and usage lines are still logged. Don't edit this ticket except to
swap `agent:` to whichever agent type matches your `coga.toml`.
