"""Config loading. Walks up from CWD to find relay.toml, then reads both
shared (relay.toml) and per-machine (relay.local.toml) config."""
import os
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore
    except ImportError as e:
        raise SystemExit(
            "error: Relay requires Python 3.11+ (for stdlib tomllib) or the "
            "`tomli` package on older Python. Install with: pip install tomli"
        ) from e


def find_repo_root(start=None) -> Path:
    """Walk up from start (or cwd) looking for relay.toml."""
    p = Path(start or os.getcwd()).resolve()
    for d in [p, *p.parents]:
        if (d / "relay.toml").exists():
            return d
    raise SystemExit(
        "error: not inside a Relay repo (no relay.toml found walking up from "
        f"{p})"
    )


class Config:
    def __init__(self, start=None):
        self.root = find_repo_root(start)
        with (self.root / "relay.toml").open("rb") as f:
            self.shared = tomllib.load(f)
        local_path = self.root / "relay.local.toml"
        if local_path.exists():
            with local_path.open("rb") as f:
                self.local = tomllib.load(f)
        else:
            self.local = {}

    # --- Accessors ---

    @property
    def user(self):
        return self.local.get("user")

    def project(self, name):
        return self.shared.get("projects", {}).get(name)

    def project_path(self, name) -> Path | None:
        paths = self.local.get("paths", {}) or {}
        raw = paths.get(name)
        if not raw:
            return None
        expanded = Path(os.path.expanduser(raw))
        if not expanded.is_absolute():
            expanded = (self.root / expanded).resolve()
        else:
            expanded = expanded.resolve()
        return expanded

    def agent_type(self, name):
        return self.shared.get("agents", {}).get(name)

    def resolve_assignee(self, nickname):
        """Given an assignee nickname, return the agent type config dict.
        Returns None if the nickname is not a known agent for the current
        user (i.e. it's a human, or the user isn't set)."""
        user = self.user
        if not user:
            return None
        assignees = self.shared.get("assignees", {}) or {}
        me = assignees.get(user) or {}
        agents = me.get("agents") or {}
        agent_type_name = agents.get(nickname)
        if not agent_type_name:
            return None
        return self.agent_type(agent_type_name)

    def assignee_slack(self, user):
        """Slack user ID for a given user, if configured."""
        assignees = self.shared.get("assignees", {}) or {}
        return (assignees.get(user) or {}).get("slack") or None

    def secret(self, key):
        """Resolve a secret reference. Returns the resolved string or None."""
        secrets = self.local.get("secrets", {}) or {}
        val = secrets.get(key)
        if not isinstance(val, str) or not val:
            return None
        if val.startswith("env:"):
            return os.environ.get(val[4:])
        return val

    def secrets_env(self) -> dict:
        """Build a dict of env-ready secrets to inject at launch time."""
        out = {}
        secrets = self.local.get("secrets", {}) or {}
        for key, val in secrets.items():
            if not isinstance(val, str):
                continue
            if val.startswith("env:"):
                src = val[4:]
                if src in os.environ:
                    out[key.upper()] = os.environ[src]
            else:
                out[key.upper()] = val
        return out
