"""Load and merge coga.toml + coga.local.toml."""

from __future__ import annotations

import math
import os
import random
import subprocess
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(Exception):
    """Raised for any invalid/missing config."""


class SecretError(Exception):
    """A ticket's declared secret cannot be satisfied at launch time.

    Raised by `select_launch_secrets` / `parse_inline_secrets` when a ticket's
    `secrets:` entry is malformed, holds a raw literal value (which may not live
    in a git-committed ticket), whose `env:VAR` indirection points at an unset
    env var, or whose `op://` reference cannot be resolved (the `op` CLI is
    missing or `op read` returns non-zero). `coga launch` turns this into a
    non-zero exit before any agent or script is spawned — the fail-loud
    guarantee. Messages name the Coga secret name and reference, never the
    resolved secret value.
    """


@dataclass(frozen=True)
class AgentType:
    name: str
    cli: str
    file: str
    mode: str               # "local" | future: "remote" | "cloud"
    # Flag (or flag template) the CLI accepts to set the session display name
    # at launch — e.g. `-n` for claude (shown in /resume, prompt box, terminal
    # title). Empty when the CLI has no such flag. Split with shlex; the
    # ticket title is appended as the next argv element. Skipped in
    # `discussion` mode so the human's first ask can name the session.
    name_flag: str = ""
    # Optional CLI flag that pins the launched agent session id. Empty when
    # the CLI does not expose one; Coga then falls back to provider-specific
    # transcript matching.
    session_id_flag: str = ""
    # Optional argv override for discussion prompts (`coga chat`, `coga ticket`):
    # the composed prompt rides as system/developer context instead of becoming
    # the agent's first user message. Parsed via `shlex.split`; the literal
    # token `{prompt}` is replaced with the composed prompt. Empty string lets
    # launch use its built-in defaults for known CLIs, then positional fallback.
    discussion: str = ""


@dataclass(frozen=True)
class TicketField:
    """A repo-declared extension to the canonical ticket frontmatter schema.

    Declared in `coga.toml` under `[ticket.fields.<name>]`. The field is
    written into every freshly created ticket below the
    `# --- extensions ---` marker, and `coga validate` / `coga mark active`
    enforce the declared constraints.
    """

    name: str
    description: str
    values: tuple[str, ...] | None = None  # enum constraint, None = free string
    default: str = ""
    required: bool = False


@dataclass(frozen=True)
class MegalaunchConfig:
    """Budget guard for unattended sequential launches.

    The live guard reads each agent's own subscription usage windows (see
    `coga.usage_probe`): a fixed session (5h-window) reserve floor, plus a
    weekly pacing reserve that requires ~100% remaining at the start of the
    weekly window and relaxes linearly down to the hard floor inside the
    final `weekly_final_window_hours`.
    """

    min_session_remaining_percent: float = 5.0
    min_weekly_remaining_percent: float = 5.0
    weekly_final_window_hours: float = 24.0
    # Deprecated, unused: the coga-tracked token budget the usage-window guard
    # replaced. Still parsed so existing coga.toml files keep loading; drop
    # these once live configs no longer set them.
    token_guard: int = 200_000
    default_token_budget: int = 2_000_000
    window_hours: int = 24
    agent_token_budgets: dict[str, int] = field(default_factory=dict)


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
    notification_channels: tuple[str, ...] = ("slack",)
    notification_deprecation_notes: tuple[str, ...] = ()
    slack_gifs: dict[str, list[str]] = field(default_factory=dict)
    slack_users: dict[str, str] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)
    # Repo-owned free-form config namespace. coga does not interpret it; its
    # contents pass through verbatim for skills/scripts to read (e.g.
    # `[extensions.patent] calendar_id = "..."`). Like `[aliases]`/`[secrets]`,
    # the keys are user data, not schema.
    extensions: dict[str, object] = field(default_factory=dict)
    ticket_fields: dict[str, TicketField] = field(default_factory=dict)
    # Git sync — the git analogue of Slack. `git_enabled` follows the same
    # local-overrides-shared resolution as `slack_enabled`; `git_remote` /
    # `git_control_branch` come from shared `[git]`. See `coga.git`.
    git_enabled: bool = True
    git_remote: str = "origin"
    git_control_branch: str = "main"
    # Liveness limits for the interactive REPLs `coga recurring` spawns, from
    # the shared `[launch]` table. None = no limit from config. The idle timeout
    # also keeps a presence flag because that limit has a built-in default:
    # `[launch].idle_timeout = 0` must explicitly disarm it rather than collapse
    # to "omitted" and re-enable the default. The env overrides
    # (`COGA_REPL_IDLE_TIMEOUT` / `COGA_REPL_MAX_SESSION`) still win over these;
    # see `coga.recurring_runner`. Attended `coga launch` does not read them
    # — only the unattended sweep arms a limit, so a human's session is never
    # killed by a committed default.
    launch_idle_timeout: float | None = None
    launch_idle_timeout_present: bool = False
    launch_max_session: float | None = None
    # When true (the default), each `coga launch` agent session runs in its own
    # per-launch `git worktree` (detached at the control-branch tip) instead of
    # the shared primary checkout, so concurrent agents on different tickets
    # never contend one `.git/index` / stash stack. Set `[launch].worktree =
    # false` to opt back into the shared single-checkout flow. Shared repo policy
    # (no `coga.local.toml` override) — read from the shared `[launch]` table.
    # See `coga.commands.launch`.
    launch_worktree: bool = True
    # Directory holding those per-launch worktrees. Relative paths resolve
    # against the git toplevel; absolute paths are used as-is. Default
    # `.coga/worktrees` sits under a gitignored `.coga/` so the primary
    # checkout's `git status` stays clean and the `sync_coga_state` sweep never
    # touches it — a custom in-repo path must be gitignored by the operator to
    # keep those properties. See `coga.git`.
    launch_worktree_path: str = ".coga/worktrees"
    megalaunch: MegalaunchConfig = field(default_factory=MegalaunchConfig)

    # --- convenience accessors -------------------------------------------------

    @property
    def project_name(self) -> str:
        """Display name of the host repo. Parent of `coga/` when nested."""
        if self.repo_root.name == "coga":
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
        first in `coga.toml`.
        """
        if not self.agents:
            return None
        first = next(iter(self.agents))
        return self.agents[first]

    def gif_for(self, kind: str) -> str | None:
        """Pick a random GIF URL for `kind` (e.g. "done", "block"), or None.

        Configured under `[notification.slack.gifs]` in coga.toml as
        `kind = ["url", ...]`. Empty/missing → None, and the caller posts
        text-only.
        """
        urls = self.slack_gifs.get(kind, [])
        return random.choice(urls) if urls else None


# --- discovery -----------------------------------------------------------------


def find_repo_root(start: Path | None = None) -> Path:
    """Walk up from `start` (default cwd) until a `coga.toml` is found.

    Also descends into a sibling `coga/` subdir at each level — so
    `coga` works from a company repo's root, not just from inside
    `coga/`.

    Discovery never descends deeper than that one `coga/` level: a coga repo
    nested in a monorepo subdir (`tools/ops/coga/`, via `coga init tools/ops`)
    is deliberately found only from inside its subtree, not from the host
    repo's root — scanning the whole tree downward would be slow and ambiguous
    with several nested coga repos.
    """
    cur = (start or Path.cwd()).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / "coga.toml").is_file():
            return candidate
        nested = candidate / "coga"
        if (nested / "coga.toml").is_file():
            return nested
    raise ConfigError(
        f"No coga.toml found in {cur} or any parent directory. "
        "Run `coga` from inside a Coga repo — a coga/ nested in a subdir "
        "is only discovered from inside that subdir's subtree."
    )


# --- loader --------------------------------------------------------------------


def load_config(repo_root: Path | None = None) -> Config:
    root = repo_root or find_repo_root()
    shared = _read_toml(root / "coga.toml")
    local_path = root / "coga.local.toml"
    local = _read_toml(local_path) if local_path.is_file() else {}

    version = shared.get("version")
    if version != 1:
        raise ConfigError(f"Unsupported coga.toml version: {version!r} (expected 1)")

    # `assignees` carries a dedicated migration message, so its raise must beat
    # the generic top-level unknown-key check below (which omits it).
    if "assignees" in shared:
        raise ConfigError(
            "[assignees] is no longer supported in coga.toml. Remove the "
            "[assignees.*] tables — ticket `assignee:` now names an agent "
            "type (e.g. `claude`) or a human directly. See docs/spec.md."
        )
    # Tailored migration error before the generic unknown-section check, so a
    # leftover `[secrets]` table gets the actionable "declare inline" message
    # rather than a bare "unknown key" one.
    if "secrets" in local:
        raise ConfigError(
            "[secrets] in coga.local.toml is no longer supported. Secrets are "
            "now declared inline on each ticket's `secrets:` frontmatter as "
            "`NAME: op://vault/item/field` or `NAME: env:VAR` entries (resolved "
            "at launch / `coga secret get`), so there is no central catalog. "
            "Move each key into the tickets that need it and delete the "
            "[secrets] table."
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
    extensions = _parse_extensions(shared.get("extensions", {}))
    ticket_fields = _parse_ticket_fields(shared.get("ticket"))
    git_enabled = _resolve_git_enabled(shared.get("git"), local.get("git"))
    git_remote, git_control_branch = _parse_git(shared.get("git"))
    (
        launch_idle_timeout,
        launch_idle_timeout_present,
        launch_max_session,
        launch_worktree,
        launch_worktree_path,
    ) = _parse_launch(shared.get("launch"))
    megalaunch = _parse_megalaunch(shared.get("megalaunch"))

    # The operator's `user` must be set explicitly in `coga.local.toml` — coga
    # never guesses it. A guessed name (git `user.name`, OS username) can
    # disagree with the `owner` tokens written into tickets, and for an
    # unattended sweep a wrong `me` fails silently. So a missing/empty `user` is
    # a hard error on every command. Existing repos recover by creating or
    # editing `coga.local.toml`; fresh repos pass `coga init --user <name>`,
    # which writes `user` before anything reads config.
    current_user = local.get("user")
    if not current_user:
        raise ConfigError(
            "No `user` set in coga.local.toml — coga needs your name and will "
            'not guess it. Add `user = "<name>"` to '
            f"{local_path} (for example, `user = \"marc\"`). "
            "For a fresh repo that has not been initialized yet, run "
            "`coga init --user <name>`."
        )

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
        aliases=aliases,
        extensions=extensions,
        ticket_fields=ticket_fields,
        git_enabled=git_enabled,
        git_remote=git_remote,
        git_control_branch=git_control_branch,
        launch_idle_timeout=launch_idle_timeout,
        launch_idle_timeout_present=launch_idle_timeout_present,
        launch_max_session=launch_max_session,
        launch_worktree=launch_worktree,
        launch_worktree_path=launch_worktree_path,
        megalaunch=megalaunch,
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
    `[extensions]`, `[notification.slack.gifs]`, `[notification.slack.users]` —
    do **not** call this: their keys are user-chosen data, not schema.
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
# maps (aliases, secrets, extensions, slack gifs/users) are deliberately absent;
# their keys are data. Deprecated / known-rejected keys run their dedicated
# migration errors before this generic check.
_ALLOWED_SHARED_SECTIONS: frozenset[str] = frozenset({
    "version",
    "default_status",
    "agents",
    "notification",
    "slack",
    "git",
    "launch",
    "megalaunch",
    "ticket",
    "aliases",
    "extensions",
})
_ALLOWED_LOCAL_SECTIONS: frozenset[str] = frozenset({
    "user",
    "agents",
    "notification",
    "slack",
    "git",
})
_ALLOWED_AGENT_KEYS: frozenset[str] = frozenset({
    "cli",
    "file",
    "mode",
    "name_flag",
    "session_id_flag",
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
# repo policy and `_parse_git` intentionally reads them only from coga.toml.
_ALLOWED_LOCAL_GIT_KEYS: frozenset[str] = frozenset({"enabled"})
_ALLOWED_LAUNCH_KEYS: frozenset[str] = frozenset(
    {"idle_timeout", "max_session", "worktree", "worktree_path"}
)
_ALLOWED_MEGALAUNCH_KEYS: frozenset[str] = frozenset({
    "min_session_remaining_percent",
    "min_weekly_remaining_percent",
    "weekly_final_window_hours",
    # Deprecated token-budget keys — parsed but unused (see MegalaunchConfig).
    "token_guard",
    "default_token_budget",
    "window_hours",
    "agent_token_budgets",
})
_ALLOWED_TICKET_KEYS: frozenset[str] = frozenset({"fields"})


def _reject_unknown_sections(shared: dict, local: dict) -> None:
    """Reject unknown keys in the top-level and cross-file fixed-schema tables.

    Covers what isn't validated inside a single dedicated parser: the top-level
    sections of both files, plus the `[notification]` / `[notification.slack]` /
    legacy `[slack]` / `[git]` tables, each of which may appear in *both*
    `coga.toml` and `coga.local.toml`. The per-table parsers
    (`_parse_agents`, `_parse_launch`, `_parse_ticket_fields`) reject their own
    nested keys, so they aren't repeated here.

    `_notification_slack_table` is reused to reach the nested `slack` sub-table;
    it raises the existing "must be a table" error for a non-dict, so the type
    contract is unchanged.
    """
    _reject_unknown_keys(shared, _ALLOWED_SHARED_SECTIONS, "coga.toml")
    _reject_unknown_keys(local, _ALLOWED_LOCAL_SECTIONS, "coga.local.toml")
    for source, table in (("coga.toml", shared), ("coga.local.toml", local)):
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
        shared.get("git"), _ALLOWED_SHARED_GIT_KEYS, "[git] in coga.toml"
    )
    _reject_unknown_keys(
        local.get("git"), _ALLOWED_LOCAL_GIT_KEYS, "[git] in coga.local.toml"
    )


def _parse_positive_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigError(f"{label} must be a positive integer")
    return value


def _parse_percent(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{label} must be a number between 0 and 100")
    if not 0 <= value <= 100:
        raise ConfigError(f"{label} must be a number between 0 and 100")
    return float(value)


def _parse_positive_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ConfigError(f"{label} must be a positive number")
    return float(value)


def _parse_megalaunch(raw: object) -> MegalaunchConfig:
    """Parse `[megalaunch]` budget guard settings."""
    if raw is None:
        return MegalaunchConfig()
    if not isinstance(raw, dict):
        raise ConfigError(f"[megalaunch] must be a table (got {type(raw).__name__})")
    _reject_unknown_keys(raw, _ALLOWED_MEGALAUNCH_KEYS, "[megalaunch]")
    budgets_raw = raw.get("agent_token_budgets", {})
    if not isinstance(budgets_raw, dict):
        raise ConfigError("[megalaunch].agent_token_budgets must be a table")
    budgets = {
        str(name): _parse_positive_int(value, f"[megalaunch.agent_token_budgets].{name}")
        for name, value in budgets_raw.items()
    }
    return MegalaunchConfig(
        min_session_remaining_percent=_parse_percent(
            raw.get(
                "min_session_remaining_percent",
                MegalaunchConfig.min_session_remaining_percent,
            ),
            "[megalaunch].min_session_remaining_percent",
        ),
        min_weekly_remaining_percent=_parse_percent(
            raw.get(
                "min_weekly_remaining_percent",
                MegalaunchConfig.min_weekly_remaining_percent,
            ),
            "[megalaunch].min_weekly_remaining_percent",
        ),
        weekly_final_window_hours=_parse_positive_number(
            raw.get(
                "weekly_final_window_hours",
                MegalaunchConfig.weekly_final_window_hours,
            ),
            "[megalaunch].weekly_final_window_hours",
        ),
        token_guard=_parse_positive_int(
            raw.get("token_guard", MegalaunchConfig.token_guard),
            "[megalaunch].token_guard",
        ),
        default_token_budget=_parse_positive_int(
            raw.get("default_token_budget", MegalaunchConfig.default_token_budget),
            "[megalaunch].default_token_budget",
        ),
        window_hours=_parse_positive_int(
            raw.get("window_hours", MegalaunchConfig.window_hours),
            "[megalaunch].window_hours",
        ),
        agent_token_budgets=budgets,
    )


def _parse_agents(raw: dict, local_raw: dict | None = None) -> dict[str, AgentType]:
    out: dict[str, AgentType] = {}
    for name, data in raw.items():
        for required in ("cli", "file"):
            if required not in data:
                raise ConfigError(f"agents.{name}.{required} is required")
        _reject_unknown_keys(data, _ALLOWED_AGENT_KEYS, f"[agents.{name}]")
        discussion = data.get("discussion", "")
        if not isinstance(discussion, str):
            raise ConfigError(
                f"agents.{name}.discussion must be a string "
                f"(got {type(discussion).__name__})"
            )
        session_id_flag = data.get("session_id_flag", "")
        if not isinstance(session_id_flag, str):
            raise ConfigError(
                f"agents.{name}.session_id_flag must be a string "
                f"(got {type(session_id_flag).__name__})"
            )
        out[name] = AgentType(
            name=name,
            cli=data["cli"],
            file=data["file"],
            mode=data.get("mode", "local"),
            name_flag=data.get("name_flag", ""),
            session_id_flag=session_id_flag,
            discussion=discussion,
        )
    if local_raw:
        raise ConfigError(
            "coga.local.toml no longer supports [agents.<name>] overrides; "
            "put shared agent config in coga.toml."
        )
    return out


_RESERVED_TICKET_FIELD_NAMES: frozenset[str] = frozenset({
    # Canonical ticket frontmatter keys — see `coga/architecture` and
    # `coga.validate.REQUIRED_TASK_KEYS` / `OPTIONAL_TASK_KEYS`. Extensions
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
                "See `coga/contexts/coga/architecture/SKILL.md` for the "
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
    """Parse [aliases] table — each entry is name → expanded coga command."""
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


def _parse_extensions(raw: object) -> dict[str, object]:
    """Parse the `[extensions]` table — a repo-owned, free-form namespace.

    coga does not interpret the contents; they pass through verbatim so a repo's
    own skills/scripts can read repo-specific config that isn't part of coga's
    fixed schema (e.g. `[extensions.patent] calendar_id = "..."`). Only the table
    type is enforced — keys and values are user data, exactly like `[aliases]`
    and `[secrets]`, so nested tables and arbitrary scalars are all allowed.
    """
    if not isinstance(raw, dict):
        raise ConfigError(f"[extensions] must be a table (got {type(raw).__name__})")
    return raw


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
        ("[notification] in coga.local.toml", local),
        ("[notification] in coga.toml", shared),
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
        _notification_slack_table(shared_notification, "[notification] in coga.toml")
        is not None
    ):
        return True
    if (
        _notification_slack_table(
            local_notification, "[notification] in coga.local.toml"
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
        shared_notification, "[notification] in coga.toml"
    )
    local_slack = _notification_slack_table(
        local_notification, "[notification] in coga.local.toml"
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
    """Parse Slack user mapping — maps a coga name (the token used in a
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
    false` in `coga.local.toml`) is for repos with no remote —
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
    (`_resolve_git_enabled`) so it can pick up a `coga.local.toml` override.
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


_DEFAULT_LAUNCH_WORKTREE_PATH = ".coga/worktrees"


def _parse_launch(
    shared: dict | None,
) -> tuple[float | None, bool, float | None, bool, str]:
    """Parse `[launch]` for the recurring sweep's liveness limits and worktree knobs.

    `idle_timeout` / `max_session` are seconds (int or float). A `<= 0` or
    non-finite value disarms that limit (returns None), matching the env-var
    override's "off" contract in `coga.recurring_runner`. `idle_timeout`
    returns a separate presence flag so an explicit disarm can beat the built-in
    recurring default; omitted keys are None/False. These are defaults for the
    *unattended* sweep only — attended `coga launch` never reads them.

    `worktree` is a plain on/off boolean (default true) gating per-launch
    `git worktree` isolation in `coga launch`; unlike the timeouts it applies to
    attended launches too. `worktree_path` (default `.coga/worktrees`) is where
    those worktrees live — a non-empty string, relative to the git toplevel or
    absolute.
    """
    if shared is None:
        return None, False, None, True, _DEFAULT_LAUNCH_WORKTREE_PATH
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

    worktree = shared.get("worktree", True)
    if not isinstance(worktree, bool):
        raise ConfigError(f"[launch].worktree must be a boolean (got {worktree!r})")

    worktree_path = shared.get("worktree_path", _DEFAULT_LAUNCH_WORKTREE_PATH)
    if not isinstance(worktree_path, str) or not worktree_path.strip():
        raise ConfigError(
            f"[launch].worktree_path must be a non-empty string (got {worktree_path!r})"
        )

    return (
        _seconds("idle_timeout"),
        "idle_timeout" in shared,
        _seconds("max_session"),
        worktree,
        worktree_path.strip(),
    )


def _resolve_secret_value(value: str) -> str:
    """Resolve an `env:VAR` reference to the env var's value; pass literals through.

    A missing env var resolves to the empty string here. This is only used for
    `[notification.slack].webhook`, where an unset var collapsing to "" (then
    `or None`) correctly means "no webhook configured". Ticket secrets do **not**
    use this — they go through `select_launch_secrets`, which fails loud on an
    unset env var at launch instead of injecting "". The notification layer also
    keeps a deprecated bare `SLACK_WEBHOOK_URL` fallback for legacy repos.
    """
    if value.startswith("env:"):
        return os.environ.get(value[len("env:") :], "")
    return value


def parse_inline_secrets(declared: object) -> list[tuple[str, str]]:
    """Validate a ticket's inline `secrets:` and return `[(name, ref), ...]`.

    Secrets are declared inline per-ticket — there is no `[secrets]` catalog.
    Each entry is a single-key map binding an env-var name to an indirection
    reference that is safe to commit to git: `op://vault/item/field` (resolved
    live with `op read`) or `env:VAR` (read from the operator's environment).

    Three frontmatter shapes, kept distinct:

    - `None` (absent / null) and `[]` → no secrets.
    - a list of `{NAME: "op://…"|"env:VAR"}` single-key maps → those secrets.

    Fails loud (`SecretError`) on a non-list, a non-single-key entry, a
    duplicate name, a non-string name/ref, a bare-string entry (the removed
    catalog-key form), or a **raw literal** value — a literal secret may not
    live in a git-committed ticket; use `env:VAR` and export it locally.
    Resolution is deferred: this never shells out to `op` or reads env values.
    """
    if declared is None:
        return []
    if not isinstance(declared, list):
        raise SecretError(
            "ticket `secrets:` must be null or a list of `NAME: <ref>` entries "
            f"(got {type(declared).__name__})"
        )
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for entry in declared:
        if isinstance(entry, str):
            raise SecretError(
                f"ticket secret {entry!r} is a bare string; the [secrets] "
                "catalog was removed. Declare it inline as "
                "`NAME: op://vault/item/field` or `NAME: env:VAR`."
            )
        if not isinstance(entry, dict) or len(entry) != 1:
            raise SecretError(
                "ticket `secrets:` entries must each be a single-key map "
                f"`NAME: <ref>` (got {entry!r})"
            )
        (name, ref), = entry.items()
        if not isinstance(name, str) or not name:
            raise SecretError(
                f"ticket secret name must be a non-empty string (got {name!r})"
            )
        if name in seen:
            raise SecretError(f"ticket declares secret {name!r} more than once")
        seen.add(name)
        if not isinstance(ref, str):
            raise SecretError(
                f"ticket secret {name!r} reference must be a string (got {ref!r})"
            )
        if not (ref.startswith("op://") or ref.startswith("env:")):
            raise SecretError(
                f"ticket secret {name!r} must reference `op://vault/item/field` "
                f"or `env:VAR` — a literal value cannot live in a git-committed "
                f"ticket (got {ref!r}). Use `env:VAR` and export the value "
                "locally."
            )
        out.append((name, ref))
    return out


def _resolve_op_reference(key: str, ref: str) -> str:
    """Resolve a 1Password `op://` reference by shelling out to `op read`.

    Passes the reference URI verbatim to `op read` — Coga does not parse
    vault/item/field. Strips only the single trailing newline `op` prints; the
    secret is otherwise returned untransformed. Raises `SecretError` (naming the
    Coga secret key and reference, never the value) when `op` is not installed
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
    """Resolve a ticket's inline `secrets:` into the `{name: value}` map to inject.

    `declared` is the ticket's raw `secrets:` frontmatter value (`None`/`[]` →
    no secrets; otherwise a list of `{NAME: ref}` maps — see
    `parse_inline_secrets`). Each reference is resolved at this point, live:
    `op://…` via `op read`, `env:VAR` from the operator's environment. Fails
    loud (`SecretError`, no agent spawned) when `op` is missing/non-zero or a
    referenced env var is unset. `cfg` is unused (kept for call-site stability
    now that resolution is catalog-free); messages never name the value.
    """
    env: dict[str, str] = {}
    for name, ref in parse_inline_secrets(declared):
        if ref.startswith("op://"):
            env[name] = _resolve_op_reference(name, ref)
        else:  # env:VAR — prefix guaranteed by parse_inline_secrets
            var = ref[len("env:") :]
            value = os.environ.get(var)
            if value is None:
                raise SecretError(
                    f"ticket secret {name!r} references env var {var!r} but it "
                    "is not set"
                )
            env[name] = value
    return env


def build_launch_env(
    cfg: Config,
    declared: object,
    *,
    base_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build a child process env with Coga secrets scoped and source vars scrubbed.

    The spawned agent/script receives only the ticket's scoped secret names (for
    example `STRIPE_KEY=<value>`), never the raw source env vars an `env:VAR`
    reference points at. Scrub each referenced source variable from the inherited
    environment first, then add back only the resolved, scoped aliases.
    """
    env = dict(os.environ if base_env is None else base_env)
    for _name, ref in parse_inline_secrets(declared):
        if ref.startswith("env:"):
            env.pop(ref[len("env:") :], None)
    env.update(select_launch_secrets(cfg, declared))
    return env
