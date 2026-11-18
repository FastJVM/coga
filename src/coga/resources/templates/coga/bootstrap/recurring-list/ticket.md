---
title: List recurring work
---

## Description

`coga recurring list` is a fixed subcommand adapter to `launch --read-only bootstrap/recurring-list --`.
Launch executes the sibling `ticket.py` with trailing arguments, including
`--help`. This command has no agent phase, workflow, task or blackboard.

Show the effective local and package catalog, selection and load errors, firing times, clone ledger state and instantiated period tasks. Unselected bundled definitions are summarized as available. This inspects schedules without admitting or launching work.

Successful reports exit 0; argument and configuration errors exit 2. The
read-only invocation needs existing valid configuration, but no configured
user, agent, TTY or network. Streams pass through; aliases announce their
expansion on stderr. The effects boundary belongs to
[coga/launch](context:coga/launch); report behavior belongs here and in
`ticket.py`. Copy this entire directory to `coga/bootstrap/recurring-list/` to
customize the report locally. A local definition wins over the wheel and
stops receiving upstream changes until removed or reconciled by its owner.
Shared core APIs remain imports; no report imports another report.

## Context

Related operator guidance: [coga/recurring/scheduling](context:coga/recurring/scheduling).
