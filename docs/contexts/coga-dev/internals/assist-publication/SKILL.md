---
name: coga-dev/internals/assist-publication
description: The recorded assist's alignment loop and `COGA_ASSIST_*` identity, and where a human-step assist's lifecycle, script, and audit writes are published (control only, never the PR branch), how failures behave, and what the assist identity does and does not authorize.
---

# Assist attribution

Launch sets `COGA_ASSIST_AGENT` for an explicitly requested assist on an
owner-held step. `pr_assist.assist_session_from_env` checks the configured
agent and scopes the audit identity to the supervised ticket. Lifecycle
commands use the identity for attribution. The owner handles checkout and
PR state through Git.
