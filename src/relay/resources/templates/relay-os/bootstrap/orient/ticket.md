---
title: Orient an agent in this relay-os/ repo
mode: interactive
assignee: claude1
contexts:
  - relay/architecture
  - relay/principles
  - relay/codebase
  - relay/current-direction
  - relay/project-stage
---

## Description

Stateless launch shim. `relay launch bootstrap/orient` drops an agent
into a fully-composed relay-aware session — global rules, repo context,
and the five canonical relay/* contexts (principles, architecture,
codebase, current-direction, project-stage). No ticket, no workflow,
no lock.

The point: skip the "open `claude` in the repo and re-explain the
project" dance. Use this when the human wants to direct ad-hoc work —
triage, edits to relay-os/ itself, discussion — without committing to a
specific ticket up front. For ticket-bound work, exit and `relay launch
<slug>`; that gives the ticket's own contexts, workflow step, skill,
and a lock.

## Context

What the agent should do once oriented:

- Read `README.md` for the CLI surface (`relay status / launch / bump /
  panic / feed / create / init`). The relay/* contexts cover principles
  + architecture + codebase + current-direction + project-stage; README
  covers the commands.
- Wait for the human to direct. Don't `relay create` of your own
  initiative.
- If asked for a triage view, run `relay status` and summarize.

This is a bootstrap shim, not a `tasks/` ticket: stateless — no status,
no owner, no log, no lock — every launch is independent and concurrent
launches are safe. Don't edit this shim except to swap `assignee` to
whichever agent nickname matches your `relay.toml`.
