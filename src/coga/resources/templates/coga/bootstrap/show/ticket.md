---
title: Show a ticket
---

## Description

`coga show` is a default alias to `launch --read-only bootstrap/show --`.
Launch executes the sibling `ticket.py` with trailing arguments, including
`--help`. This command has no agent phase, workflow, task or blackboard.

Render a uniquely resolved task or bootstrap ticket. Task views include the derived operator and every retained log line; bootstrap views contain only the ticket. Missing or ambiguous targets exit 2. Read files directly for scripting.

Successful reports exit 0; argument and configuration errors exit 2. The
read-only invocation needs existing valid configuration, but no configured
user, agent, TTY or network. Streams pass through; aliases announce their
expansion on stderr. The effects boundary belongs to
[coga/launch](context:coga/launch); report behavior belongs here and in
`ticket.py`. Copy this entire directory to `coga/bootstrap/show/` to
customize the report locally. A local definition wins over the wheel and
stops receiving upstream changes until removed or reconciled by its owner.
Shared core APIs remain imports; no report imports another report.

## Context

Related operator guidance: [coga/tickets/authoring](context:coga/tickets/authoring).
