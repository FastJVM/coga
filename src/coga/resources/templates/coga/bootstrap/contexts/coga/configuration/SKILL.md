---
name: coga/configuration
description: The shared `coga.toml` versus machine-local `coga.local.toml` split, each file's key allowlist, fail-loud unknown-key and migration errors, and where `env:` indirection works.
---

# Configuration

`load_config` (`src/coga/config.py`) reads two files from the Coga root:

- **`coga.toml`**, committed: repo policy every clone must agree on.
- **`coga.local.toml`**, gitignored: facts about this machine and operator.
  `COGA_LOCAL_CONFIG` can point a process at an absolute path instead, so a
  Coga process in another checkout of the same repo, such as a relay
  worktree, reads the operator's local settings (`local_config_path`).

Both are validated against fixed schemas on every command. Never commit real
credentials. Use indirection ([coga/secrets](../secrets/SKILL.md)).

## Allowlists

`coga.toml` top level: `version` (must be `1`), `default_status`, `owner`,
`agents`, `notification`, `git`, `launch`, `ticket`, `aliases`,
`extensions`, `layout`, `autofix`, `telemetry`.

`coga.local.toml` top level: `user`, `agents`, `notification`, `git`,
`upstream`, `telemetry`.

| Table | Keys | Where |
|---|---|---|
| `[agents.<name>]` | `cli`, `file` (both required), `mode`, `name_flag`, `session_id_flag`, `discussion`, `analyze`, `peer` | both; local overlays shared ([coga/agents](../agents/SKILL.md)) |
| `[notification]` | `channels`, `slack` | both |
| `[notification.slack]` | `webhook`, `important_webhook`, `enabled`, `gifs`, `users` | both; local wins ([coga/notifications](../notifications/SKILL.md)) |
| `[git]` | `enabled`, `remote`, `control_branch`, `worktrees_ticket_owned` | shared |
| `[git]` | `enabled` only | local; overrides shared ([coga/sync](../sync/SKILL.md)) |
| `[launch]` | `idle_timeout`, `max_session` | shared |
| `[ticket]` / `[ticket.fields.<name>]` | `fields` / `description`, `values`, `default`, `required` | shared ([coga/tickets](../tickets/SKILL.md)) |
| `[layout]` | `contexts` | shared only ([coga/context-layout](../context-layout/SKILL.md)) |
| `[autofix]` | `agent` | shared only |
| `[upstream]` | `checkouts` | local only |
| `[telemetry]` | `enabled` (boolean only) | both; local overrides shared, including local true over shared false |

The split is deliberate. `[layout]` and `[autofix]` are team policy: one
clone must not resolve a context ref somewhere another clone does not.
`[upstream] checkouts` is the mirror image. It names absolute paths to other
repos on this machine, so it is accepted only locally and validated for
shape alone: a list of non-empty strings, `~` expanded, required to be
absolute. A path missing on disk still loads and is skipped by its consumer,
because failing config load would brick every command when a client repo
moves. `user` is always local and never guessed
([coga/init](../init/SKILL.md)).

## Unknown keys fail loud

Any unrecognized key at any level of a fixed-schema table, in either file,
raises `ConfigError` naming the offender and listing the allowed keys
(`_reject_unknown_keys`, `_reject_unknown_sections`, plus the per-table
parsers). A misspelled `[notification.slak]` therefore stops every command
instead of silently resolving to "no webhook". Adding a config key means
adding it to its table's allowlist in the same change.

Free-form maps are exempt because their keys are data: `[aliases]`,
`[extensions]` (a repo-owned namespace Coga passes through uninterpreted),
`[notification.slack.gifs]`, and `[notification.slack.users]`.

Known-but-removed keys raise tailored migration errors **before** the
generic check, so the actionable message survives:

- `[assignees]` and `[megalaunch]` in `coga.toml`;
- `[secrets]` in `coga.local.toml` (secrets are declared inline on tickets);
- `[slack]` in either file (moved under `[notification.slack]`);
- `auto`, `skip_permissions`, `skip_permissions_argv` in any
  `[agents.<name>]`, reported against the file that contains them.

## `env:` indirection in config

Config values are otherwise literal. Exactly two fields run an `env:VAR`
reference through the shared resolver: `[notification.slack].webhook` and
`[notification.slack].important_webhook` (`_resolve_secret_value`). An unset
variable there resolves to "no webhook configured". An `env:VAR` written in
any other config field is a literal string, not an indirection, and `op://`
is not understood anywhere in config. Ticket `secrets:` are a separate,
fail-loud path.

## Other configuration surfaces

`owner` (the recurring operator), `[launch]` limits, and `[autofix]` are
owned by [coga/recurring](../recurring/SKILL.md). `[aliases]` expand to
Coga argv ([coga/cli](../cli/SKILL.md)).

`Config.telemetry_enabled` defaults true. Both `[telemetry]` layers are
validated even when overridden. No endpoint, key, cadence, or test bypass is
configurable. Delivery, state and payload belong to
[coga/telemetry](../telemetry/SKILL.md); git and notification switches remain
independent.
