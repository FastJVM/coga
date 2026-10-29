---
name: coga/configuration
description: The shared `coga.toml` versus machine-local `coga.local.toml` split, each file's key allowlist, fail-loud unknown-key and migration errors, and where `env:` indirection works.
---

# Configuration

Coga reads two files from the Coga root:

- **`coga.toml`**, committed: repo policy every clone must agree on.
- **`coga.local.toml`**, gitignored: facts about this machine and operator.
  `COGA_LOCAL_CONFIG` can point a process at an absolute path instead, so a
  Coga process in another checkout of the same repo, such as a relay
  worktree, reads the operator's local settings.

Both are validated against fixed schemas on every command that loads config.
Two invocations read neither file, so neither validates config nor sweeps
state: `coga --version`, and `--help`/`-h` under a built-in command (for
example `coga launch --help`). Top-level `coga --help`
still loads config to list the repo's `[aliases]`. Never commit real
credentials. Use indirection ([coga/secrets](../secrets/SKILL.md)).

## Choosing an agent

Init supplies definitions for Claude Code and Codex; the default Claude path
needs no config edit. To use Codex for new tasks, place this top-level setting
before any `[table]` in `coga/coga.local.toml`:

```toml
default_agent = "codex"
```

This does not change an already activated ticket or select the interviewer
for `coga chat` and `coga ticket`. Use `coga chat --agent codex` or
`coga ticket "Your task title" --agent codex` for those sessions.
The comments beside `default_agent` and `[agents.*]` in the
[shipped configuration](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/coga.toml)
own precedence and routing details. Workflow roles and peer selection are
explained in [coga/workflows](../workflows/SKILL.md); the
[first-task walk](../first-task/SKILL.md) covers the prerequisites for a PR
with either one agent or a peer reviewer.

## Allowlists

`coga.toml` top level: `version` (must be `1`), `default_status`,
`default_agent`, `owner`, `agents`, `notification`, `git`, `launch`, `ticket`, `aliases`,
`extensions`, `layout`, `autofix`, `telemetry`, `recurring`, `log`.

`coga.local.toml` top level: `user`, `default_agent`, `agents`,
`notification`, `git`, `upstream`, `telemetry`, `authoring`.

`default_agent` is a string in both files. The local value wins, and each
present value must name a type in the merged `[agents.*]`; it is validated at
load. Precedence, freezing at activation, and what it does not move are
explained beside the key in the shipped `coga.toml`.

| Table | Keys | Where |
|---|---|---|
| `[agents.<name>]` | `cli`, `file` (both required), `mode`, `name_flag`, `session_id_flag`, `launch_args`, `discussion`, `analyze`, `peer` | both; local overlays shared key by key (explained in the shipped `coga.toml`) |
| `[notification]` | `channels`, `slack` | both |
| `[notification.slack]` | `webhook`, `important_webhook`, `enabled`, `gifs`, `users` | both; local wins ([coga/notifications](../notifications/SKILL.md)) |
| `[git]` | `enabled`, `remote`, `control_branch`, `worktrees_ticket_owned` | shared |
| `[git]` | `enabled` only | local; overrides shared ([coga/state-publication](../state-publication/SKILL.md)) |
| `[log]` | `retention_days` (non-negative integer, default `30`; `0` disables trimming) | shared only |
| `[recurring]` | `idle_days` (non-negative integer, default `14`; `0` disables inactivity gating) | shared only |
| `[launch]` | `idle_timeout`, `max_session` | shared |
| `[ticket]` / `[ticket.fields.<name>]` | `fields` / `description`, `values`, `default`, `required` | shared ([coga/tickets](../tickets/SKILL.md)) |
| `[layout]` | `contexts` | shared only ([coga/context-layout](../context-layout/SKILL.md)) |
| `[autofix]` | `agent`, `contexts` | shared only ([coga/recurring/autofix](../recurring/autofix/SKILL.md)) |
| `[upstream]` | `checkouts` | local only |
| `[authoring]` | `agent` | local only ([coga/tickets/authoring](../tickets/authoring/SKILL.md)) |
| `[telemetry]` | `enabled` (boolean only) | both; local overrides shared, including local true over shared false |

The split is deliberate. `[layout]` and `[autofix]` are team policy: one
clone must not resolve a context ref somewhere another clone does not.
`[upstream] checkouts` is the mirror image. It names absolute paths to other
repos on this machine, so it is accepted only locally and validated for
shape alone: a list of non-empty strings, `~` expanded, required to be
absolute. A path missing on disk still loads and is skipped by its consumer,
because failing config load would brick every command when a client repo
moves. `[authoring] agent` is local for the same reason: which agent an
operator authors tickets with (say, while one agent's quota is exhausted) is
a fact about that operator. Load checks only its shape; the name is checked
against `[agents]` when authoring resolves it, and `COGA_AUTHORING_AGENT`
overrides it. `user` is always local and never guessed
([coga/init](../init/SKILL.md)).

## Unknown keys fail loud

Any unrecognized key at any level of a fixed-schema table, in either file,
raises `ConfigError` naming the offender and listing the allowed keys. A
misspelled `[notification.slak]` therefore stops every config-loading command
instead of silently resolving to "no webhook".

Free-form maps are exempt because their keys are data: `[aliases]`,
`[extensions]` (a repo-owned namespace Coga passes through uninterpreted),
`[notification.slack.gifs]`, and `[notification.slack.users]`.

Known-but-removed or misplaced keys raise tailored errors **before** the
generic check, so the actionable message survives:

- `[assignees]` and `[megalaunch]` in `coga.toml`;
- `[secrets]` in `coga.local.toml` (secrets are declared inline on tickets);
- `[authoring]` in `coga.toml` (machine-local; the install-level default is
  `bootstrap/ticket`'s `agent:`);
- `[slack]` in either file (moved under `[notification.slack]`);
- `auto`, `skip_permissions`, `skip_permissions_argv` in any
  `[agents.<name>]`, reported against the file that contains them.

## `env:` indirection in config

Config values are otherwise literal. Exactly two fields run an `env:VAR`
reference through the shared resolver: `[notification.slack].webhook` and
`[notification.slack].important_webhook`. An unset
variable there resolves to "no webhook configured". An `env:VAR` written in
any other config field is a literal string, not an indirection, and `op://`
is not understood anywhere in config. Ticket `secrets:` are a separate,
fail-loud path.

## Other configuration surfaces

`owner` (the recurring operator), `[launch]` limits, and `[autofix]` are
owned by [coga/recurring](../recurring/SKILL.md). `[aliases]` expand to
Coga argv ([coga/cli](../cli/SKILL.md)).

Telemetry defaults on. Both `[telemetry]` layers are
validated even when overridden. No endpoint, key, cadence, or test bypass is
configurable. Delivery, state and payload belong to
[phone-home ticket](https://github.com/FastJVM/coga/blob/main/coga/recurring/phone-home/ticket.md); git and notification switches remain
independent.

`[recurring].idle_days` is team policy and cannot be overridden locally.
Booleans, negative values and non-integers raise `ConfigError`. The activity
signal, calendar boundary and sweep overrides are owned by
[recurring scheduling](../recurring/scheduling/inactivity/SKILL.md).

`[log].retention_days` cannot be overridden locally. Booleans, negative values,
non-integers, non-table values and unknown keys fail config loading. Very large
positive integers saturate at `datetime.min` when computing the cutoff. Days
are local calendar days, matching timezone-free log envelopes: complete
unprotected events strictly before local midnight on today minus the window
expire. The boundary and future timestamps stay. The
[trim-log ticket](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/recurring/trim-log/ticket.md)
owns exceptions and its weekly schedule; its
[operations guide](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/recurring/trim-log/operations.md)
owns default-on adoption for existing repos.
