---
title: skip-permissions-option
status: draft
mode: interactive
owner: zach
human: zach
agent: claude
assignee: claude
contexts:
- relay/architecture
- relay/codebase
skills: []
workflow: code/with-review
---

## Description

Add a Relay launch option that lets a trusted ticket run Claude Code or
Codex without stopping for per-command permission/approval prompts. The
important constraint is scope: this must be opt-in per ticket, not a global
default that silently changes every launch.

The dangerous CLI argv should live in local configuration so each operator
chooses what their own machine is willing to run. Add a first-class optional
ticket frontmatter field named `skip_permissions`; when a normal task ticket
sets `skip_permissions: true`, `relay launch` should add the effective
agent's local `skip_permissions_argv` to the spawned command.

### Acceptance Criteria

- A normal task ticket can opt into permission-skipping behavior with
  `skip_permissions: true`. Existing tickets keep today's behavior when the
  field is absent or false.
- `skip_permissions` is a boolean optional canonical frontmatter field.
  Validation rejects non-boolean values.
- `relay.local.toml` can provide per-agent argv for the opt-in behavior using
  `skip_permissions_argv = "..."` under `[agents.<name>]`, without requiring
  dangerous machine-local choices to be committed to shared `relay.toml`.
  The value is a string parsed with `shlex.split`; bad types fail config load.
- `relay launch` applies the extra argv to both supported local agent CLIs:
  Claude Code and Codex. The behavior must work across supervised multi-step
  launches, including `code/with-review` agent rotation.
- If a ticket opts in but the current agent has no configured skip-permission
  argv, launch fails loud before spawning the agent rather than silently
  falling back to the normal permission mode.
- The extra argv is inserted after any `name_flag`/session-name argv and
  before the mode-specific argv/prompt payload. For example:
  `claude -n <title> <skip-argv> <prompt>` and
  `codex <skip-argv> exec <prompt>`.
- `--agent` launch overrides use the effective launch agent's local
  `skip_permissions_argv` for that first step; chained steps use the current
  ticket assignee's agent config.
- Bootstrap/discussion shims such as `relay chat` and `relay ticket` are not
  affected. This option applies to normal task tickets only.
- Script-mode tasks are not affected; they do not launch an agent CLI.
- Tests cover config parsing, command construction, default/no-op behavior,
  boolean validation, the opted-in behavior for Claude and Codex, `--agent`
  override behavior, bootstrap/discussion no-op behavior, and the fail-loud
  missing-config path.
- Update the relevant docs/context/template copies so the new frontmatter and
  local-config contract are durable, not only described in the PR.


## Context

Local CLI help was checked while drafting this ticket:

- `codex --help` exposes `--dangerously-bypass-approvals-and-sandbox` and
  `--ask-for-approval never`.
- `claude --help` exposes `--dangerously-skip-permissions`,
  `--allow-dangerously-skip-permissions`, and
  `--permission-mode bypassPermissions`.

Do not hard-code these flags blindly if the implementation finds a better
current flag combination; verify against the installed CLIs and document the
choice. The intent is "skip approval/permission stops for this trusted ticket,"
not "remove every possible safety layer for every Relay launch."

Likely implementation areas:

- `src/relay/config.py` — parse a local-only per-agent field from
  `relay.local.toml` by allowing partial `[agents.<name>]` local overrides
  for `skip_permissions_argv`.
- `src/relay/commands/launch.py` — thread the ticket's opt-in value into
  `build_agent_command`, and re-evaluate it for every chained step because
  the agent can rotate between Claude and Codex.
- `src/relay/ticket.py`, `src/relay/validate.py`, and
  `relay-os/contexts/relay/architecture/SKILL.md` for the first-class
  optional canonical `skip_permissions` field.
- `relay-os/relay.toml`, `src/relay/resources/templates/relay-os/relay.toml`,
  README/docs, `example/relay-os/relay.local.toml`, and any examples/templates
  that teach agent config.
- If architecture context changes, also update the packaged bootstrap context
  copy under
  `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/architecture/SKILL.md`.

Design preference: because this is a built-in Relay launch behavior, prefer a
first-class optional canonical field over a `[ticket.fields.*]` extension if
that avoids forcing every existing ticket to carry a new extension value.
