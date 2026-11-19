---
title: Show task status
---

## Description

`coga status` is a default alias to `launch --read-only bootstrap/status --`.
Launch executes the sibling `ticket.py` with trailing arguments, including
`--help`. This command has no agent phase, workflow, task or blackboard.

List local tasks, optionally filtered by directory, depth, terminal status or open blockers. Sorting, narrow tables, recurring summaries and local Git hints are presentation policy in the sibling script. No network refresh occurs; Git hints use existing refs.

Successful reports exit 0; argument and configuration errors exit 2. The
read-only invocation needs existing valid configuration, but no configured
user, agent, TTY or network. Streams pass through; aliases announce their
expansion on stderr. The effects boundary belongs to
[coga/launch](context:coga/launch); report behavior belongs here and in
`ticket.py`. Copy this entire directory to `coga/bootstrap/status/` to
customize the report locally. A local definition wins over the wheel and
stops receiving upstream changes until removed or reconciled by its owner.
Shared core APIs remain imports; no report imports another report.

## Context

Related operator guidance: [coga/lifecycle](context:coga/lifecycle).
