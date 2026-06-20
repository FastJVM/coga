"""Load and merge relay.toml + relay.local.toml."""

from __future__ import annotations

import math
import os
import random
import shlex
import subprocess
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(Exception):
    """Raised for any invalid/missing config."""


class SecretError(Exception):
    """A ticket's declared secret cannot be satisfied at launch time.

    Raised by `select_launch_secrets` when a ticket declares a `secrets:` key
    that is not in `[secrets]`, whose `env:VAR` indirection points at an unset
    env var, or whose `op://` reference cannot be resolved (the `op` CLI is
    missing or `op read` returns non-zero). `relay launch` turns this into a
    non-zero exit before any agent or script is spawned — the fail-loud
    guarantee. Messages name the Relay secret key and reference, never the
    resolved secret value.
    """


@dataclass(frozen=True)
class SecretValue:
    """A resolved `[secrets]` entry that remembers where it came from.

    `cfg.secrets` keeps these instead of bare strings so launch-time
    enforcement and `relay validate` can tell an `env:VAR` reference whose var
    is unset (`value is None`) apart from an empty literal (`value == ""`), and
    can name the missing env var in errors. `raw` is the original `[secrets]`
    value; `env_var` is the referenced variable name (None for a literal);
    `op_ref` is the `op://vault/item/field` 1Password reference (None unless
    op-indirected); `value` is the resolved string, or None iff env-indirected
    and unset, **or** op-indirected (op values are resolved on demand at launch
    / `relay secret get` time, never at config load — see `_resolve_secrets`).
    """

    raw: str
    env_var: str | None
    value: str | None
    op_ref: str | None = None

    @property
    def missing(self) -> bool:
        """True when this is an `env:VAR` reference whose var is unset.

        An `op://` reference is **not** missing here — its `value` is None only
        because resolution is deferred, not because anything is wrong. The
        env-unset and op-deferred cases are kept distinct so legacy blanket
        injection skips op references without trying to read them.
        """
        return self.env_var is not None and self.value is None


@dataclass(frozen=True)
class AgentType:
    name: str
    cli: str
    auto: str
    file: str
    mode: str               # "local" | future: "remote" | "cloud"
    # Flag (or flag template) the CLI accepts to set the session display name
    # at launch — e.g. `-n` for claude (shown in /resume, prompt box, terminal
    # title). Empty when the CLI has no such flag. Split with shlex; the
    # ticket title is appended as the next argv element. Skipped in
    # `discussion` mode so the human's first ask can name the session.
    name_flag: str = ""
    # Optional argv override for discussion prompts (`relay chat`, `relay ticket`):
    # the composed prompt rides as system/developer context instead of becoming
    # the agent's first user message. Parsed via `shlex.split`; the literal
    # token `{prompt}` is replaced with the composed prompt. Empty string lets
    # launch use its built-in defaults for known CLIs, then positional fallback.
    discussion: str = ""
    # Machine-local permission-skip policy — settable ONLY from a partial
    # `[agents.<name>]` table in `relay.local.toml` (shared `relay.toml`
    # carrying either key fails config load, so a dangerous default can never
    # be committed). `skip_permissions = "auto"` opts this agent into
    # appending `skip_permissions_argv` for normal `mode: auto` task launches;
    # unset / `false` keeps today's behavior. The argv is authored as one
    # string and parsed with `shlex.split` (e.g.
    # `"--dangerously-skip-permissions"` for claude,
    # `"--dangerously-bypass-approvals-and-sandbox"` for codex).
    skip_permissions: str = ""           # "" (off) | "auto"
    skip_permissions_argv: tuple[str, ...] = ()


@dataclass(frozen=True)
class TicketField:
    """A repo-declared extension to the canonical ticket frontmatter schema.

    Declared in `relay.toml` under `[ticket.fields.<name>]`. The field is
    written into every freshly created ticket below the
    `# --- extensions ---` marker, and `relay validate` / `relay mark active`
    enforce the declared constraints.
    """

    name: str
    description: str
    values: tuple[str, ...] | None = None  # enum constraint, None = free string
    default: str = ""
    required: bool = False


@dataclass(frozen=True)
class Config:
    repo_root: Path
    current_user: str
    default_status: str
    agents: dict[str, AgentType]
    # Slack remains as the first notification backend. These compatibility
    # fields hold the effective Slack-channel config resolved from
    # `[notification.slack]`, legacy `[slack]`, or deprecated env fallback.
    slack_webhook: str | None
    slack_enabled: bool
    secrets: dict[str, SecretValue]
    notification_channels: tuple[str, ...] = ("slack",)
    notification_deprecation_notes: tuple[str, ...] = ()
    slack_gifs: dict[str, list[str]] = field(default_factory=dict)
    slack_users: dict[str, str] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)
    ticket_fields: dict[str, TicketField] = field(default_factory=dict)
    # Git sync — the git analogue of Slack. `git_enabled` follows the same
    # local-overrides-shared resolution as `slack_enabled`; `git_remote` /
    # `git_control_branch` come from shared `[git]`. See `relay.git`.
    git_enabled: bool = True
    git_remote: str = "origin"
    git_control_branch: str = "main"
    # Liveness limits for the interactive REPLs `relay recurring` spawns, from
    # the shared `[launch]` table. None = no limit from config. The idle timeout
    # also keeps a presence flag because that limit has a built-in default:
    # `[launch].idle_timeout = 0` must explicitly disarm it rather than collapse
    # to "omitted" and re-enable the default. The env overrides
    # (`RELAY_REPL_IDLE_TIMEOUT` / `RELAY_REPL_MAX_SESSION`) still win over these;
    # see `relay.commands.recurring`. Attended `relay launch` does not read them
    # — only the unattended sweep arms a limit, so a human's session is never
    # killed by a committed default.
    launch_idle_timeout: float | None = None
    launch_idle_timeout_present: bool = False
    launch_max_session: float | None = None

    # --- convenience accessors -------------------------------------------------

    @property
    def project_name(self) -> str:
        """Display name of the host repo. Parent of `relay-os/` when nested."""
        if self.repo_root.name == "relay-os":
            return self.repo_root.parent.name
        return self.repo_root.name

    def agent_type(self, name: str) -> AgentType:
        """Resolve an agent type name to its AgentType config.

        The ticket `agent:` and `assignee:` fields name an agent type
        directly (e.g. `claude`, `codex`) — no per-user nickname layer.
        """
        if name not in self.agents:
            raise ConfigError(
                f"Agent type {name!r} is not defined in [agents]. "
                f"Known: {sorted(self.agents)}."
            )
        return self.agents[name]

    def default_agent(self) -> AgentType | None:
        """First-declared agent type, used as the create-time default.

        TOML preserves declaration order, so the team puts their default
        first in `relay.toml`.
        """
        if not self.agents:
            return None
        first = next(iter(self.agents))
        return self.agents[first]

    def gif_for(self, kind: str) -> str | None:
        """Pick a random GIF URL for `kind` (e.g. "done", "panic"), or None.

        Configured under `[notification.slack.gifs]` in relay.toml as
        `kind = ["url", ...]`. Empty/missing → None, and the caller posts
        text-only.
        """
        urls = self.slack_gifs.get(kind, [])
        return random.choice(urls) if urls else None


# --- discovery -----------------------------------------------------------------


def find_repo_root(start: Path | None = None) -> Path:
    """Walk up from `start` (default cwd) until a `relay.toml` is found.

    Also descends into a sibling `relay-os/` subdir at each level — so
    `relay` works from a company repo's root, not just from inside
    `relay-os/`.
    """
    cur = (start or Path.cwd()).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / "relay.toml").is_file():
            return candidate
        nested = candidate / "relay-os"
        if (nested / "relay.toml").is_file():
            return nested
    raise ConfigError(
        f"No relay.toml found in {cur} or any parent directory. "
        "Run `relay` from inside a Relay repo."
    )


# --- loader --------------------------------------------------------------------


def load_config(repo_root: Path | None = None) -> Config:
    root = repo_root or find_repo_root()
    shared = _read_toml(root / "relay.toml")
    local_path = root / "relay.local.toml"
    local = _read_toml(local_path) if local_path.is_file() else {}

    version = shared.get("version")
    if version != 1:
        raise ConfigError(f"Unsupported relay.toml version: {version!r} (expected 1)")

    # `assignees` carries a dedicated migration message, so its raise must beat
    # the generic top-level unknown-key check below (which omits it).
    if "assignees" in shared:
        raise ConfigError(
            "[assignees] is no longer supported in relay.toml. Remove the "
            "[assignees.*] tables — ticket `assignee:` now names an agent "
            "type (e.g. `claude`) or a human directly. See docs/spec.md."
        )
    _reject_unknown_sections(shared, local)

    default_status = shared.get("default_status", "draft")
    agents = _parse_agents(shared.get("agents", {}), local.get("agents", {}))
    notification_channels = _resolve_notification_channels(
        shared.get("notification"),
        local.get("notification"),
        shared.get("slack"),
        local.get("slack"),
    )
    (
        slack_webhook,
        slack_enabled,
        slack_gifs,
        slack_users,
        notification_deprecation_notes,
    ) = _parse_slack_notification(
        shared.get("notification"),
        local.get("notification"),
        shared.get("slack"),
        local.get("slack"),
    )
    aliases = _parse_aliases(shared.get("aliases", {}))
    ticket_fields = _parse_ticket_fields(shared.get("ticket"))
    git_enabled = _resolve_git_enabled(shared.get("git"), local.get("git"))
    git_remote, git_control_branch = _parse_git(shared.get("git"))
    launch_idle_timeout, launch_idle_timeout_present, launch_max_session = (
        _parse_launch(shared.get("launch"))
    )

    current_user = local.get("user")
    if not current_user:
        raise ConfigError(
            f"`user` is missing from {local_path}. "
            "Set it to your name, e.g. `user = \"marc\"`."
        )

    secrets = _resolve_secrets(local.get("secrets", {}))

    return Config(
        repo_root=root,
        current_user=current_user,
        default_status=default_status,
        agents=agents,
        slack_webhook=slack_webhook,
        slack_enabled=slack_enabled,
        notification_channels=notification_channels,
        notification_deprecation_notes=notification_deprecation_notes,
        slack_gifs=slack_gifs,
        slack_users=slack_users,
        secrets=secrets,
        aliases=aliases,
        ticket_fields=ticket_fields,
        git_enabled=git_enabled,
        git_remote=git_remote,
        git_control_branch=git_control_branch,
        launch_idle_timeout=launch_idle_timeout,
        launch_idle_timeout_present=launch_idle_timeout_present,
        launch_max_session=launch_max_session,
    )


# --- parsing helpers -----------------------------------------------------------


def _read_toml(path: Path) -> dict:
    if not path.is_file():
        raise ConfigError(f"Missing config file: {path}")
    with path.open("rb") as f:
        return tomllib.load(f)


def _reject_unknown_keys(table: object, allowed: frozenset[str], label: str) -> None:
    """Fail loud on any key in `table` outside `allowed`.

    The fail-loud guard for every fixed-schema config table: a misspelled or
    stray key (a top-level `[notifcation]` section, a `[notification.slak]`
    sub-table, an `[agents.claude].clii` typo) raises `ConfigError` naming the
    offender and listing the valid keys, instead of `.get(...)` silently
    treating the real section as absent (the Slack-goes-dark footgun).

    A no-op on non-dicts, so the dedicated "must be a table" type errors keep
    firing from their own call sites. Free-form maps — `[aliases]`, `[secrets]`,
    `[notification.slack.gifs]`, `[notification.slack.users]` — do **not** call
    this: their keys are user-chosen data, not schema.
    """
    if not isinstance(table, dict):
        return
    unknown = sorted(set(table) - allowed)
    if unknown:
        raise ConfigError(
            f"{label} has unknown key(s) {unknown}. "
            f"Allowed: {sorted(allowed)}."
        )


# Fixed-schema tables — every key not listed is rejected at load time. Free-form
# maps (aliases, secrets, slack gifs/users) are deliberately absent; their keys
# are data. Top-level keys that carry a dedicated migration error (`assignees`
# in shared; `skip_permissions*` in a shared `[agents.<name>]`) are omitted here
# so their tailored raise fires before the generic check.
_ALLOWED_SHARED_SECTIONS: frozenset[str] = frozenset({
    "version",
    "default_status",
    "agents",
    "notification",
    "slack",
    "git",
    "launch",
    "ticket",
    "aliases",
})
_ALLOWED_LOCAL_SECTIONS: frozenset[str] = frozenset({
    "user",
    "secrets",
    "agents",
    "notification",
    "slack",
    "git",
})
_ALLOWED_AGENT_KEYS: frozenset[str] = frozenset({
    "cli",
    "auto",
    "file",
    "mode",
    "name_flag",
    "discussion",
})
_ALLOWED_NOTIFICATION_KEYS: frozenset[str] = frozenset({"channels", "slack"})
_ALLOWED_SLACK_KEYS: frozenset[str] = frozenset({
    "webhook",
    "enabled",
    "gifs",
    "users",
})
_ALLOWED_SHARED_GIT_KEYS: frozenset[str] = frozenset({
    "enabled",
    "remote",
    "control_branch",
})
# Only `enabled` is machine-local. `remote` and `control_branch` are shared
# repo policy and `_parse_git` intentionally reads them only from relay.toml.
_ALLOWED_LOCAL_GIT_KEYS: frozenset[str] = frozenset({"enabled"})
_ALLOWED_LAUNCH_KEYS: frozenset[str] = frozenset({"idle_timeout", "max_session"})
_ALLOWED_TICKET_KEYS: frozenset[str] = frozenset({"fields"})


def _reject_unknown_sections(shared: dict, local: dict) -> None:
    """Reject unknown keys in the top-level and cross-file fixed-schema tables.

    Covers what isn't validated inside a single dedicated parser: the top-level
    sections of both files, plus the `[notification]` / `[notification.slack]` /
    legacy `[slack]` / `[git]` tables, each of which may appear in *both*
    `relay.toml` and `relay.local.toml`. The per-table parsers
    (`_parse_agents`, `_parse_launch`, `_parse_ticket_fields`) reject their own
    nested keys, so they aren't repeated here.

    `_notification_slack_table` is reused to reach the nested `slack` sub-table;
    it raises the existing "must be a table" error for a non-dict, so the type
    contract is unchanged.
    """
    _reject_unknown_keys(shared, _ALLOWED_SHARED_SECTIONS, "relay.toml")
    _reject_unknown_keys(local, _ALLOWED_LOCAL_SECTIONS, "relay.local.toml")
    for source, table in (("relay.toml", shared), ("relay.local.toml", local)):
        notification = table.get("notification")
        _reject_unknown_keys(
            notification, _ALLOWED_NOTIFICATION_KEYS, f"[notification] in {source}"
        )
        _reject_unknown_keys(
            _notification_slack_table(notification, f"[notification] in {source}"),
            _ALLOWED_SLACK_KEYS,
            f"[notification.slack] in {source}",
        )
        _reject_unknown_keys(table.get("slack"), _ALLOWED_SLACK_KEYS, f"[slack] in {source}")
    _reject_unknown_keys(
        shared.get("git"), _ALLOWED_SHARED_GIT_KEYS, "[git] in relay.toml"
    )
    _reject_unknown_keys(
        local.get("git"), _ALLOWED_LOCAL_GIT_KEYS, "[git] in relay.local.toml"
    )


_LOCAL_AGENT_OVERRIDE_KEYS: frozenset[str] = frozenset({
    # The only `[agents.<name>]` keys honored from `relay.local.toml`.
    # Anything else in a local agent table fails loud rather than silently
    # diverging from the shared agent definition.
    "skip_permissions",
    "skip_permissions_argv",
})


def _parse_agents(raw: dict, local_raw: dict | None = None) -> dict[str, AgentType]:
    out: dict[str, AgentType] = {}
    for name, data in raw.items():
        for required in ("cli", "auto", "file"):
            if required not in data:
                raise ConfigError(f"agents.{name}.{required} is required")
        for local_only in sorted(_LOCAL_AGENT_OVERRIDE_KEYS):
            if local_only in data:
                raise ConfigError(
                    f"agents.{name}.{local_only} is machine-local policy and "
                    "must not be committed to shared relay.toml. Move it to a "
                    f"partial [agents.{name}] table in relay.local.toml."
                )
        # Generic unknown-key reject runs after the dedicated skip-policy raise
        # above so that machine-local-policy message is preserved.
        _reject_unknown_keys(data, _ALLOWED_AGENT_KEYS, f"[agents.{name}]")
        discussion = data.get("discussion", "")
        if not isinstance(discussion, str):
            raise ConfigError(
                f"agents.{name}.discussion must be a string "
                f"(got {type(discussion).__name__})"
            )
        local_data = (local_raw or {}).get(name, {})
        skip_permissions, skip_permissions_argv = _parse_local_skip_policy(
            name, local_data
        )
        out[name] = AgentType(
            name=name,
            cli=data["cli"],
            auto=data["auto"],
            file=data["file"],
            mode=data.get("mode", "local"),
            name_flag=data.get("name_flag", ""),
            discussion=discussion,
            skip_permissions=skip_permissions,
            skip_permissions_argv=skip_permissions_argv,
        )
    unknown_local = sorted(set(local_raw or {}) - set(raw))
    if unknown_local:
        raise ConfigError(
            f"relay.local.toml overrides unknown agent(s) {unknown_local}. "
            f"Known agents (from relay.toml): {sorted(raw)}."
        )
    return out


def _parse_local_skip_policy(
    name: str, local_data: object
) -> tuple[str, tuple[str, ...]]:
    """Parse a partial local `[agents.<name>]` table's permission-skip policy.

    `skip_permissions` accepts only unset / `false` (off) or the string
    `"auto"`; anything else fails config load. `skip_permissions_argv` must be
    a string and is parsed with `shlex.split`. The "auto without argv" case is
    deliberately legal here — `relay launch` fails loud when the policy would
    actually apply, so a half-written local table doesn't brick every other
    relay command on the machine.
    """
    if not isinstance(local_data, dict):
        raise ConfigError(
            f"[agents.{name}] in relay.local.toml must be a table "
            f"(got {type(local_data).__name__})"
        )
    bad_keys = sorted(set(local_data) - _LOCAL_AGENT_OVERRIDE_KEYS)
    if bad_keys:
        raise ConfigError(
            f"[agents.{name}] in relay.local.toml has unsupported keys "
            f"{bad_keys}. Only {sorted(_LOCAL_AGENT_OVERRIDE_KEYS)} may be "
            "overridden locally; everything else belongs in shared relay.toml."
        )

    skip_permissions = ""
    if "skip_permissions" in local_data:
        value = local_data["skip_permissions"]
        if value is False:
            skip_permissions = ""
        elif value == "auto":
            skip_permissions = "auto"
        else:
            raise ConfigError(
                f"[agents.{name}].skip_permissions in relay.local.toml must "
                f"be false or \"auto\" (got {value!r})"
            )

    skip_permissions_argv: tuple[str, ...] = ()
    if "skip_permissions_argv" in local_data:
        value = local_data["skip_permissions_argv"]
        if not isinstance(value, str):
            raise ConfigError(
                f"[agents.{name}].skip_permissions_argv in relay.local.toml "
                f"must be a string (got {type(value).__name__})"
            )
        skip_permissions_argv = tuple(shlex.split(value))

    return skip_permissions, skip_permissions_argv


_RESERVED_TICKET_FIELD_NAMES: frozenset[str] = frozenset({
    # Canonical ticket frontmatter keys — see `relay/architecture` and
    # `relay.validate.REQUIRED_TASK_KEYS` / `OPTIONAL_TASK_KEYS`. Extensions
    # may not collide with any of these.
    "title",
    "status",
    "mode",
    "owner",
    "human",
    "agent",
    "assignee",
    "watchers",
    "workflow",
    "step",
    "contexts",
    "skills",
    "secrets",
})

_ALLOWED_TICKET_FIELD_KEYS: frozenset[str] = frozenset({
    "description",
    "values",
    "default",
    "required",
})


def _parse_ticket_fields(raw: dict | None) -> dict[str, TicketField]:
    """Parse `[ticket.fields.<name>]` tables into `TicketField` records.

    Order in TOML is preserved (insertion order on dict), so create writes
    extension fields in declaration order.
    """
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError(
            f"[ticket] must be a table (got {type(raw).__name__})"
        )
    _reject_unknown_keys(raw, _ALLOWED_TICKET_KEYS, "[ticket]")
    fields_raw = raw.get("fields")
    if fields_raw is None:
        return {}
    if not isinstance(fields_raw, dict):
        raise ConfigError(
            f"[ticket.fields] must be a table (got {type(fields_raw).__name__})"
        )

    out: dict[str, TicketField] = {}
    for name, data in fields_raw.items():
        if not isinstance(data, dict):
            raise ConfigError(
                f"[ticket.fields.{name}] must be a table "
                f"(got {type(data).__name__})"
            )
        if name in _RESERVED_TICKET_FIELD_NAMES:
            raise ConfigError(
                f"[ticket.fields.{name}] collides with the canonical ticket "
                f"frontmatter key {name!r}. Pick a different name. "
                "See `relay-os/contexts/relay/architecture/SKILL.md` for the "
                "reserved set."
            )
        bad_keys = sorted(set(data) - _ALLOWED_TICKET_FIELD_KEYS)
        if bad_keys:
            raise ConfigError(
                f"[ticket.fields.{name}] has unsupported keys {bad_keys}. "
                f"Allowed: {sorted(_ALLOWED_TICKET_FIELD_KEYS)}."
            )

        description = data.get("description")
        if not isinstance(description, str) or not description.strip():
            raise ConfigError(
                f"[ticket.fields.{name}].description must be a non-empty string"
            )

        values: tuple[str, ...] | None = None
        if "values" in data:
            v = data["values"]
            if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                raise ConfigError(
                    f"[ticket.fields.{name}].values must be a list of strings"
                )
            if not v:
                raise ConfigError(
                    f"[ticket.fields.{name}].values must not be empty"
                )
            values = tuple(v)

        default = data.get("default", "")
        if not isinstance(default, str):
            raise ConfigError(
                f"[ticket.fields.{name}].default must be a string "
                f"(got {type(default).__name__})"
            )
        if values is not None and default and default not in values:
            raise ConfigError(
                f"[ticket.fields.{name}].default {default!r} is not in "
                f"declared values {list(values)}"
            )

        required = data.get("required", False)
        if not isinstance(required, bool):
            raise ConfigError(
                f"[ticket.fields.{name}].required must be a boolean "
                f"(got {type(required).__name__})"
            )

        out[name] = TicketField(
            name=name,
            description=description.strip(),
            values=values,
            default=default,
            required=required,
        )
    return out


def _parse_aliases(raw: dict) -> dict[str, str]:
    """Parse [aliases] table — each entry is name → expanded relay command."""
    if not isinstance(raw, dict):
        raise ConfigError(f"[aliases] must be a table (got {type(raw).__name__})")
    out: dict[str, str] = {}
    for name, value in raw.items():
        if not isinstance(value, str):
            raise ConfigError(
                f"aliases.{name} must be a string (got {type(value).__name__})"
            )
        if not value.strip():
            raise ConfigError(f"aliases.{name} is empty")
        out[name] = value.strip()
    return out


_SUPPORTED_NOTIFICATION_CHANNELS: frozenset[str] = frozenset({"slack"})


def _resolve_notification_channels(
    shared: dict | None,
    local: dict | None,
    shared_legacy_slack: dict | None,
    local_legacy_slack: dict | None,
) -> tuple[str, ...]:
    """Resolve `[notification].channels` with local overriding shared.

    An explicit `channels` list — including an empty one — is authoritative. A
    fresh repo that names no `channels` key anywhere gets no notification
    channels: Slack is opt-in, not the first-run default. Slack is *inferred*
    only when the absent key is paired with opt-in or compatibility evidence —
    a `[notification.slack]` table, a legacy `[slack]` table, or a bare
    `SLACK_WEBHOOK_URL` env var (see `_slack_opt_in_present`).
    """
    for label, table in (
        ("[notification] in relay.local.toml", local),
        ("[notification] in relay.toml", shared),
    ):
        if table is None:
            continue
        if not isinstance(table, dict):
            raise ConfigError(f"{label} must be a table (got {type(table).__name__})")
        if "channels" not in table:
            continue
        channels = table["channels"]
        if not isinstance(channels, list) or not all(
            isinstance(ch, str) for ch in channels
        ):
            raise ConfigError("[notification].channels must be a list of strings")
        cleaned: list[str] = []
        for channel in channels:
            name = channel.strip()
            if name and name not in cleaned:
                cleaned.append(name)
        unsupported = sorted(set(cleaned) - _SUPPORTED_NOTIFICATION_CHANNELS)
        if unsupported:
            allowed = ", ".join(sorted(_SUPPORTED_NOTIFICATION_CHANNELS))
            raise ConfigError(
                "[notification].channels contains unsupported channel(s) "
                f"{unsupported}; supported: {allowed}"
            )
        return tuple(cleaned)
    if _slack_opt_in_present(shared, local, shared_legacy_slack, local_legacy_slack):
        return ("slack",)
    return ()


def _slack_opt_in_present(
    shared_notification: dict | None,
    local_notification: dict | None,
    shared_legacy_slack: dict | None,
    local_legacy_slack: dict | None,
) -> bool:
    """True when a repo has opted into Slack via new, legacy, or env config.

    Drives channel inference when `[notification].channels` is absent: a
    `[notification.slack]` table (shared or local), a legacy `[slack]` table,
    or a bare exported `SLACK_WEBHOOK_URL` each count as opt-in evidence. With
    none of these a fresh repo selects no channels.
    """
    if (
        _notification_slack_table(shared_notification, "[notification] in relay.toml")
        is not None
    ):
        return True
    if (
        _notification_slack_table(
            local_notification, "[notification] in relay.local.toml"
        )
        is not None
    ):
        return True
    if isinstance(shared_legacy_slack, dict) or isinstance(local_legacy_slack, dict):
        return True
    if os.environ.get("SLACK_WEBHOOK_URL"):
        return True
    return False


def _notification_slack_table(raw: dict | None, label: str) -> dict | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ConfigError(f"{label} must be a table (got {type(raw).__name__})")
    table = raw.get("slack")
    if table is None:
        return None
    if not isinstance(table, dict):
        raise ConfigError(
            f"{label}.slack must be a table (got {type(table).__name__})"
        )
    return table


def _parse_slack_notification(
    shared_notification: dict | None,
    local_notification: dict | None,
    shared_legacy_slack: dict | None,
    local_legacy_slack: dict | None,
) -> tuple[str | None, bool, dict[str, list[str]], dict[str, str], tuple[str, ...]]:
    """Parse the effective Slack channel config.

    New config lives under `[notification.slack]`. Legacy `[slack]` and a bare
    `SLACK_WEBHOOK_URL` environment variable remain compatibility fallbacks and
    are reported through `notification_deprecation_notes`.
    """
    shared_slack = _notification_slack_table(
        shared_notification, "[notification] in relay.toml"
    )
    local_slack = _notification_slack_table(
        local_notification, "[notification] in relay.local.toml"
    )
    notes: list[str] = []

    webhook = _resolve_notification_slack_webhook(
        shared_slack,
        local_slack,
        shared_legacy_slack,
        local_legacy_slack,
        notes,
    )
    enabled = _resolve_notification_slack_enabled(
        shared_slack,
        local_slack,
        shared_legacy_slack,
        local_legacy_slack,
        notes,
    )
    gifs = _parse_notification_slack_gifs(
        shared_slack,
        local_slack,
        shared_legacy_slack,
        local_legacy_slack,
        notes,
    )
    users = _parse_notification_slack_users(
        shared_slack,
        local_slack,
        shared_legacy_slack,
        local_legacy_slack,
        notes,
    )
    return webhook, enabled, gifs, users, tuple(dict.fromkeys(notes))


def _legacy_note(notes: list[str], key: str) -> None:
    notes.append(
        f"`[slack].{key}` is deprecated; move it to `[notification.slack].{key}`."
    )


def _resolve_notification_slack_webhook(
    shared: dict | None,
    local: dict | None,
    shared_legacy: dict | None,
    local_legacy: dict | None,
    notes: list[str],
) -> str | None:
    """Resolve Slack webhook with local overriding shared."""
    for table in (local, shared):
        if isinstance(table, dict) and "webhook" in table:
            value = table["webhook"]
            if not isinstance(value, str):
                raise ConfigError(
                    "[notification.slack].webhook must be a string "
                    f"(got {type(value).__name__})"
                )
            return _resolve_secret_value(value) or None
    for table in (local_legacy, shared_legacy):
        if isinstance(table, dict) and "webhook" in table:
            _legacy_note(notes, "webhook")
            value = table["webhook"]
            if not isinstance(value, str):
                raise ConfigError(
                    f"[slack].webhook must be a string (got {type(value).__name__})"
                )
            return _resolve_secret_value(value) or None
    value = os.environ.get("SLACK_WEBHOOK_URL")
    if value:
        notes.append(
            "bare `SLACK_WEBHOOK_URL` fallback is deprecated; set "
            '`[notification.slack].webhook = "env:SLACK_WEBHOOK_URL"`.'
        )
        return value
    return None


def _resolve_notification_slack_enabled(
    shared: dict | None,
    local: dict | None,
    shared_legacy: dict | None,
    local_legacy: dict | None,
    notes: list[str],
) -> bool:
    """Resolve Slack channel enabled flag. Default: True."""
    for table in (local, shared):
        if isinstance(table, dict) and "enabled" in table:
            value = table["enabled"]
            if not isinstance(value, bool):
                raise ConfigError(
                    "[notification.slack].enabled must be a boolean "
                    f"(got {type(value).__name__})"
                )
            return value
    for table in (local_legacy, shared_legacy):
        if isinstance(table, dict) and "enabled" in table:
            _legacy_note(notes, "enabled")
            value = table["enabled"]
            if not isinstance(value, bool):
                raise ConfigError(
                    f"[slack].enabled must be a boolean (got {type(value).__name__})"
                )
            return value
    return True


def _parse_notification_slack_gifs(
    shared: dict | None,
    local: dict | None,
    shared_legacy: dict | None,
    local_legacy: dict | None,
    notes: list[str],
) -> dict[str, list[str]]:
    for table, prefix, legacy_key in (
        (local, "[notification.slack.gifs]", None),
        (shared, "[notification.slack.gifs]", None),
        (local_legacy, "[slack.gifs]", "gifs"),
        (shared_legacy, "[slack.gifs]", "gifs"),
    ):
        if isinstance(table, dict) and "gifs" in table:
            if legacy_key:
                _legacy_note(notes, legacy_key)
            return _parse_slack_gifs(table, prefix)
    return {}


def _parse_notification_slack_users(
    shared: dict | None,
    local: dict | None,
    shared_legacy: dict | None,
    local_legacy: dict | None,
    notes: list[str],
) -> dict[str, str]:
    for table, prefix, legacy_key in (
        (local, "[notification.slack.users]", None),
        (shared, "[notification.slack.users]", None),
        (local_legacy, "[slack.users]", "users"),
        (shared_legacy, "[slack.users]", "users"),
    ):
        if isinstance(table, dict) and "users" in table:
            if legacy_key:
                _legacy_note(notes, legacy_key)
            return _parse_slack_users(table, prefix)
    return {}


def _parse_slack_gifs(
    shared: dict | None, table_name: str = "[slack.gifs]"
) -> dict[str, list[str]]:
    """Parse Slack GIF table — each key maps an event-kind to a list of URLs.

    A random URL is picked per post. Missing/empty → text-only Slack messages.
    """
    if not isinstance(shared, dict):
        return {}
    gifs = shared.get("gifs")
    if gifs is None:
        return {}
    if not isinstance(gifs, dict):
        raise ConfigError(
            f"{table_name} must be a table (got {type(gifs).__name__})"
        )
    out: dict[str, list[str]] = {}
    for kind, urls in gifs.items():
        if not isinstance(urls, list) or not all(isinstance(u, str) for u in urls):
            raise ConfigError(
                f"{table_name}.{kind} must be a list of URL strings"
            )
        cleaned = [u.strip() for u in urls if u.strip()]
        if cleaned:
            out[kind] = cleaned
    return out


def _parse_slack_users(
    shared: dict | None, table_name: str = "[slack.users]"
) -> dict[str, str]:
    """Parse Slack user mapping — maps a relay name (the token used in a
    ticket's `owner` / `watchers` fields) to a Slack member ID.

    The member ID is what lets an incoming webhook actually *ping* someone:
    Slack only fires a notification for the `<@U…>` mention form, and a
    webhook can't look an ID up itself. Missing/empty → no mapping, and
    messages name people in plain text without notifying them.
    """
    if not isinstance(shared, dict):
        return {}
    users = shared.get("users")
    if users is None:
        return {}
    if not isinstance(users, dict):
        raise ConfigError(
            f"{table_name} must be a table (got {type(users).__name__})"
        )
    out: dict[str, str] = {}
    for name, user_id in users.items():
        if not isinstance(user_id, str) or not user_id.strip():
            raise ConfigError(
                f"{table_name}.{name} must be a non-empty Slack member ID string"
            )
        out[name] = user_id.strip()
    return out


def _resolve_git_enabled(shared: dict | None, local: dict | None) -> bool:
    """Resolve [git].enabled with local overriding shared. Default: True.

    Git sync is on by default, and the machine-local opt-out (`[git].enabled =
    false` in `relay.local.toml`) is for repos with no remote —
    dev/CI/single-developer checkouts.
    """
    for table in (local, shared):
        if isinstance(table, dict) and "enabled" in table:
            value = table["enabled"]
            if not isinstance(value, bool):
                raise ConfigError(
                    f"[git].enabled must be a boolean (got {type(value).__name__})"
                )
            return value
    return True


def _parse_git(shared: dict | None) -> tuple[str, str]:
    """Parse `[git]` for `remote` / `control_branch`, with sane defaults.

    Defaults to `origin` / `main`. The `enabled` key is resolved separately
    (`_resolve_git_enabled`) so it can pick up a `relay.local.toml` override.
    """
    remote = "origin"
    control_branch = "main"
    if shared is None:
        return remote, control_branch
    if not isinstance(shared, dict):
        raise ConfigError(f"[git] must be a table (got {type(shared).__name__})")
    if "remote" in shared:
        value = shared["remote"]
        if not isinstance(value, str) or not value.strip():
            raise ConfigError("[git].remote must be a non-empty string")
        remote = value.strip()
    if "control_branch" in shared:
        value = shared["control_branch"]
        if not isinstance(value, str) or not value.strip():
            raise ConfigError("[git].control_branch must be a non-empty string")
        control_branch = value.strip()
    return remote, control_branch


def _parse_launch(shared: dict | None) -> tuple[float | None, bool, float | None]:
    """Parse `[launch]` for the recurring sweep's liveness limits.

    `idle_timeout` / `max_session` are seconds (int or float). A `<= 0` or
    non-finite value disarms that limit (returns None), matching the env-var
    override's "off" contract in `relay.commands.recurring`. `idle_timeout`
    returns a separate presence flag so an explicit disarm can beat the built-in
    recurring default; omitted keys are None/False. These are defaults for the
    *unattended* sweep only — attended `relay launch` never reads them.
    """
    if shared is None:
        return None, False, None
    if not isinstance(shared, dict):
        raise ConfigError(f"[launch] must be a table (got {type(shared).__name__})")
    _reject_unknown_keys(shared, _ALLOWED_LAUNCH_KEYS, "[launch]")

    def _seconds(key: str) -> float | None:
        if key not in shared:
            return None
        value = shared[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigError(f"[launch].{key} must be a number (got {value!r})")
        seconds = float(value)
        if not math.isfinite(seconds) or seconds <= 0:
            return None
        return seconds

    return _seconds("idle_timeout"), "idle_timeout" in shared, _seconds("max_session")


def _resolve_secret_value(value: str) -> str:
    """Resolve an `env:VAR` reference to the env var's value; pass literals through.

    A missing env var resolves to the empty string here. This is only used for
    `[notification.slack].webhook`, where an unset var collapsing to "" (then
    `or None`) correctly means "no webhook configured". `[secrets]` does **not**
    use this — it goes through `_resolve_secrets`, which keeps provenance so an
    unset env var can fail loud at launch instead of being injected as "". The
    notification layer also keeps a deprecated bare `SLACK_WEBHOOK_URL` fallback
    for legacy repos.
    """
    if value.startswith("env:"):
        return os.environ.get(value[len("env:") :], "")
    return value


def _resolve_secrets(raw: dict) -> dict[str, SecretValue]:
    """Resolve `[secrets]` into `SecretValue`s, retaining provenance.

    Unlike a plain string map, this preserves the `env:VAR` reference and the
    unset-vs-empty-literal distinction: an `env:VAR` whose var is unset resolves
    to `value=None` (not `""`), so `relay launch` can fail loud naming the var
    and `relay validate` can warn — neither of which is possible once the
    reference is flattened away. Literals and set env vars carry their string.

    An `op://vault/item/field` 1Password reference is recorded as `op_ref` with
    `value=None` and is **not** resolved here: shelling out to `op read` at
    config-load time would prompt 1Password on every command. Op references are
    resolved on demand by `select_launch_secrets` — only when a ticket's
    explicit `secrets:` list selects the key, or a human runs
    `relay secret get`. Prefix dispatch lives here (the extension seam for new
    providers is another explicit branch), not in a provider registry.
    """
    out: dict[str, SecretValue] = {}
    for key, value in raw.items():
        if not isinstance(value, str):
            raise ConfigError(f"secrets.{key} must be a string (got {type(value).__name__})")
        if value.startswith("env:"):
            env_var = value[len("env:") :]
            resolved = os.environ.get(env_var)  # None when unset — kept distinct from ""
            out[key] = SecretValue(raw=value, env_var=env_var, value=resolved)
        elif value.startswith("op://"):
            # Deferred: value stays None until resolved on demand. Never read here.
            out[key] = SecretValue(raw=value, env_var=None, value=None, op_ref=value)
        else:
            out[key] = SecretValue(raw=value, env_var=None, value=value)
    return out


def _resolve_op_reference(key: str, ref: str) -> str:
    """Resolve a 1Password `op://` reference by shelling out to `op read`.

    Passes the reference URI verbatim to `op read` — Relay does not parse
    vault/item/field. Strips only the single trailing newline `op` prints; the
    secret is otherwise returned untransformed. Raises `SecretError` (naming the
    Relay secret key and reference, never the value) when `op` is not installed
    or `op read` returns non-zero.
    """
    try:
        result = subprocess.run(
            ["op", "read", ref],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise SecretError(
            f"secret {key!r} references {ref!r} but the 1Password CLI `op` is "
            "not installed or not on PATH"
        ) from exc
    if result.returncode != 0:
        detail = result.stderr.strip()
        raise SecretError(
            f"secret {key!r}: `op read {ref}` failed (exit {result.returncode})"
            + (f": {detail}" if detail else "")
        )
    out = result.stdout
    if out.endswith("\n"):
        out = out[:-1]
    return out


def select_launch_secrets(cfg: Config, declared: object) -> dict[str, str]:
    """Build the env-var secret map a `relay launch` should inject.

    `declared` is the ticket's raw `secrets:` frontmatter value. Three cases
    (absent and explicit `null` both arrive here as `None`):

    - `None` (absent / null) → **legacy blanket**: every `[secrets]` entry that
      resolves. Unset `env:VAR` secrets are skipped, never injected as "". An
      `op://` reference has `value is None` (deferred) so it is skipped too —
      blanket mode never prompts 1Password for every configured op secret. A
      task that needs an op secret must declare that key explicitly.
    - `[]` (explicit empty list) → **strict lockdown**: inject nothing.
    - non-empty list → **least privilege**: inject only the listed keys; raise
      `SecretError` (fail loud, no agent spawned) on any key not in `[secrets]`,
      whose `env:VAR` points at an unset var, or whose `op://` reference cannot
      be resolved. `op://` keys are resolved live here via `op read`.

    `None` and `[]` must stay distinct — do not collapse with `declared or []`.
    """
    if declared is None:
        return {
            key: sv.value
            for key, sv in cfg.secrets.items()
            if sv.value is not None
        }
    if not isinstance(declared, list):
        raise SecretError(
            f"ticket `secrets:` must be a list of secret keys "
            f"(got {type(declared).__name__})"
        )
    if not declared:
        return {}
    env: dict[str, str] = {}
    for key in declared:
        if not isinstance(key, str):
            raise SecretError(
                f"ticket `secrets:` entries must be strings (got {key!r})"
            )
        sv = cfg.secrets.get(key)
        if sv is None:
            raise SecretError(
                f"ticket declares secret {key!r} but it is not defined in "
                "[secrets] in relay.local.toml"
            )
        if sv.op_ref is not None:
            env[key] = _resolve_op_reference(key, sv.op_ref)
            continue
        if sv.value is None:
            raise SecretError(
                f"ticket declares secret {key!r} but its env var "
                f"{sv.env_var!r} is not set"
            )
        env[key] = sv.value
    return env


def build_launch_env(
    cfg: Config,
    declared: object,
    *,
    base_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build a child process env with Relay secrets scoped and source vars scrubbed.

    Relay resolves `[secrets]` from operator env vars such as `env:STRIPE_KEY`,
    but the spawned agent/script must only receive the scoped Relay secret keys
    (for example `stripe_key`), not every raw source env var inherited from
    `os.environ.copy()`. Scrub all configured source variables first, then add
    back only `select_launch_secrets`' selected aliases.
    """
    env = dict(os.environ if base_env is None else base_env)
    selected = select_launch_secrets(cfg, declared)
    for sv in cfg.secrets.values():
        if sv.env_var is not None:
            env.pop(sv.env_var, None)
    env.update(selected)
    return env
