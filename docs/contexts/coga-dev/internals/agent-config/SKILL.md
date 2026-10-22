---
name: coga-dev/internals/agent-config
description: How `[agents.*]` config is parsed and resolved — the key-level shared/local merge, `default_agent` validation and freezing, `peer` resolution and its live-config asymmetry, and the deferred per-ticket reviewer.
---

# Agent configuration internals

User-facing key meanings live in comments in the shipped
`src/coga/resources/templates/coga/coga.toml`; this page holds what a change
to `src/coga/config.py` (`AgentType`, `_parse_agents`,
`_parse_default_agent`, `Config.default_agent`) or `src/coga/bump.py`
(`resolve_other_agent`) must preserve. Tickets name types directly in
`agent:`; there is no per-user nickname layer, and `Config.agent_type` fails
loud on an undefined name.

## Shared/local merge

`[agents.*]` is machine capability, so unlike `[layout]` it may appear in
both files. `_parse_agents` merges at the **key** level: a local table
overrides individual keys of the shared one and inherits the rest, and a
local-only table appends a type. Required-key (`cli`, `file`) and type checks
run on the merged result. An explicit local `launch_args = ""` clears a
shared value. `file` is parsed and required, but launch does not currently
read it. Removed keys (`auto`, `skip_permissions`, `skip_permissions_argv`)
raise a migration error naming the file that holds them
([coga/configuration](../../../coga/configuration/SKILL.md)).

## The default agent

`Config.default_agent()` is the type stamped into `agent:` at first
activation (or at a create straight into a live status), and the fallback for
`coga retire`, the autofix analyst, and the authoring interviewer.
Precedence: local `default_agent`, then shared `default_agent`, then the
first-declared table in the merged `[agents.*]` (the behaviour from before
the key existed). The key is local-capable on purpose, unlike shared-only
`[autofix]`: which vendor a machine can run right now is an operator fact,
and a local table cannot reorder the shared ones, so before the key existed a
machine had no way to change its default.

Each value present must be a non-empty string naming a type in the
**merged** table, or config load fails naming the supplying file and listing
known types. Both values are checked even when the local one wins. A shared
value naming a type some clone declares only locally breaks other clones on
their next command; that failure is loud, not a silent fallback.

Resolved once, then frozen: activation writes it into `agent:`, so later
changes affect only tickets activated afterwards. An existing recurring
period ticket keeps its agent even when a forced rerun reactivates it; the
new default applies from the next materialized period. Read-only surfaces
(status, show, compose, validate) report the default activation *would*
stamp, and the `other-agent` peer of an unactivated ticket derives from it.

More specific knobs win: a recurring agent-backed launch uses `--agent`,
else the period's `agent:`; the autofix analyst uses `--agent`, else
`[autofix] agent`, else the default; the authoring interviewer reaches the
default only after `[authoring] agent`, `COGA_AUTHORING_AGENT`, and the
ticket's own `agent:`. The packaged `bootstrap/ticket`, `bootstrap/orient`,
and onboarding tickets pin `agent: claude`, which outranks the default.
Interactive `coga init` may write the key (`commands/init.py`
`_write_default_agent`); see [coga/init](../../../coga/init/SKILL.md).

## `peer` resolution

- The target must be another configured type; naming itself or an unknown
  type fails config load.
- Global and one-directional per type; it cannot vary by ticket or workflow.
  A per-ticket reviewer was deferred as unneeded policy surface.
- With no `peer`, "other" is the single configured type that is not the
  main agent, zero-config for two-agent repos. With three or more types and
  no `peer`, `resolve_other_agent` fails loud asking for one.
- The asymmetry: the ticket freezes its main `agent:`, but `peer` is read
  from **live** config at each handoff or launch. A `peer` set only in
  `coga.local.toml` picks a different reviewer on that machine without
  rewriting ticket routing. That is accepted, so a machine can use a third
  agent teammates do not have; one policy for everyone goes in shared
  `coga.toml`.

Step roles and handoff mechanics belong to
[coga/workflows](../../../coga/workflows/SKILL.md) and
[coga/lifecycle](../../../coga/lifecycle/SKILL.md); spawning to
[agent spawn](../agent-spawn/SKILL.md).
