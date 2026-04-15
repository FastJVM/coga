"""Config loading — relay.toml (shared) + relay.local.toml (per-machine).

Every CLI command depends on this. Walks up from the caller's CWD to
find `relay.toml`, parses both files with stdlib `tomllib`, validates
cross-references (assignees -> agent types, paths -> projects), and
resolves `env:VAR_NAME` references in the [secrets] section to their
actual environment variable values at load time.

All failures raise `ConfigError` with a message that tells the caller
how to fix the problem. The CLI layer is responsible for catching
`ConfigError` and presenting it to the user (e.g. non-zero exit with
the error on stderr).

The spec treats shared config as "the what" and local config as "the
where and the credentials" — projects and agents are defined in
`relay.toml` (committed), paths and secrets are defined in
`relay.local.toml` (gitignored, per-machine).
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(Exception):
    """Raised on any config-loading or validation failure.

    Messages are written for end users — they should describe what's
    wrong and how to fix it, not expose Python internals. The CLI
    catches this and surfaces it as a non-zero exit.
    """


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass(frozen=True)
class ProjectConfig:
    """A project location. `path` is None if the current machine's
    `relay.local.toml` doesn't set a path for this project — that's
    valid (a teammate may have a path, we may not), but launching a
    task in an unmapped project will fail later."""

    name: str
    type: str  # "repo" or "local"
    remote: str | None
    default_status: str
    path: Path | None


@dataclass(frozen=True)
class AgentConfig:
    """An agent type — the template for how to invoke this agent
    binary. Instances of an agent (nicknamed per-user) live in
    `AssigneeConfig.agents`."""

    name: str
    cli: str
    interactive: str
    auto: str
    file: str
    mode: str


@dataclass(frozen=True)
class AssigneeConfig:
    """A human assignee. `agents` maps this person's nicknames to
    agent type names (e.g. `{"claude1": "claude"}`). `slack` is the
    Slack user ID used for @mentions — None if unset."""

    user: str
    agents: dict[str, str]
    slack: str | None


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def find_repo_root(start: Path | None = None) -> Path:
    """Walk up from `start` (or CWD) looking for `relay.toml`."""
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
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"invalid TOML in {path}: {e}") from e


def _resolve_secret(raw: object, key: str) -> str:
    """Resolve a single [secrets] value. `env:VAR_NAME` looks up the
    environment variable (raises if unset). Any other string passes
    through as-is so users can hard-code a value if they want to."""
    if not isinstance(raw, str):
        raise ConfigError(
            f"secret {key!r}: expected string, got {type(raw).__name__}"
        )
    if not raw.startswith("env:"):
        return raw
    var_name = raw[len("env:") :]
    if not var_name:
        raise ConfigError(
            f"secret {key!r}: 'env:' reference is missing a variable name"
        )
    val = os.environ.get(var_name)
    if val is None:
        raise ConfigError(
            f"secret {key!r} references env var {var_name!r}, which is not "
            f"set. Either export {var_name} in your shell, or remove the line "
            f"from relay.local.toml."
        )
    return val


def _normalize_path(raw: str, root: Path) -> Path:
    expanded = Path(os.path.expanduser(raw))
    if not expanded.is_absolute():
        return (root / expanded).resolve()
    return expanded.resolve()


# ------------------------------------------------------------------
# Top-level config
# ------------------------------------------------------------------


@dataclass
class RelayConfig:
    root: Path
    user: str | None
    projects: dict[str, ProjectConfig] = field(default_factory=dict)
    agents: dict[str, AgentConfig] = field(default_factory=dict)
    assignees: dict[str, AssigneeConfig] = field(default_factory=dict)
    secrets: dict[str, str] = field(default_factory=dict)
    slack_webhook: str | None = None

    # ----- Loader -----

    @classmethod
    def load(cls, start: Path | None = None) -> "RelayConfig":
        root = find_repo_root(start)
        shared = _parse_toml(root / "relay.toml")
        local_path = root / "relay.local.toml"
        local = _parse_toml(local_path) if local_path.exists() else {}

        version = shared.get("version")
        if version != 1:
            raise ConfigError(
                f"{root / 'relay.toml'}: unsupported version {version!r} "
                f"(expected 1)"
            )

        user = local.get("user")
        paths_by_name = local.get("paths", {}) or {}

        projects = cls._load_projects(shared, paths_by_name, root)
        cls._validate_paths_reference_known_projects(paths_by_name, projects)
        agents = cls._load_agents(shared)
        assignees = cls._load_assignees(shared, agents)
        secrets = cls._load_secrets(local)

        # Slack webhook: prefer per-machine secret, fall back to shared config.
        slack_webhook = secrets.get("slack_webhook")
        if not slack_webhook:
            slack_webhook = (shared.get("slack") or {}).get("webhook") or None

        return cls(
            root=root,
            user=user,
            projects=projects,
            agents=agents,
            assignees=assignees,
            secrets=secrets,
            slack_webhook=slack_webhook,
        )

    # ----- Sub-loaders -----

    @staticmethod
    def _load_projects(
        shared: dict, paths_by_name: dict, root: Path
    ) -> dict[str, ProjectConfig]:
        projects: dict[str, ProjectConfig] = {}
        for name, raw in (shared.get("projects") or {}).items():
            ptype = raw.get("type")
            if ptype not in ("repo", "local"):
                raise ConfigError(
                    f"project {name!r}: type must be 'repo' or 'local', "
                    f"got {ptype!r}"
                )
            remote = raw.get("remote")
            if ptype == "repo" and not remote:
                raise ConfigError(
                    f"project {name!r}: type='repo' requires a 'remote' field"
                )
            raw_path = paths_by_name.get(name)
            path = _normalize_path(raw_path, root) if raw_path else None
            projects[name] = ProjectConfig(
                name=name,
                type=ptype,
                remote=remote,
                default_status=raw.get("default_status", "ready"),
                path=path,
            )
        return projects

    @staticmethod
    def _validate_paths_reference_known_projects(
        paths_by_name: dict, projects: dict[str, ProjectConfig]
    ) -> None:
        for path_name in paths_by_name:
            if path_name not in projects:
                known = sorted(projects) or ["(none)"]
                raise ConfigError(
                    f"relay.local.toml [paths]: {path_name!r} is not a project "
                    f"in relay.toml. Known projects: {', '.join(known)}"
                )

    @staticmethod
    def _load_agents(shared: dict) -> dict[str, AgentConfig]:
        agents: dict[str, AgentConfig] = {}
        for name, raw in (shared.get("agents") or {}).items():
            missing = [f for f in ("cli", "interactive", "auto", "file") if f not in raw]
            if missing:
                raise ConfigError(
                    f"agent {name!r}: missing required fields: "
                    f"{', '.join(missing)}"
                )
            agents[name] = AgentConfig(
                name=name,
                cli=raw["cli"],
                interactive=raw["interactive"],
                auto=raw["auto"],
                file=raw["file"],
                mode=raw.get("mode", "local"),
            )
        return agents

    @staticmethod
    def _load_assignees(
        shared: dict, agents: dict[str, AgentConfig]
    ) -> dict[str, AssigneeConfig]:
        assignees: dict[str, AssigneeConfig] = {}
        for user_name, raw in (shared.get("assignees") or {}).items():
            agent_map = dict(raw.get("agents") or {})
            for nickname, agent_type_name in agent_map.items():
                if agent_type_name not in agents:
                    known = sorted(agents) or ["(none)"]
                    raise ConfigError(
                        f"assignee {user_name!r} has agent nickname "
                        f"{nickname!r} mapped to unknown type "
                        f"{agent_type_name!r}. Known agent types: "
                        f"{', '.join(known)}"
                    )
            assignees[user_name] = AssigneeConfig(
                user=user_name,
                agents=agent_map,
                slack=raw.get("slack") or None,
            )
        return assignees

    @staticmethod
    def _load_secrets(local: dict) -> dict[str, str]:
        secrets: dict[str, str] = {}
        for key, raw in (local.get("secrets") or {}).items():
            secrets[key] = _resolve_secret(raw, key)
        return secrets

    # ----- Accessors -----

    def project(self, name: str) -> ProjectConfig:
        try:
            return self.projects[name]
        except KeyError:
            known = sorted(self.projects) or ["(none)"]
            raise ConfigError(
                f"unknown project {name!r}. Known: {', '.join(known)}"
            ) from None

    def agent(self, nickname: str, user: str | None = None) -> AgentConfig:
        """Resolve (user, nickname) -> AgentConfig.

        `user` defaults to the current user from relay.local.toml. The
        dispatch key is always (user, nickname) — nicknames are
        per-person, not global.
        """
        effective_user = user or self.user
        if effective_user is None:
            raise ConfigError(
                "cannot resolve agent: no user set in relay.local.toml and "
                "no explicit user argument provided"
            )
        if effective_user not in self.assignees:
            known = sorted(self.assignees) or ["(none)"]
            raise ConfigError(
                f"user {effective_user!r} is not configured in relay.toml "
                f"[assignees]. Known: {', '.join(known)}"
            )
        assignee = self.assignees[effective_user]
        if nickname not in assignee.agents:
            known = sorted(assignee.agents) or ["(none)"]
            raise ConfigError(
                f"user {effective_user!r} has no agent nicknamed "
                f"{nickname!r}. Known: {', '.join(known)}"
            )
        agent_type_name = assignee.agents[nickname]
        # Already validated at load time — this lookup cannot fail.
        return self.agents[agent_type_name]
