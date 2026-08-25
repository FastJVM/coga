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
    non-zero exit before any agent or recipe process is spawned — the fail-loud
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
    # Optional argv override for the recurring sweep's post-run analysis call
    # (`coga/recurring_autofix.py`). Not a launch: this is a one-shot,
    # text-in/text-out call with no PTY, no REPL, and no lifecycle — the
    # analyst reads a run record and answers, and Coga does every mutation.
    # Parsed via `shlex.split`; the literal token `{prompt}` is replaced with
    # the analysis prompt. Empty string uses the built-in defaults for known
    # `claude` / `codex` CLIs; an unknown CLI with no override skips the
    # analysis loudly rather than guessing an argv.
    analyze: str = ""


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
class Config:
    repo_root: Path
    current_user: str
    default_status: str
    agents: dict[str, AgentType]
    # Slack remains as the first notification backend. These fields hold the
    # effective Slack-channel config resolved from `[notification.slack]`.
    slack_webhook: str | None
    slack_enabled: bool
    # Second webhook, pointing at the coga-important channel. Explicit and
    # automatic alerts that need a human to act post here; ordinary lifecycle
    # traffic stays on `slack_webhook`. None when unconfigured —
    # `SlackChannel.send` then crashes an important post rather than rerouting
    # it to `slack_webhook`.
    slack_important_webhook: str | None = None
    notification_channels: tuple[str, ...] = ("slack",)
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
    # The repo's recurring owner: the one operator whose checkout may launch
    # recurring sweeps. Committed in `coga.toml` — unlike machine-local
    # `current_user` — so every clone agrees on who runs them, which is what
    # keeps two operators from sweeping the same repo concurrently. Empty means
    # unset, and recurring stays ungated. See
    # `coga.recurring_runner.recurring_owner_refusal`.
    owner: str = ""
    # Resolved absolute path of the repo's contexts directory when
    # `[layout] contexts` relocates it out of `coga/contexts/`. None means the
    # key is unset and the default location applies — read `contexts_root`, not
    # this field. See `_parse_layout` for the anchoring and containment rules.
    contexts_dir: Path | None = None

    # --- convenience accessors -------------------------------------------------

    @property
    def contexts_root(self) -> Path:
        """Directory holding this repo's contexts, `coga/contexts/` by default.

        The single place the local contexts directory is named. `paths.py`
        builds every context path off this, so a repo that relocates its
        contexts with `[layout] contexts` moves them for composition,
        validation, ref resolution, git state sync, and authoring sync alike.
        """
        if self.contexts_dir is not None:
            return self.contexts_dir
        return self.repo_root / "contexts"

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


def find_checkout_root(repo_root: Path) -> Path | None:
    """The git checkout containing the coga root, or None if there is none.

    The anchor for `[layout]` paths. `repo_root` cannot serve as that anchor:
    in the nested layout it is `<checkout>/coga/`, but in the root layout it
    *is* the checkout root, so the same relative path would mean two different
    places. The checkout root is the one directory that sits above the coga
    root in both, which is what makes `contexts = "docs/contexts"` mean
    `<checkout>/docs/contexts` either way.

    Detected by walking up for a `.git` entry: a directory holding a `HEAD` in
    an ordinary clone, or a plain file in a linked worktree or submodule — so
    coga's own feature worktrees anchor at their own checkout rather than at
    the primary one. The `HEAD` probe matters because a bare `.git` *directory*
    with nothing in it is not a repository to git either, and treating one as
    the anchor would silently resolve `[layout]` paths against a directory that
    has no checkout at all.
    """
    for candidate in [repo_root.resolve(), *repo_root.resolve().parents]:
        marker = candidate / ".git"
        if marker.is_file() or (marker / "HEAD").is_file():
            return candidate
    return None


# --- loader --------------------------------------------------------------------


def load_config(repo_root: Path | None = None, *, require_user: bool = True) -> Config:
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
    # `megalaunch` also gets a dedicated migration message ahead of the
    # generic check: the usage-window budget guard was removed, so the whole
    # table is dead config.
    if "megalaunch" in shared:
        raise ConfigError(
            "[megalaunch] is no longer supported in coga.toml. The megalaunch "
            "budget guard was removed — the sweep no longer reads agent usage "
            "windows or token budgets. Delete the [megalaunch] table."
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
    for source, table in (("coga.toml", shared), ("coga.local.toml", local)):
        if "slack" in table:
            raise ConfigError(
                f"[slack] in {source} is no longer supported. Move its keys "
                "under [notification.slack] (including [notification.slack.gifs] "
                "and [notification.slack.users]) and delete the [slack] table."
            )
    _reject_unknown_sections(shared, local)

    default_status = shared.get("default_status", "draft")
    owner = parse_owner(shared.get("owner"))
    agents = _parse_agents(shared.get("agents", {}), local.get("agents", {}))
    notification_channels = _resolve_notification_channels(
        shared.get("notification"),
        local.get("notification"),
    )
    (
        slack_webhook,
        slack_important_webhook,
        slack_enabled,
        slack_gifs,
        slack_users,
    ) = _parse_slack_notification(
        shared.get("notification"),
        local.get("notification"),
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
    ) = _parse_launch(shared.get("launch"))
    contexts_dir = _parse_layout(shared.get("layout"), root)

    # The operator's `user` must be set explicitly in `coga.local.toml` — coga
    # never guesses it. A guessed name (git `user.name`, OS username) can
    # disagree with the `owner` tokens written into tickets, and for an
    # unattended sweep a wrong `me` fails silently. So a missing/empty `user`
    # is a hard error on every command that acts *as* someone. Read-only
    # surfaces that never read `current_user` (the eager load behind `--help`;
    # `status`, `show`, `validate`, and `usage`; plus the `skill status`,
    # `recurring list`, and `secret get` group views) pass `require_user=False`
    # and get `current_user = ""` instead, so
    # a teammate on a fresh clone — where the gitignored `coga.local.toml`
    # does not exist yet — can look around before setting a name. Existing
    # repos recover by creating or editing `coga.local.toml`; fresh repos pass
    # `coga init --user <name>`, which writes `user` before anything reads
    # config.
    current_user = local.get("user")
    if not current_user:
        if require_user:
            raise ConfigError(
                "No `user` set in coga.local.toml — coga needs your name and "
                'will not guess it. Add `user = "<name>"` to '
                f"{local_path} (for example, `user = \"marc\"`); the file is "
                "gitignored, so every teammate's clone sets its own. "
                "For a fresh repo that has not been initialized yet, run "
                "`coga init --user <name>`."
            )
        current_user = ""

    return Config(
        repo_root=root,
        current_user=current_user,
        default_status=default_status,
        agents=agents,
        slack_webhook=slack_webhook,
        slack_important_webhook=slack_important_webhook,
        slack_enabled=slack_enabled,
        notification_channels=notification_channels,
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
        owner=owner,
        contexts_dir=contexts_dir,
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
    "owner",
    "agents",
    "notification",
    "git",
    "launch",
    "ticket",
    "aliases",
    "extensions",
    "layout",
})
_ALLOWED_LOCAL_SECTIONS: frozenset[str] = frozenset({
    "user",
    "agents",
    "notification",
    "git",
})
_ALLOWED_AGENT_KEYS: frozenset[str] = frozenset({
    "cli",
    "file",
    "mode",
    "name_flag",
    "session_id_flag",
    "discussion",
    "analyze",
})
_ALLOWED_NOTIFICATION_KEYS: frozenset[str] = frozenset({"channels", "slack"})
_ALLOWED_SLACK_KEYS: frozenset[str] = frozenset({
    "webhook",
    "important_webhook",
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
    {"idle_timeout", "max_session"}
)
_ALLOWED_TICKET_KEYS: frozenset[str] = frozenset({"fields"})
# `[layout]` is shared repo policy — where this repo keeps hand-edited prose —
# so it is deliberately absent from `_ALLOWED_LOCAL_SECTIONS`: one clone must
# not resolve a context ref somewhere another clone doesn't.
_ALLOWED_LAYOUT_KEYS: frozenset[str] = frozenset({"contexts"})


def _reject_unknown_sections(shared: dict, local: dict) -> None:
    """Reject unknown keys in the top-level and cross-file fixed-schema tables.

    Covers what isn't validated inside a single dedicated parser: the top-level
    sections of both files, plus the `[notification]` / `[notification.slack]` /
    `[git]` tables, each of which may appear in *both* `coga.toml` and
    `coga.local.toml`. The per-table parsers
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
    _reject_unknown_keys(
        shared.get("git"), _ALLOWED_SHARED_GIT_KEYS, "[git] in coga.toml"
    )
    _reject_unknown_keys(
        local.get("git"), _ALLOWED_LOCAL_GIT_KEYS, "[git] in coga.local.toml"
    )
    _reject_unknown_keys(
        shared.get("layout"), _ALLOWED_LAYOUT_KEYS, "[layout] in coga.toml"
    )


_REMOVED_AGENT_KEYS: tuple[str, ...] = (
    # Removed with the autonomy rework (#503): launches are interactive-only,
    # so the headless `auto` argv and the machine-local permission-skip policy
    # no longer exist. The 0.2.0 `coga init` scaffold wrote `auto` into every
    # repo's coga.toml, so these must raise a tailored migration error before
    # the generic unknown-key check — otherwise upgrading the CLI bricks every
    # existing repo with a bare "unknown key(s) ['auto']" on all commands.
    "auto",
    "skip_permissions",
    "skip_permissions_argv",
)


def _parse_agents(raw: dict, local_raw: dict | None = None) -> dict[str, AgentType]:
    out: dict[str, AgentType] = {}
    for name, data in raw.items():
        for required in ("cli", "file"):
            if required not in data:
                raise ConfigError(f"agents.{name}.{required} is required")
        removed = [key for key in _REMOVED_AGENT_KEYS if key in data]
        if removed:
            raise ConfigError(
                f"[agents.{name}] has removed key(s) {removed}. Launches are "
                "interactive-only now: the headless `auto` argv and the "
                "`skip_permissions` / `skip_permissions_argv` policy are gone "
                "with no replacement. Delete those line(s) from coga.toml — "
                "a repo initialized by coga 0.2.0 carries `auto` in its "
                "scaffolded config."
            )
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
        analyze = data.get("analyze", "")
        if not isinstance(analyze, str):
            raise ConfigError(
                f"agents.{name}.analyze must be a string "
                f"(got {type(analyze).__name__})"
            )
        out[name] = AgentType(
            name=name,
            cli=data["cli"],
            file=data["file"],
            mode=data.get("mode", "local"),
            name_flag=data.get("name_flag", ""),
            session_id_flag=session_id_flag,
            discussion=discussion,
            analyze=analyze,
        )
    for name, data in (local_raw or {}).items():
        if not isinstance(data, Mapping):
            continue
        removed = [key for key in _REMOVED_AGENT_KEYS if key in data]
        if removed:
            raise ConfigError(
                f"[agents.{name}] in coga.local.toml has removed key(s) "
                f"{removed}. Launches are interactive-only now: the headless "
                "`auto` argv and the `skip_permissions` / "
                "`skip_permissions_argv` policy are gone with no replacement. "
                "Delete those line(s) from coga.local.toml."
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
                "See the `coga/architecture` context for the reserved set."
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


def parse_owner(raw: object) -> str:
    """Parse the shared `owner` key — the repo's recurring owner.

    Committed in `coga.toml` (never `coga.local.toml`, where it would say
    nothing to the other clones the gate exists to hold off). Absent or empty
    means unset, and recurring stays ungated; a non-string fails loud like
    every other fixed-schema value.
    """
    if raw is None:
        return ""
    if not isinstance(raw, str):
        raise ConfigError(f"`owner` must be a string (got {type(raw).__name__})")
    return raw.strip()


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
) -> tuple[str, ...]:
    """Resolve `[notification].channels` with local overriding shared.

    An explicit `channels` list — including an empty one — is authoritative. A
    fresh repo that names no `channels` key anywhere gets no notification
    channels: Slack is opt-in, not the first-run default. Slack is *inferred*
    only when the absent key is paired with a `[notification.slack]` table.
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
    if _slack_opt_in_present(shared, local):
        return ("slack",)
    return ()


def _slack_opt_in_present(
    shared_notification: dict | None,
    local_notification: dict | None,
) -> bool:
    """True when a repo has opted into Slack via TOML config.

    Drives channel inference when `[notification].channels` is absent: a
    `[notification.slack]` table in either config counts as opt-in evidence.
    With neither, a fresh repo selects no channels.
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
) -> tuple[
    str | None,
    str | None,
    bool,
    dict[str, list[str]],
    dict[str, str],
]:
    """Parse the effective `[notification.slack]` channel config."""
    shared_slack = _notification_slack_table(
        shared_notification, "[notification] in coga.toml"
    )
    local_slack = _notification_slack_table(
        local_notification, "[notification] in coga.local.toml"
    )
    webhook = _resolve_notification_slack_webhook(
        shared_slack,
        local_slack,
    )
    important_webhook = _resolve_notification_slack_important_webhook(
        shared_slack,
        local_slack,
    )
    enabled = _resolve_notification_slack_enabled(
        shared_slack,
        local_slack,
    )
    gifs = _parse_notification_slack_gifs(
        shared_slack,
        local_slack,
    )
    users = _parse_notification_slack_users(
        shared_slack,
        local_slack,
    )
    return (
        webhook,
        important_webhook,
        enabled,
        gifs,
        users,
    )


def _resolve_notification_slack_webhook(
    shared: dict | None,
    local: dict | None,
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
    value = os.environ.get("SLACK_WEBHOOK_URL")
    if value:
        raise ConfigError(
            "Bare `SLACK_WEBHOOK_URL` is no longer supported. Declare "
            '`[notification.slack].webhook = "env:SLACK_WEBHOOK_URL"` in '
            "coga.toml or coga.local.toml, or unset the environment variable."
        )
    return None


def _resolve_notification_slack_important_webhook(
    shared: dict | None,
    local: dict | None,
) -> str | None:
    """Resolve the coga-important webhook, with local overriding shared.

    Absent — or an `env:` reference whose var isn't exported — resolves to
    None, and `SlackChannel.send` crashes an `--important` post rather than
    rerouting it to the primary webhook.
    """
    for table in (local, shared):
        if isinstance(table, dict) and "important_webhook" in table:
            value = table["important_webhook"]
            if not isinstance(value, str):
                raise ConfigError(
                    "[notification.slack].important_webhook must be a string "
                    f"(got {type(value).__name__})"
                )
            return _resolve_secret_value(value) or None
    return None


def _resolve_notification_slack_enabled(
    shared: dict | None,
    local: dict | None,
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
    return True


def _parse_notification_slack_gifs(
    shared: dict | None,
    local: dict | None,
) -> dict[str, list[str]]:
    for table in (local, shared):
        if isinstance(table, dict) and "gifs" in table:
            return _parse_slack_gifs(table)
    return {}


def _parse_notification_slack_users(
    shared: dict | None,
    local: dict | None,
) -> dict[str, str]:
    for table in (local, shared):
        if isinstance(table, dict) and "users" in table:
            return _parse_slack_users(table)
    return {}


def _parse_slack_gifs(
    shared: dict | None, table_name: str = "[notification.slack.gifs]"
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
    shared: dict | None, table_name: str = "[notification.slack.users]"
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


def _parse_layout(raw: object, repo_root: Path) -> Path | None:
    """Resolve `[layout] contexts` to an absolute directory, or None if unset.

    Every check here is fail-loud on purpose. `resolve_context_path` falls back
    to the packaged `bootstrap/contexts/` batteries when a ref misses locally,
    which is right for a single missing ref and catastrophic for a mistyped
    *directory*: every repo-local context would silently vanish from composed
    prompts while `coga/architecture` still resolved to the bundled copy. So a
    misconfigured directory has to fail at load, before anything composes.

    The value is a relative path anchored at the git checkout root (see
    `find_checkout_root`), and must resolve to a reproducible child directory
    inside that checkout. Absolute/outside/checkout-root paths, symlinked path
    components, Git pathspec metacharacters, and empty or ignored context trees
    are rejected — coga's state is git-backed, so the directory must be safely
    selectable and survive a clone.

    An unset key skips all of it, so a repo that never touches `[layout]`
    behaves exactly as it did before the key existed.
    """
    resolved = resolve_layout_contexts_path(raw, repo_root)
    if resolved is None:
        return None
    if not resolved.exists():
        raise ConfigError(
            f"[layout].contexts points at {resolved}, which does not exist. "
            "Create the directory (and move the existing contexts into it), or "
            "remove the key to use the default `contexts/` directory beside "
            "coga.toml."
        )
    if not resolved.is_dir():
        raise ConfigError(
            f"[layout].contexts points at {resolved}, which is not a directory."
        )
    checkout = find_checkout_root(repo_root)
    assert checkout is not None
    _require_trackable_context_entry(checkout, resolved)
    return resolved


def resolve_layout_contexts_path(raw: object, repo_root: Path) -> Path | None:
    """Resolve `[layout] contexts` without requiring its target to exist.

    Config loading adds the filesystem and Git-trackability checks in
    `_parse_layout`. Fresh scaffolding uses this location-only half before it
    copies anything, so `coga init` can materialize its context templates at
    the configured destination without first creating a knowingly-invalid
    default tree.
    """
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ConfigError("[layout] in coga.toml must be a table")
    value = raw.get("contexts")
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(
            "[layout].contexts must be a non-empty string, for example "
            '`contexts = "docs/contexts"`.'
        )
    candidate = Path(value)
    if candidate.is_absolute():
        raise ConfigError(
            f"[layout].contexts must be a relative path, got {value!r}. It is "
            "resolved against the git checkout root, so write it as "
            "`docs/contexts`, not as an absolute path."
        )
    candidate_text = candidate.as_posix()
    if candidate_text.startswith(":") or any(
        char in candidate_text for char in ("*", "?", "[")
    ):
        raise ConfigError(
            f"[layout].contexts must not contain Git pathspec metacharacters, "
            f"got {value!r}. Choose a literal directory name without a leading "
            "':' or any of '*', '?', '['; otherwise the automatic state sweep "
            "could select files outside the contexts directory."
        )

    checkout = find_checkout_root(repo_root)
    if checkout is None:
        raise ConfigError(
            f"[layout].contexts is set to {value!r}, but {repo_root} is not "
            "inside a git checkout. `[layout]` paths are resolved against the "
            "checkout root — the only anchor that means the same thing in the "
            "nested (`<checkout>/coga/`) and root (`<checkout>/`) layouts. "
            "Run `git init` at the checkout root, or remove the key to use the "
            "default `contexts/` directory beside coga.toml."
        )

    resolved = (checkout / candidate).resolve()
    if resolved == checkout:
        raise ConfigError(
            f"[layout].contexts ({value!r}) resolves to the git checkout root "
            f"at {checkout}. Choose a directory inside the checkout; using the "
            "checkout itself would make Coga's scoped state sweep select every "
            "dirty product file."
        )
    lexical = checkout
    for part in candidate.parts:
        if part in ("", "."):
            continue
        lexical = lexical.parent if part == ".." else lexical / part
        if lexical.is_symlink():
            raise ConfigError(
                f"[layout].contexts ({value!r}) traverses the symlink at "
                f"{lexical}. Choose a real directory path inside the checkout; "
                "otherwise Git can preserve the target files without preserving "
                "the configured path that fresh clones need."
            )
    resolved_repo_root = repo_root.resolve()
    if resolved == resolved_repo_root or resolved in resolved_repo_root.parents:
        raise ConfigError(
            f"[layout].contexts ({value!r}) resolves to {resolved}, which "
            f"contains the coga root at {resolved_repo_root}. Choose a dedicated "
            "directory that does not contain coga itself; otherwise the contexts "
            "pathspec would sweep sibling product files as Coga state."
        )
    if checkout not in resolved.parents:
        raise ConfigError(
            f"[layout].contexts ({value!r}) resolves to {resolved}, which is "
            f"outside the git checkout at {checkout}. Contexts are git-backed "
            "state; a directory outside the checkout could not be committed or "
            "synced."
        )
    git_admin = checkout / ".git"
    if resolved == git_admin or git_admin in resolved.parents:
        raise ConfigError(
            f"[layout].contexts ({value!r}) resolves inside Git's administrative "
            f"directory at {git_admin}. Choose a working-tree directory instead."
        )
    for ancestor in (resolved, *resolved.parents):
        if ancestor == checkout:
            break
        if (ancestor / ".git").exists():
            raise ConfigError(
                f"[layout].contexts ({value!r}) resolves inside the nested git "
                f"checkout at {ancestor}. Contexts must belong to the same "
                f"checkout as {repo_root} so Coga can sync them atomically."
            )
    return resolved


def _require_trackable_context_entry(checkout: Path, contexts_root: Path) -> None:
    """Require a reproducible configured root and context artifacts.

    Git does not record directories. Accept tracked files and untracked,
    non-ignored files because the next Coga state sweep will add the latter;
    reject an empty or fully ignored tree before its shared config can land by
    itself and break every fresh clone at config load. Also reject an ignore
    rule covering the root or any real context ``SKILL.md``: composition would
    otherwise read state the sweep can never carry to another clone. The
    shipped ``_template`` is intentionally ignored scaffolding rather than a
    resolvable context, so it is exempt.
    """
    rel = contexts_root.relative_to(checkout).as_posix()
    try:
        ignored_root = subprocess.run(
            [
                "git",
                "-C",
                str(checkout),
                "check-ignore",
                "--quiet",
                "--no-index",
                "--",
                f"{rel}/",
            ],
            capture_output=True,
            check=False,
        )
        result = subprocess.run(
            [
                "git",
                "-C",
                str(checkout),
                "--literal-pathspecs",
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
                "--",
                rel,
            ],
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ConfigError(
            "[layout].contexts requires Git to verify that the configured "
            "directory can survive a clone, but `git` is not on PATH."
        ) from exc
    if ignored_root.returncode == 0:
        raise ConfigError(
            f"[layout].contexts points at {contexts_root}, but that directory "
            "is ignored by Git. Existing tracked files can mask this rule while "
            "new contexts are silently omitted from the state sweep. Remove the "
            "matching ignore rule, then retry."
        )
    if ignored_root.returncode != 1:
        detail = ignored_root.stderr.decode(errors="replace").strip()
        raise ConfigError(
            "[layout].contexts could not verify the configured directory with "
            f"`git check-ignore`: {detail or f'exit {ignored_root.returncode}'}."
        )
    if result.returncode != 0:
        detail = result.stderr.decode(errors="replace").strip()
        raise ConfigError(
            "[layout].contexts could not verify the configured directory with "
            f"`git ls-files`: {detail or f'exit {result.returncode}'}."
        )
    entries = {
        (checkout / os.fsdecode(path)).absolute()
        for path in result.stdout.split(b"\0")
        if path
    }
    trackable = {
        path for path in entries if path.is_file() or path.is_symlink()
    }
    if not trackable:
        raise ConfigError(
            f"[layout].contexts points at {contexts_root}, but that directory "
            "contains no tracked or unignored file, so Git cannot reproduce it "
            "in a fresh clone. Add a context file or a trackable marker such as "
            "`.gitkeep`, then retry."
        )

    for artifact in contexts_root.rglob("SKILL.md"):
        relative = artifact.relative_to(contexts_root)
        if "_template" in relative.parts:
            continue
        if artifact.absolute() not in trackable:
            raise ConfigError(
                f"[layout].contexts contains {relative}, but that context file "
                "is neither tracked nor unignored in the host checkout. Coga "
                "would compose it locally while the state sweep silently "
                "omitted it. Remove the matching ignore rule or force-add the "
                "context file, then retry."
            )


def _parse_launch(
    shared: dict | None,
) -> tuple[float | None, bool, float | None]:
    """Parse `[launch]` for the recurring sweep's liveness limits.

    `idle_timeout` / `max_session` are seconds (int or float). A `<= 0` or
    non-finite value disarms that limit (returns None), matching the env-var
    override's "off" contract in `coga.recurring_runner`. `idle_timeout`
    returns a separate presence flag so an explicit disarm can beat the built-in
    recurring default; omitted keys are None/False. These are defaults for the
    *unattended* sweep only — attended `coga launch` never reads them.
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

    return (
        _seconds("idle_timeout"),
        "idle_timeout" in shared,
        _seconds("max_session"),
    )


def _resolve_secret_value(value: str) -> str:
    """Resolve an `env:VAR` reference to the env var's value; pass literals through.

    A missing env var resolves to the empty string here. This is only used for
    `[notification.slack].webhook`, where an unset var collapsing to "" (then
    `or None`) correctly means "no webhook configured". Ticket secrets do **not**
    use this — they go through `select_launch_secrets`, which fails loud on an
    unset env var at launch instead of injecting "".
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
        if name.startswith("COGA_"):
            raise SecretError(
                f"ticket secret name {name!r} uses the reserved `COGA_` "
                "namespace for Coga launch metadata and control variables"
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

    The spawned agent or recipe receives only the ticket's scoped secret names (for
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
