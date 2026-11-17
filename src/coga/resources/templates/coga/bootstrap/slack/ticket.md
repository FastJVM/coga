---
title: Post an FYI
---

## Description

Stateless script command for `coga slack`. The sibling `ticket.py` invokes the
complete wheel-owned `coga_edge.slack` implementation. No task or agent
session is created for the command itself.

`coga slack --task <ref> --message <text> [--important]` is a default alias
for `coga launch bootstrap/slack -- ...`. The `--task` ref is a task ID,
id-slug, or a `bootstrap/<name>` command ticket. The script posts one
notification, appends a `slack: <message>` audit line for that ref, and prints
`posted`. [coga/notifications](context:coga/notifications) owns surface,
destination and failure semantics; the [producer inventory](context:coga/notifications/producers)
owns this command's row. [coga/script-tickets](context:coga/script-tickets)
owns invocation, help, streams and interrupt handling.

An FYI is never a completion signal, for an ordinary ticket or a stateless
bootstrap session. A stateless agent-backed command ends its session with
`coga mark done bootstrap/<name>`.

For a complete local fork (for example a different message format), copy this
directory and the implementation as specified by
[coga/edge-code](context:coga/edge-code). A shim edit alone does not expose
the FYI implementation.
