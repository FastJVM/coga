"""Load and merge relay.toml + relay.local.toml."""

from __future__ import annotations

import math
import os
import random
import shlex
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(Exception):
    """Raised for any invalid/missing config."""


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
    written into every freshly scaffolded ticket below the
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
    slack_webhook: str | None
    slack_enabled: bool
    secrets: dict[str, str]
    slack_gifs: dict[str, list[str]] = field(default_factory=dict)
    slack_users: dict[str, str] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)
    ticket_fields: dict[str, TicketField] = field(default_factory=dict)
    extra_local: dict[str, object] = field(default_factory=dict)
    # Git sync — the git analogue of Slack. `git_enabled` follows the same
    # local-overrides-shared resolution as `slack_enabled`; `git_remote` /
    # `git_control_branch` come from shared `[git]`. See `relay.git`.
    git_enabled: bool = True
    git_remote: str = "origin"
    git_control_branch: str = "main"
    # Liveness limits for the interactive REPLs `relay recurring` spawns, from
    # the shared `[launch]` table. None = unset (no limit from config). The env
    # overrides (`RELAY_REPL_IDLE_TIMEOUT` / `RELAY_REPL_MAX_SESSION`) still win
    # over these; see `relay.commands.recurring`. Attended `relay launch` does
    # not read them — only the unattended sweep arms a limit, so a human's
    # session is never killed by a committed default.
    launch_idle_timeout: float | None = None
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
        """First-declared agent type, used as the scaffold-time default.

        TOML preserves declaration order, so the team puts their default
        first in `relay.toml`.
        """
        if not self.agents:
            return None
        first = next(iter(self.agents))
        return self.agents[first]

    def gif_for(self, kind: str) -> str | None:
        """Pick a random GIF URL for `kind` (e.g. "done", "panic"), or None.

        Configured under `[slack.gifs]` in relay.toml as `kind = ["url", ...]`.
        Empty/missing → None, and the caller posts text-only.
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

    default_status = shared.get("default_status", "draft")
    agents = _parse_agents(shared.get("agents", {}), local.get("agents", {}))
    if "assignees" in shared:
        raise ConfigError(
            "[assignees] is no longer supported in relay.toml. Remove the "
            "[assignees.*] tables — ticket `assignee:` now names an agent "
            "type (e.g. `claude`) or a human directly. See docs/spec.md."
        )
    # The webhook is read from `[slack].webhook` (local overriding shared) and
    # resolves `env:` indirection like any other secret. The bare process
    # environment is not a second source: `SLACK_WEBHOOK_URL` only reaches relay
    # when a `webhook = "env:SLACK_WEBHOOK_URL"` key points at it.
    slack_webhook = _resolve_slack_webhook(shared.get("slack"), local.get("slack"))
    # `[slack].enabled = false` (in either toml) is the explicit opt-out.
    # Local overrides shared. Default is enabled — slack is the team sync point.
    slack_enabled = _resolve_slack_enabled(shared.get("slack"), local.get("slack"))
    slack_gifs = _parse_slack_gifs(shared.get("slack"))
    slack_users = _parse_slack_users(shared.get("slack"))
    aliases = _parse_aliases(shared.get("aliases", {}))
    ticket_fields = _parse_ticket_fields(shared.get("ticket"))
    git_enabled = _resolve_git_enabled(shared.get("git"), local.get("git"))
    git_remote, git_control_branch = _parse_git(shared.get("git"))
    launch_idle_timeout, launch_max_session = _parse_launch(shared.get("launch"))

    current_user = local.get("user")
    if not current_user:
        raise ConfigError(
            f"`user` is missing from {local_path}. "
            "Set it to your name, e.g. `user = \"marc\"`."
        )

    secrets = _resolve_secrets(local.get("secrets", {}))

    extra_local = {k: v for k, v in local.items() if k not in {"user", "secrets"}}

    return Config(
        repo_root=root,
        current_user=current_user,
        default_status=default_status,
        agents=agents,
        slack_webhook=slack_webhook,
        slack_enabled=slack_enabled,
        slack_gifs=slack_gifs,
        slack_users=slack_users,
        secrets=secrets,
        aliases=aliases,
        ticket_fields=ticket_fields,
        extra_local=extra_local,
        git_enabled=git_enabled,
        git_remote=git_remote,
        git_control_branch=git_control_branch,
        launch_idle_timeout=launch_idle_timeout,
        launch_max_session=launch_max_session,
    )


# --- parsing helpers -----------------------------------------------------------


def _read_toml(path: Path) -> dict:
    if not path.is_file():
        raise ConfigError(f"Missing config file: {path}")
    with path.open("rb") as f:
        return tomllib.load(f)


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
})

_ALLOWED_TICKET_FIELD_KEYS: frozenset[str] = frozenset({
    "description",
    "values",
    "default",
    "required",
})


def _parse_ticket_fields(raw: dict | None) -> dict[str, TicketField]:
    """Parse `[ticket.fields.<name>]` tables into `TicketField` records.

    Order in TOML is preserved (insertion order on dict), so scaffold writes
    extension fields in declaration order.
    """
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError(
            f"[ticket] must be a table (got {type(raw).__name__})"
        )
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


def _parse_slack_gifs(shared: dict | None) -> dict[str, list[str]]:
    """Parse `[slack.gifs]` table — each key maps an event-kind to a list of URLs.

    A random URL is picked per post. Missing/empty → text-only Slack messages.
    """
    if not isinstance(shared, dict):
        return {}
    gifs = shared.get("gifs")
    if gifs is None:
        return {}
    if not isinstance(gifs, dict):
        raise ConfigError(
            f"[slack.gifs] must be a table (got {type(gifs).__name__})"
        )
    out: dict[str, list[str]] = {}
    for kind, urls in gifs.items():
        if not isinstance(urls, list) or not all(isinstance(u, str) for u in urls):
            raise ConfigError(
                f"[slack.gifs].{kind} must be a list of URL strings"
            )
        cleaned = [u.strip() for u in urls if u.strip()]
        if cleaned:
            out[kind] = cleaned
    return out


def _parse_slack_users(shared: dict | None) -> dict[str, str]:
    """Parse `[slack.users]` — maps a relay name (the token used in a
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
            f"[slack.users] must be a table (got {type(users).__name__})"
        )
    out: dict[str, str] = {}
    for name, user_id in users.items():
        if not isinstance(user_id, str) or not user_id.strip():
            raise ConfigError(
                f"[slack.users].{name} must be a non-empty Slack member ID string"
            )
        out[name] = user_id.strip()
    return out


def _resolve_slack_webhook(shared: dict | None, local: dict | None) -> str | None:
    """Resolve `[slack].webhook` with local overriding shared. Default: None.

    The value may be a literal URL or an `env:VAR` reference resolved the same
    way `[secrets]` are (see `_resolve_secret_value`). This is the *only* webhook
    source — the bare process environment is not a second, independent one:
    `SLACK_WEBHOOK_URL` reaches relay only when a `webhook = "env:SLACK_WEBHOOK_URL"`
    key points at it. An `env:` whose var is unset (or an empty literal) resolves
    to None — i.e. unconfigured — matching `slack_webhook`'s `str | None` contract
    and the "enabled but no webhook" crash path in `slack.post`.

    `[slack].webhook` is a machine-specific secret, so `relay.local.toml` may
    carry it and override a safe `env:` reference (or omitted key) in shared
    `relay.toml`. Examples and docs steer users to `env:` indirection; a literal
    URL is accepted by the parser but must never be committed.
    """
    for table in (local, shared):
        if isinstance(table, dict) and "webhook" in table:
            value = table["webhook"]
            if not isinstance(value, str):
                raise ConfigError(
                    f"[slack].webhook must be a string (got {type(value).__name__})"
                )
            return _resolve_secret_value(value) or None
    return None


def _resolve_slack_enabled(shared: dict | None, local: dict | None) -> bool:
    """Resolve [slack].enabled with local overriding shared. Default: True."""
    for table in (local, shared):
        if isinstance(table, dict) and "enabled" in table:
            value = table["enabled"]
            if not isinstance(value, bool):
                raise ConfigError(
                    f"[slack].enabled must be a boolean (got {type(value).__name__})"
                )
            return value
    return True


def _resolve_git_enabled(shared: dict | None, local: dict | None) -> bool:
    """Resolve [git].enabled with local overriding shared. Default: True.

    Mirrors `_resolve_slack_enabled`: git sync is on by default, and the
    machine-local opt-out (`[git].enabled = false` in `relay.local.toml`) is
    for repos with no remote — dev/CI/single-developer checkouts.
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


def _parse_launch(shared: dict | None) -> tuple[float | None, float | None]:
    """Parse `[launch]` for the recurring sweep's liveness limits.

    `idle_timeout` / `max_session` are seconds (int or float). A `<= 0` or
    non-finite value disarms that limit (returns None), matching the env-var
    override's "off" contract in `relay.commands.recurring`. Omitted keys are
    None. These are defaults for the *unattended* sweep only — attended
    `relay launch` never reads them.
    """
    if shared is None:
        return None, None
    if not isinstance(shared, dict):
        raise ConfigError(f"[launch] must be a table (got {type(shared).__name__})")

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

    return _seconds("idle_timeout"), _seconds("max_session")


def _resolve_secret_value(value: str) -> str:
    """Resolve an `env:VAR` reference to the env var's value; pass literals through.

    A missing env var resolves to the empty string — secrets are validated at
    launch time when they're actually needed, not at config load. Shared by
    `[secrets]` and `[slack].webhook`, which both treat the bare environment as
    reachable only through an explicit `env:` reference.
    """
    if value.startswith("env:"):
        return os.environ.get(value[len("env:") :], "")
    return value


def _resolve_secrets(raw: dict) -> dict[str, str]:
    """Resolve `env:VAR` references to the env var's current value.

    Missing env vars resolve to empty strings — secrets are validated at launch
    time when they're actually needed, not at config load.
    """
    out: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(value, str):
            raise ConfigError(f"secrets.{key} must be a string (got {type(value).__name__})")
        out[key] = _resolve_secret_value(value)
    return out
