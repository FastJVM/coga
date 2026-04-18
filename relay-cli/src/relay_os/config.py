"""Config loading — relay.toml + relay.local.toml.

Every CLI command starts by calling ``RelayConfig.load()``. This module
parses both TOML files, validates the schema with pydantic, checks
cross-references (assignee nicknames -> agent types, paths -> projects),
and resolves ``env:VAR_NAME`` references in the secrets map to their
current environment values.

All failures raise ``ConfigError`` with messages written for end users —
what's wrong and how to fix it. The CLI surface catches and displays
them; downstream code shouldn't see them.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError


# --------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------


class ConfigError(Exception):
    """Any config-loading or validation failure. Messages target end
    users, not Python tracebacks."""


# --------------------------------------------------------------------
# Shared config (relay.toml) — committed, defines projects / agents /
# assignees / slack placeholder
# --------------------------------------------------------------------


StatusName = Literal[
    "design", "ready", "active", "paused", "done", "canceled", "failed"
]


class ProjectSpec(BaseModel):
    """A project definition from ``[projects.<name>]`` in relay.toml.

    ``type="repo"`` projects have a git remote; ``type="local"`` projects
    live inside this repo. The on-disk path is set per-machine in
    ``relay.local.toml`` ``[paths]``.
    """

    type: Literal["local", "repo"]
    default_status: StatusName = "ready"
    remote: str | None = None


class AgentSpec(BaseModel):
    """An agent type from ``[agents.<name>]`` in relay.toml.

    ``cli`` is the binary name on PATH. ``interactive`` and ``auto`` are
    the CLI flags used for prompt-loading in each mode. ``file`` is the
    fallback instruction file for agents without prompt injection.
    """

    cli: str
    interactive: str
    auto: str
    file: str
    mode: Literal["local"] = "local"


class AssigneeSpec(BaseModel):
    """A human from ``[assignees.<user>]`` in relay.toml.

    ``agents`` maps per-user nicknames to agent type names — e.g.
    ``{"claude1": "claude"}``. Nicknames are scoped to the user, so
    Zach's ``claude1`` and a teammate's ``claude1`` are independent.
    ``slack`` is the Slack user ID (starts with ``U``) for @mentions;
    empty string means no mention.
    """

    agents: dict[str, str] = Field(default_factory=dict)
    slack: str = ""


class SlackConfig(BaseModel):
    """Placeholder for ``[slack]`` in relay.toml. The webhook URL lives
    in ``relay.local.toml`` ``[secrets]`` (so it's never committed).
    This section exists for forward compatibility."""

    model_config = {"extra": "allow"}


class SharedConfig(BaseModel):
    """Root of relay.toml.

    ``version`` is pinned to ``1``. Bumping the schema version is a
    deliberate breaking-change event — when it happens, this Literal
    flips and callers get a clear load-time error rather than silently
    reading a newer schema with old expectations.
    """

    version: Literal[1] = 1
    projects: dict[str, ProjectSpec] = Field(default_factory=dict)
    agents: dict[str, AgentSpec] = Field(default_factory=dict)
    assignees: dict[str, AssigneeSpec] = Field(default_factory=dict)
    slack: SlackConfig = Field(default_factory=SlackConfig)


# --------------------------------------------------------------------
# Local config (relay.local.toml) — gitignored, per-machine
# --------------------------------------------------------------------


class LocalConfig(BaseModel):
    """Root of relay.local.toml.

    ``user`` is the person on this machine — used to resolve agent
    nicknames and attribute actions. ``paths`` maps project names to
    filesystem paths (absolute, relative to repo root, or ``~``-prefixed).
    ``secrets`` holds key → value mappings where values may be
    ``env:VAR_NAME`` references (resolved at load time).
    """

    user: str
    paths: dict[str, str] = Field(default_factory=dict)
    secrets: dict[str, str] = Field(default_factory=dict, repr=False)


# --------------------------------------------------------------------
# Combined config with accessors
# --------------------------------------------------------------------


class RelayConfig(BaseModel):
    """Loaded and validated config. Construct via :meth:`load`."""

    root: Path
    shared: SharedConfig
    local: LocalConfig
    # repr=False so accidental print(config) / debugger inspection
    # doesn't dump secret values. Callers access via .secret(key) or
    # .secrets_env() deliberately.
    resolved_secrets: dict[str, str] = Field(default_factory=dict, repr=False)

    # -- Accessors --

    @property
    def current_user(self) -> str:
        """The user on this machine (from relay.local.toml)."""
        return self.local.user

    @property
    def slack_webhook(self) -> str | None:
        """Resolved Slack webhook URL, or None if unconfigured."""
        return self.secret("slack_webhook")

    def project(self, name: str) -> ProjectSpec | None:
        """Project definition by name, or None if unknown."""
        return self.shared.projects.get(name)

    def project_path(self, name: str) -> Path | None:
        """Absolute on-disk path for a project, or None if unmapped
        on this machine. Relative paths resolve against the repo root;
        ``~`` is expanded."""
        raw = self.local.paths.get(name)
        if raw is None:
            return None
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = (self.root / p).resolve()
        return p

    def agent(self, name: str) -> AgentSpec | None:
        """Agent type by name, or None if unknown."""
        return self.shared.agents.get(name)

    def resolve_assignee(self, nickname: str) -> AgentSpec | None:
        """Resolve the current user's nickname (e.g. ``claude1``) to the
        agent spec it refers to. Returns None if the current user has no
        assignee block or the nickname isn't mapped."""
        assignee = self.shared.assignees.get(self.current_user)
        if assignee is None:
            return None
        agent_type = assignee.agents.get(nickname)
        if agent_type is None:
            return None
        return self.agent(agent_type)

    def slack_user(self, user: str) -> str | None:
        """Slack user ID for the named human, or None if unset."""
        assignee = self.shared.assignees.get(user)
        if assignee is None or not assignee.slack:
            return None
        return assignee.slack

    def secret(self, key: str) -> str | None:
        """Resolved secret value by key. Returns None if the key is
        unset, or if the referenced env var resolved to empty."""
        val = self.resolved_secrets.get(key)
        return val if val else None

    def secrets_env(self) -> dict[str, str]:
        """All resolved non-empty secrets as a dict. Intended for
        ``relay launch`` to inject into the environment of the agent or
        script it spawns. Empty values (unset env vars) are filtered
        out — downstream features should silently no-op rather than see
        ``KEY=""``."""
        return {k: v for k, v in self.resolved_secrets.items() if v}

    def missing_secrets(self) -> list[str]:
        """Keys whose ``env:VAR_NAME`` references resolved to empty
        because the environment variable isn't set.

        The resolver itself is fail-open — unset env vars become empty
        strings so the feature that needs them silently no-ops. This
        method gives callers (``relay launch``, a future ``relay doctor``)
        a way to surface the unset vars without changing that contract:
        *"heads up, `slack_webhook` is unset, Slack posts won't work."*

        Literal secret values (not ``env:`` references) are never
        counted as missing, even if the literal is an empty string.
        """
        return [
            key
            for key, raw in self.local.secrets.items()
            if raw.startswith("env:") and not self.resolved_secrets.get(key)
        ]

    # -- Loader --

    @classmethod
    def load(cls, start: Path | None = None) -> "RelayConfig":
        """Find ``relay.toml`` (walking up from ``start`` or CWD), parse
        both config files, validate schema + cross-references, resolve
        env-var secrets, and return the combined config.

        Raises :class:`ConfigError` on any failure with a user-facing
        message."""
        root = find_repo_root(start)
        shared_raw = _parse_toml(root / "relay.toml")
        local_path = root / "relay.local.toml"
        local_raw = (
            _parse_toml(local_path)
            if local_path.exists()
            else {"user": os.environ.get("USER", "unknown")}
        )

        try:
            shared = SharedConfig.model_validate(shared_raw)
        except ValidationError as e:
            raise ConfigError(f"invalid relay.toml:\n{e}") from e
        try:
            local = LocalConfig.model_validate(local_raw)
        except ValidationError as e:
            raise ConfigError(f"invalid relay.local.toml:\n{e}") from e

        _validate_cross_references(shared, local)
        resolved = _resolve_secrets(local.secrets)

        return cls(
            root=root,
            shared=shared,
            local=local,
            resolved_secrets=resolved,
        )


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------


def find_repo_root(start: Path | None = None) -> Path:
    """Walk up from ``start`` (or CWD) looking for ``relay.toml``.
    Raises :class:`ConfigError` if the filesystem root is reached
    without finding one."""
    p = Path(start or os.getcwd()).resolve()
    for d in [p, *p.parents]:
        if (d / "relay.toml").exists():
            return d
    raise ConfigError(
        f"not inside a Relay repo (no relay.toml found walking up from {p})"
    )


def _parse_toml(path: Path) -> dict:
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {path}")
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"invalid TOML in {path}: {e}") from e


def _validate_cross_references(
    shared: SharedConfig, local: LocalConfig
) -> None:
    """Pydantic can't know that ``assignees.zach.agents.claude1 =
    "claude"`` requires ``[agents.claude]`` to exist. These are
    application-level invariants. We check them here so failures
    surface at load time, not later when some command tries to use
    the broken reference."""
    agent_names = set(shared.agents.keys())
    for user, assignee in shared.assignees.items():
        for nickname, agent_type in assignee.agents.items():
            if agent_type not in agent_names:
                raise ConfigError(
                    f"assignees.{user}.agents.{nickname} = {agent_type!r}: "
                    f"no such agent type. Valid agent types: "
                    f"{sorted(agent_names)}"
                )

    project_names = set(shared.projects.keys())
    for name in local.paths:
        if name not in project_names:
            raise ConfigError(
                f"paths.{name}: no project named {name!r} in relay.toml. "
                f"Valid projects: {sorted(project_names)}"
            )


def _resolve_secrets(secrets: dict[str, str]) -> dict[str, str]:
    """Resolve ``env:VAR_NAME`` references to current env values.

    Unset env vars resolve to empty string so the matching feature (e.g.
    Slack feed) silently no-ops rather than crashing — matches the
    existing Relay contract. Malformed references (``env:`` with no
    variable name) raise :class:`ConfigError`."""
    resolved: dict[str, str] = {}
    for key, raw in secrets.items():
        if raw.startswith("env:"):
            var_name = raw[len("env:"):]
            if not var_name:
                raise ConfigError(
                    f"secret {key!r}: 'env:' reference missing variable name"
                )
            resolved[key] = os.environ.get(var_name, "")
        else:
            resolved[key] = raw
    return resolved
