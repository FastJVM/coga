---
title: skip-permissions-option
status: done
mode: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts:
- relay/architecture
- relay/codebase
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
---

## Description

Add a Relay launch option that lets a trusted ticket run Claude Code or
Codex without stopping for per-command permission/approval prompts when Relay
is running autonomous work. The important constraint is scope: this should be
a local per-agent policy that applies to normal `mode: auto` task launches,
not a shared repo default and not a field every ticket must remember to set.

The dangerous CLI argv should live in local configuration so each operator
chooses what their own machine is willing to run. Add per-agent local config
under `[agents.<name>]`: `skip_permissions = "auto"` opts that agent into
using `skip_permissions_argv = "..."` for normal auto-mode task launches only.
When the policy is absent, false, or otherwise unset, `relay launch` keeps
today's behavior.

### Acceptance Criteria

- `relay.local.toml` can provide per-agent permission-skip policy with
  `skip_permissions = "auto"` and argv with `skip_permissions_argv = "..."`
  under `[agents.<name>]`, without requiring dangerous machine-local choices
  to be committed to shared `relay.toml`.
- `skip_permissions = "auto"` applies only to normal task tickets whose
  frontmatter has `mode: auto`. Existing interactive tickets and auto tickets
  whose effective agent has no skip policy keep today's behavior.
- `skip_permissions` accepts only unset/false and `"auto"`; bad values or bad
  types fail config load. `skip_permissions_argv` is a string parsed with
  `shlex.split`; bad types fail config load.
- `relay launch` applies the extra argv to both supported local agent CLIs:
  Claude Code and Codex. The behavior must work across supervised multi-step
  launches, including `code/with-review` agent rotation.
- If an agent has `skip_permissions = "auto"` but no configured
  `skip_permissions_argv`, launch fails loud before spawning the agent rather
  than silently falling back to the normal permission mode.
- The extra argv is inserted after any `name_flag`/session-name argv and
  before the mode-specific argv/prompt payload. For example:
  `claude -n <title> <skip-argv> <prompt>` and
  `codex <skip-argv> exec <prompt>`.
- `--agent` launch overrides use the effective launch agent's local
  `skip_permissions_argv` for that first step; chained steps use the current
  ticket assignee's agent config and current ticket mode.
- Bootstrap/discussion shims such as `relay chat` and `relay ticket` are not
  affected, even if the selected agent has `skip_permissions = "auto"`. This
  option applies to normal task tickets only.
- Script-mode tasks are not affected; they do not launch an agent CLI.
- Tests cover config parsing, invalid config values/types, command
  construction, default/no-op behavior, auto-mode behavior for Claude and
  Codex, interactive-mode no-op behavior, `--agent` override behavior,
  supervised chained-step behavior, bootstrap/discussion no-op behavior, and
  the fail-loud configured-without-argv path.
- Update the relevant docs/context/template copies so the auto-mode launch
  policy and local-config contract are durable, not only described in the PR.


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
  for `skip_permissions` and `skip_permissions_argv`.
- `src/relay/commands/launch.py` — thread the ticket mode and effective
  agent's local skip policy into `build_agent_command`, and re-evaluate it for
  every chained step because the agent can rotate between Claude and Codex.
- `src/relay/ticket.py` and `src/relay/validate.py` only if the existing task
  loading/validation path needs an explicit helper for normal task vs
  bootstrap/discussion shims. Do not add a `skip_permissions` ticket
  frontmatter field.
- `relay-os/relay.toml`, `src/relay/resources/templates/relay-os/relay.toml`,
  README/docs, `example/relay-os/relay.local.toml`, and any examples/templates
  that teach agent config.
- If architecture context changes, also update the packaged bootstrap context
  copy under
  `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/architecture/SKILL.md`.

Design preference: treat permission skipping as a machine-local agent policy
for autonomous launches, not task metadata. The product intent is "when this
operator has chosen autonomy for this agent, auto tasks should not block on
per-command approvals."
