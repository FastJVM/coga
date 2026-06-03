---
name: digest/post
description: One-step script workflow that flushes the spooled state-change events into one Slack digest.
steps:
  - name: flush
    skills:
      - relay/digest/flush
    assignee: agent
---

## flush

Script step. Runs `relay/digest/flush`, which calls `relay digest`: drain the
`recurring/digest/` spool, group the day's events project → person → ticket,
post one sectioned message to the shared channel, and empty the spool. An empty
spool is a silent no-op.
