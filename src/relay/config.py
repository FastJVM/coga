"""Load and merge relay.toml + relay.local.toml."""

from __future__ import annotations

import os
import random
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


@dataclass(frozen=True)
class Assignee:
    name: str
    agents: dict[str, str]  # nickname -> agent type name


@dataclass(frozen=True)
class Config:
    repo_root: Path
    current_user: str
    default_status: str
    agents: dict[str, AgentType]
    assignees: dict[str, Assignee]
    slack_webhook: str | None
    slack_enabled: bool
    secrets: dict[str, str]
    slack_gifs: dict[str, list[str]] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)
    extra_local: dict[str, object] = field(default_factory=dict)

    # --- convenience accessors -------------------------------------------------

    @property
    def project_name(self) -> str:
        """Display name of the host repo. Parent of `relay-os/` when nested."""
        if self.repo_root.name == "relay-os":
            return self.repo_root.parent.name
        return self.repo_root.name

    def assignee(self, name: str) -> Assignee:
        if name not in self.assignees:
            raise ConfigError(f"Unknown assignee: {name!r}. Known: {sorted(self.assignees)}")
        return self.assignees[name]

    def agent_type_for(self, user: str, nickname: str) -> AgentType:
        """Resolve (user, nickname) -> AgentType."""
        who = self.assignee(user)
        if nickname not in who.agents:
            if nickname in self.assignees:
                raise ConfigError(
                    f"Ticket assignee {nickname!r} is a human user, not an agent. "
                    f"`relay launch` only runs agent assignees. "
                    f"Reassign to one of {sorted(who.agents)} or do the work yourself."
                )
            raise ConfigError(
                f"Assignee {user!r} has no agent nickname {nickname!r}. "
                f"Known nicknames: {sorted(who.agents)}"
            )
        type_name = who.agents[nickname]
        if type_name not in self.agents:
            raise ConfigError(
                f"Agent type {type_name!r} (from {user}.{nickname}) is not defined in [agents]."
            )
        return self.agents[type_name]

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
    agents = _parse_agents(shared.get("agents", {}))
    assignees = _parse_assignees(shared.get("assignees", {}))
    slack_webhook = os.environ.get("SLACK_WEBHOOK_URL")
    # `[slack].enabled = false` (in either toml) is the explicit opt-out.
    # Local overrides shared. Default is enabled — slack is the team sync point.
    slack_enabled = _resolve_slack_enabled(shared.get("slack"), local.get("slack"))
    slack_gifs = _parse_slack_gifs(shared.get("slack"))
    aliases = _parse_aliases(shared.get("aliases", {}))

    current_user = local.get("user")
    if not current_user:
        raise ConfigError(
            f"`user` is missing from {local_path}. "
            "Set it to your assignee name, e.g. `user = \"marc\"`."
        )
    if current_user not in assignees:
        raise ConfigError(
            f"Current user {current_user!r} not found in [assignees] of relay.toml."
        )

    secrets = _resolve_secrets(local.get("secrets", {}))

    extra_local = {k: v for k, v in local.items() if k not in {"user", "secrets"}}

    return Config(
        repo_root=root,
        current_user=current_user,
        default_status=default_status,
        agents=agents,
        assignees=assignees,
        slack_webhook=slack_webhook,
        slack_enabled=slack_enabled,
        slack_gifs=slack_gifs,
        secrets=secrets,
        aliases=aliases,
        extra_local=extra_local,
    )


# --- parsing helpers -----------------------------------------------------------


def _read_toml(path: Path) -> dict:
    if not path.is_file():
        raise ConfigError(f"Missing config file: {path}")
    with path.open("rb") as f:
        return tomllib.load(f)


def _parse_agents(raw: dict) -> dict[str, AgentType]:
    out: dict[str, AgentType] = {}
    for name, data in raw.items():
        for required in ("cli", "auto", "file"):
            if required not in data:
                raise ConfigError(f"agents.{name}.{required} is required")
        out[name] = AgentType(
            name=name,
            cli=data["cli"],
            auto=data["auto"],
            file=data["file"],
            mode=data.get("mode", "local"),
        )
    return out


def _parse_assignees(raw: dict) -> dict[str, Assignee]:
    out: dict[str, Assignee] = {}
    for name, data in raw.items():
        agents = data.get("agents", {})
        if not isinstance(agents, dict):
            raise ConfigError(f"assignees.{name}.agents must be a table (got {type(agents).__name__})")
        out[name] = Assignee(
            name=name,
            agents=dict(agents),
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


def _resolve_secrets(raw: dict) -> dict[str, str]:
    """Resolve `env:VAR` references to the env var's current value.

    Missing env vars resolve to empty strings — secrets are validated at launch
    time when they're actually needed, not at config load.
    """
    out: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(value, str):
            raise ConfigError(f"secrets.{key} must be a string (got {type(value).__name__})")
        if value.startswith("env:"):
            out[key] = os.environ.get(value[len("env:") :], "")
        else:
            out[key] = value
    return out
