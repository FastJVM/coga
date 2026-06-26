---
title: Orient an agent in this coga-os/ repo
mode: interactive
assignee: claude
contexts:
  - coga/architecture
  - coga/principles
  - coga/cli
---

## Description

Stateless launch target. `coga launch bootstrap/orient` drops an agent
into a fully-composed coga-aware session — global rules, repo context,
and the canonical coga/* contexts (architecture, principles, cli).
No ticket, no workflow, no lock.

The point: skip the "open `claude` in the repo and re-explain the
project" dance. Use this when the human wants to direct ad-hoc work —
triage, edits to coga-os/ itself, discussion — without committing to a
specific ticket up front. For ticket-bound work, exit and `coga launch
<slug>`; that gives the ticket's own contexts, workflow step, skill,
and a lock.

## Context

What the agent should do once oriented:

- The composed prompt already includes the canonical coga/* contexts
  (architecture, principles, cli). For deeper reference, `README.md`
  has more narrative; `docs/spec.md` has the config / frontmatter / error
  contracts.
- Wait for the human to direct. Don't `coga create` or `coga ticket` of your own
  initiative.
- If asked for a triage view, run `coga status` and summarize.

This is a bootstrap ticket, not a `tasks/` ticket: stateless — no status,
no owner, no log, no lock — every launch is independent and concurrent
launches are safe. Don't edit this ticket except to swap `assignee` to
whichever agent type matches your `coga.toml`.
