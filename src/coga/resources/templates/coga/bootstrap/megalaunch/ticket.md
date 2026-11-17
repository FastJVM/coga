---
title: Run the work queue
---

## Description

Stateless script command for `coga megalaunch` and `coga pick`. The sibling
`ticket.py` invokes the complete wheel-owned `coga_edge.megalaunch` policy.
No task or agent session is created for the command itself.

[coga/megalaunch](context:coga/megalaunch) owns selection, service order,
dependency drain, attempt budgets, liveness, gates, summary and exit behavior.
[coga/script-tickets](context:coga/script-tickets) owns invocation, help,
streams and interrupt handling. Queued work remains agent-only. Shared claim,
held-child release and admission transactions cannot be replaced by policy.

For a complete local fork, copy this directory and the implementation as
specified by [coga/edge-code](context:coga/edge-code). A shim edit alone does
not expose the queue implementation.
