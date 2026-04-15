"""Tests for relay_os.config.

Covers both happy paths (parsing the spec example, resolving agents
and env secrets) and error paths (missing files, bad TOML, unset env
vars, cross-reference violations). No CLI surface is exercised here —
this module is a pure library.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from relay_os.config import (
    AgentConfig,
    AssigneeConfig,
    ConfigError,
    ProjectConfig,
    RelayConfig,
    find_repo_root,
)


# ------------------------------------------------------------------
# find_repo_root
# ------------------------------------------------------------------


def test_find_repo_root_at_root(temp_repo: Path) -> None:
    assert find_repo_root(temp_repo) == temp_repo.resolve()


def test_find_repo_root_walks_up(temp_repo: Path) -> None:
    deep = temp_repo / "a" / "b" / "c"
    deep.mkdir(parents=True)
    assert find_repo_root(deep) == temp_repo.resolve()


def test_find_repo_root_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="no relay.toml"):
        find_repo_root(tmp_path)


# ------------------------------------------------------------------
# RelayConfig.load — happy paths
# ------------------------------------------------------------------


def test_load_minimal(temp_repo: Path) -> None:
    cfg = RelayConfig.load(temp_repo)
    assert cfg.root == temp_repo.resolve()
    assert cfg.user is None
    assert cfg.projects == {}
    assert cfg.agents == {}
    assert cfg.assignees == {}
    assert cfg.secrets == {}
    assert cfg.slack_webhook is None


def test_load_spec_example(spec_repo: Path) -> None:
    cfg = RelayConfig.load(spec_repo)

    assert cfg.user == "marc"

    assert set(cfg.projects) == {"email-tool", "content", "ops"}
    email = cfg.projects["email-tool"]
    assert isinstance(email, ProjectConfig)
    assert email.type == "repo"
    assert email.remote == "git@github.com:company/email-tool.git"
    assert email.default_status == "ready"
    assert email.path == (spec_repo / "email-tool").resolve()
    assert cfg.projects["ops"].default_status == "design"

    assert set(cfg.agents) == {"claude", "codex"}
    claude = cfg.agents["claude"]
    assert isinstance(claude, AgentConfig)
    assert claude.cli == "claude"
    assert claude.interactive == "--append-system-prompt-file"
    assert claude.auto == "-p"
    assert claude.file == "CLAUDE.md"
    assert claude.mode == "local"

    assert set(cfg.assignees) == {"marc", "pierre"}
    marc = cfg.assignees["marc"]
    assert isinstance(marc, AssigneeConfig)
    assert marc.agents == {"claude1": "claude", "claude2": "claude"}
    assert marc.slack == "U04ABCDEF"


def test_load_without_local_toml(temp_repo: Path) -> None:
    """Missing relay.local.toml is valid — the repo just has no user,
    no paths, no secrets. This is the state a teammate sees after a
    fresh clone before they run `cp relay.local.toml.example`."""
    cfg = RelayConfig.load(temp_repo)
    assert cfg.user is None
    assert cfg.secrets == {}


def test_load_path_expands_user(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / "relay.toml").write_text(
        dedent("""\
            version = 1
            [projects.foo]
            type = "local"
        """)
    )
    (tmp_path / "relay.local.toml").write_text(
        dedent("""\
            [paths]
            foo = "~/foo-dir"
        """)
    )
    cfg = RelayConfig.load(tmp_path)
    assert cfg.projects["foo"].path == (tmp_path / "foo-dir").resolve()


def test_load_absolute_path_respected(tmp_path: Path) -> None:
    abs_elsewhere = tmp_path / "elsewhere"
    abs_elsewhere.mkdir()
    (tmp_path / "repo").mkdir()
    (tmp_path / "repo" / "relay.toml").write_text(
        dedent("""\
            version = 1
            [projects.foo]
            type = "local"
        """)
    )
    (tmp_path / "repo" / "relay.local.toml").write_text(
        dedent(f"""\
            [paths]
            foo = "{abs_elsewhere}"
        """)
    )
    cfg = RelayConfig.load(tmp_path / "repo")
    assert cfg.projects["foo"].path == abs_elsewhere.resolve()


# ------------------------------------------------------------------
# RelayConfig.load — error paths
# ------------------------------------------------------------------


def test_load_missing_relay_toml(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="no relay.toml"):
        RelayConfig.load(tmp_path)


def test_load_invalid_toml(tmp_path: Path) -> None:
    (tmp_path / "relay.toml").write_text("this is not = valid = toml =\n")
    with pytest.raises(ConfigError, match="invalid TOML"):
        RelayConfig.load(tmp_path)


def test_load_unsupported_version(tmp_path: Path) -> None:
    (tmp_path / "relay.toml").write_text("version = 99\n")
    with pytest.raises(ConfigError, match="unsupported version"):
        RelayConfig.load(tmp_path)


def test_load_repo_project_missing_remote(tmp_path: Path) -> None:
    (tmp_path / "relay.toml").write_text(
        dedent("""\
            version = 1
            [projects.broken]
            type = "repo"
        """)
    )
    with pytest.raises(ConfigError, match="requires a 'remote' field"):
        RelayConfig.load(tmp_path)


def test_load_project_bad_type(tmp_path: Path) -> None:
    (tmp_path / "relay.toml").write_text(
        dedent("""\
            version = 1
            [projects.broken]
            type = "remote"
        """)
    )
    with pytest.raises(ConfigError, match="must be 'repo' or 'local'"):
        RelayConfig.load(tmp_path)


def test_load_paths_reference_unknown_project(tmp_path: Path) -> None:
    (tmp_path / "relay.toml").write_text(
        dedent("""\
            version = 1
            [projects.known]
            type = "local"
        """)
    )
    (tmp_path / "relay.local.toml").write_text(
        dedent("""\
            [paths]
            unknown = "./somewhere"
        """)
    )
    with pytest.raises(ConfigError, match="not a project in relay.toml"):
        RelayConfig.load(tmp_path)


def test_load_assignee_references_unknown_agent_type(tmp_path: Path) -> None:
    (tmp_path / "relay.toml").write_text(
        dedent("""\
            version = 1
            [agents.claude]
            cli = "claude"
            interactive = "-i"
            auto = "-p"
            file = "CLAUDE.md"

            [assignees.marc]
            agents = { "mystery" = "gpt-5" }
        """)
    )
    with pytest.raises(ConfigError, match="unknown type 'gpt-5'"):
        RelayConfig.load(tmp_path)


def test_load_agent_missing_required_fields(tmp_path: Path) -> None:
    (tmp_path / "relay.toml").write_text(
        dedent("""\
            version = 1
            [agents.claude]
            cli = "claude"
        """)
    )
    with pytest.raises(ConfigError, match="missing required fields"):
        RelayConfig.load(tmp_path)


# ------------------------------------------------------------------
# Secrets — env var resolution
# ------------------------------------------------------------------


def test_secrets_env_reference_resolved(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MY_TOKEN", "super-secret")
    (tmp_path / "relay.toml").write_text("version = 1\n")
    (tmp_path / "relay.local.toml").write_text(
        dedent("""\
            [secrets]
            token = "env:MY_TOKEN"
        """)
    )
    cfg = RelayConfig.load(tmp_path)
    assert cfg.secrets == {"token": "super-secret"}


def test_secrets_plain_string_passthrough(tmp_path: Path) -> None:
    (tmp_path / "relay.toml").write_text("version = 1\n")
    (tmp_path / "relay.local.toml").write_text(
        dedent("""\
            [secrets]
            plain = "just-a-value"
        """)
    )
    cfg = RelayConfig.load(tmp_path)
    assert cfg.secrets == {"plain": "just-a-value"}


def test_secrets_env_var_missing_raises(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("PROBABLY_NOT_SET_12345", raising=False)
    (tmp_path / "relay.toml").write_text("version = 1\n")
    (tmp_path / "relay.local.toml").write_text(
        dedent("""\
            [secrets]
            missing = "env:PROBABLY_NOT_SET_12345"
        """)
    )
    with pytest.raises(ConfigError, match="PROBABLY_NOT_SET_12345"):
        RelayConfig.load(tmp_path)


def test_secrets_env_reference_no_var_name(tmp_path: Path) -> None:
    (tmp_path / "relay.toml").write_text("version = 1\n")
    (tmp_path / "relay.local.toml").write_text(
        dedent("""\
            [secrets]
            broken = "env:"
        """)
    )
    with pytest.raises(ConfigError, match="missing a variable name"):
        RelayConfig.load(tmp_path)


# ------------------------------------------------------------------
# Slack webhook resolution
# ------------------------------------------------------------------


def test_slack_webhook_from_secret(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SLACK_HOOK", "https://example.com/hook")
    (tmp_path / "relay.toml").write_text("version = 1\n")
    (tmp_path / "relay.local.toml").write_text(
        dedent("""\
            [secrets]
            slack_webhook = "env:SLACK_HOOK"
        """)
    )
    cfg = RelayConfig.load(tmp_path)
    assert cfg.slack_webhook == "https://example.com/hook"


def test_slack_webhook_from_shared_fallback(tmp_path: Path) -> None:
    (tmp_path / "relay.toml").write_text(
        dedent("""\
            version = 1
            [slack]
            webhook = "https://fallback.example/hook"
        """)
    )
    cfg = RelayConfig.load(tmp_path)
    assert cfg.slack_webhook == "https://fallback.example/hook"


def test_slack_webhook_secret_wins_over_shared(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("HOOK", "https://from-secret.example")
    (tmp_path / "relay.toml").write_text(
        dedent("""\
            version = 1
            [slack]
            webhook = "https://from-shared.example"
        """)
    )
    (tmp_path / "relay.local.toml").write_text(
        dedent("""\
            [secrets]
            slack_webhook = "env:HOOK"
        """)
    )
    cfg = RelayConfig.load(tmp_path)
    assert cfg.slack_webhook == "https://from-secret.example"


def test_slack_webhook_absent(temp_repo: Path) -> None:
    cfg = RelayConfig.load(temp_repo)
    assert cfg.slack_webhook is None


# ------------------------------------------------------------------
# Accessors: project() and agent()
# ------------------------------------------------------------------


def test_project_accessor(spec_repo: Path) -> None:
    cfg = RelayConfig.load(spec_repo)
    email = cfg.project("email-tool")
    assert email.name == "email-tool"
    assert email.type == "repo"


def test_project_accessor_unknown(spec_repo: Path) -> None:
    cfg = RelayConfig.load(spec_repo)
    with pytest.raises(ConfigError, match="unknown project"):
        cfg.project("nonexistent")


def test_agent_accessor_uses_current_user(spec_repo: Path) -> None:
    cfg = RelayConfig.load(spec_repo)
    # marc's claude1 -> agent type "claude"
    resolved = cfg.agent("claude1")
    assert resolved.name == "claude"
    assert resolved.cli == "claude"
    assert resolved.interactive == "--append-system-prompt-file"


def test_agent_accessor_with_explicit_user(spec_repo: Path) -> None:
    cfg = RelayConfig.load(spec_repo)
    # pierre's claude2 -> agent type "claude" (same type, different user)
    resolved = cfg.agent("claude2", user="pierre")
    assert resolved.name == "claude"


def test_agent_accessor_no_user_raises(temp_repo: Path) -> None:
    # No local.toml so user is None; calling agent() without explicit user fails.
    cfg = RelayConfig.load(temp_repo)
    with pytest.raises(ConfigError, match="no user set"):
        cfg.agent("claude1")


def test_agent_accessor_unknown_user_raises(spec_repo: Path) -> None:
    cfg = RelayConfig.load(spec_repo)
    with pytest.raises(ConfigError, match="not configured in relay.toml"):
        cfg.agent("claude1", user="stranger")


def test_agent_accessor_unknown_nickname_raises(spec_repo: Path) -> None:
    cfg = RelayConfig.load(spec_repo)
    with pytest.raises(ConfigError, match="no agent nicknamed"):
        cfg.agent("does-not-exist")


def test_agent_accessor_nickname_not_for_this_user(spec_repo: Path) -> None:
    # marc has claude1 and claude2. pierre has only claude2. If we ask
    # for pierre's claude1, it should fail — the dispatch key is
    # (user, nickname), not just nickname.
    cfg = RelayConfig.load(spec_repo)
    with pytest.raises(ConfigError, match="no agent nicknamed 'claude1'"):
        cfg.agent("claude1", user="pierre")


# ------------------------------------------------------------------
# Dataclass frozen-ness
# ------------------------------------------------------------------


def test_project_config_is_frozen(spec_repo: Path) -> None:
    cfg = RelayConfig.load(spec_repo)
    email = cfg.project("email-tool")
    with pytest.raises(Exception):
        email.type = "local"  # type: ignore[misc]
