"""Load and merge relay.toml + relay.local.toml."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(Exception):
    """Raised for any invalid/missing config."""


@dataclass(frozen=True)
class AgentType:
    name: str
    cli: str
    interactive: str
    auto: str
    file: str
    mode: str               # "local" | future: "remote" | "cloud"


@dataclass(frozen=True)
class Assignee:
    name: str
    agents: dict[str, str]  # nickname -> agent type name
    slack: str | None


@dataclass(frozen=True)
class Config:
    repo_root: Path
    current_user: str
    default_status: str
    agents: dict[str, AgentType]
    assignees: dict[str, Assignee]
    slack_webhook: str | None
    secrets: dict[str, str]
    aliases: dict[str, str] = field(default_factory=dict)
    extra_local: dict[str, object] = field(default_factory=dict)

    # --- convenience accessors -------------------------------------------------

    def assignee(self, name: str) -> Assignee:
        if name not in self.assignees:
            raise ConfigError(f"Unknown assignee: {name!r}. Known: {sorted(self.assignees)}")
        return self.assignees[name]

    def agent_type_for(self, user: str, nickname: str) -> AgentType:
        """Resolve (user, nickname) -> AgentType."""
        who = self.assignee(user)
        if nickname not in who.agents:
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
    slack_webhook = (shared.get("slack") or {}).get("webhook")
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
        for required in ("cli", "interactive", "auto", "file"):
            if required not in data:
                raise ConfigError(f"agents.{name}.{required} is required")
        out[name] = AgentType(
            name=name,
            cli=data["cli"],
            interactive=data["interactive"],
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
            slack=data.get("slack"),
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
