from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent

import pytest

from relay.config import ConfigError, find_repo_root, load_config


def _write(path: Path, text: str) -> None:
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        default_status = "draft"

        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        mode = "local"

        """,
    )
    _write(
        tmp_path / "relay.local.toml",
        """
        user = "marc"

        [secrets]
        stripe_key = "env:STRIPE_SECRET_KEY"
        literal = "just-a-value"
        """,
    )
    return tmp_path


def test_load_basic(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/xxx")
    cfg = load_config(repo)
    assert cfg.current_user == "marc"
    assert cfg.default_status == "draft"
    assert cfg.agents["claude"].cli == "claude"
    assert cfg.slack_webhook.startswith("https://")
    assert cfg.slack_enabled is True
    assert cfg.secrets["stripe_key"] == "sk_test_abc"
    assert cfg.secrets["literal"] == "just-a-value"


def test_default_status_defaults_to_draft(tmp_path: Path) -> None:
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        """,
    )
    _write(tmp_path / "relay.local.toml", 'user = "marc"\n')
    cfg = load_config(tmp_path)
    assert cfg.default_status == "draft"


def test_resolve_agent_type(repo: Path) -> None:
    cfg = load_config(repo)
    agent = cfg.agent_type("claude")
    assert agent.name == "claude"


def test_agent_discussion_template(repo: Path) -> None:
    text = (repo / "relay.toml").read_text()
    (repo / "relay.toml").write_text(
        text + 'discussion = "--append-system-prompt {prompt}"\n'
    )
    cfg = load_config(repo)
    assert cfg.agent_type("claude").discussion == "--append-system-prompt {prompt}"


def test_agent_discussion_template_must_be_string(repo: Path) -> None:
    text = (repo / "relay.toml").read_text()
    (repo / "relay.toml").write_text(text + "discussion = 42\n")
    with pytest.raises(ConfigError, match="agents.claude.discussion must be a string"):
        load_config(repo)


def test_unknown_agent_type(repo: Path) -> None:
    cfg = load_config(repo)
    with pytest.raises(ConfigError, match="Agent type 'goat' is not defined"):
        cfg.agent_type("goat")


def test_default_agent_is_first_declared(repo: Path) -> None:
    cfg = load_config(repo)
    default = cfg.default_agent()
    assert default is not None
    assert default.name == "claude"


def test_legacy_assignees_table_rejected(tmp_path: Path) -> None:
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"

        [assignees.marc]
        agents = {"claude" = "claude"}
        """,
    )
    _write(tmp_path / "relay.local.toml", 'user = "marc"\n')
    with pytest.raises(ConfigError, match=r"\[assignees\] is no longer supported"):
        load_config(tmp_path)


def test_missing_user(tmp_path: Path) -> None:
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        """,
    )
    _write(tmp_path / "relay.local.toml", "")
    with pytest.raises(ConfigError, match="user` is missing"):
        load_config(tmp_path)


def test_find_repo_root(repo: Path) -> None:
    nested = repo / "a" / "b" / "c"
    nested.mkdir(parents=True)
    assert find_repo_root(nested) == repo


def test_find_repo_root_not_found(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="No relay.toml found"):
        find_repo_root(tmp_path)


def test_missing_env_secret_is_empty(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    cfg = load_config(repo)
    assert cfg.secrets["stripe_key"] == ""


def test_unsupported_version(tmp_path: Path) -> None:
    _write(tmp_path / "relay.toml", "version = 99\n")
    _write(tmp_path / "relay.local.toml", 'user = "marc"\n')
    with pytest.raises(ConfigError, match="Unsupported relay.toml version"):
        load_config(tmp_path)


def test_aliases_load_and_strip(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + '\n[aliases]\nchat = "  launch bootstrap/orient  "\n'
    )
    cfg = load_config(repo)
    assert cfg.aliases == {"chat": "launch bootstrap/orient"}


def test_aliases_default_empty(repo: Path) -> None:
    cfg = load_config(repo)
    assert cfg.aliases == {}


def test_aliases_reject_non_string(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text() + "\n[aliases]\nchat = 42\n"
    )
    with pytest.raises(ConfigError, match="aliases.chat must be a string"):
        load_config(repo)


def test_aliases_reject_empty_string(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text() + '\n[aliases]\nchat = "   "\n'
    )
    with pytest.raises(ConfigError, match="aliases.chat is empty"):
        load_config(repo)


# --- [ticket.fields.*] -------------------------------------------------------


def test_ticket_fields_load_minimal(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + '\n[ticket.fields.docket]\ndescription = "USPTO docket number"\n'
    )
    cfg = load_config(repo)
    assert "docket" in cfg.ticket_fields
    field = cfg.ticket_fields["docket"]
    assert field.description == "USPTO docket number"
    assert field.values is None
    assert field.default == ""
    assert field.required is False


def test_ticket_fields_preserve_declaration_order(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + (
            "\n[ticket.fields.docket]\ndescription = \"d\"\n"
            "\n[ticket.fields.application_number]\ndescription = \"a\"\n"
            "\n[ticket.fields.priority]\ndescription = \"p\"\n"
        )
    )
    cfg = load_config(repo)
    assert list(cfg.ticket_fields) == ["docket", "application_number", "priority"]


def test_ticket_fields_default_empty(repo: Path) -> None:
    cfg = load_config(repo)
    assert cfg.ticket_fields == {}


def test_ticket_fields_full_shape(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + (
            "\n[ticket.fields.priority]\n"
            'description = "triage tier"\n'
            'values = ["P0", "P1", "P2"]\n'
            'default = "P2"\n'
            "required = true\n"
        )
    )
    cfg = load_config(repo)
    field = cfg.ticket_fields["priority"]
    assert field.values == ("P0", "P1", "P2")
    assert field.default == "P2"
    assert field.required is True


def test_ticket_fields_reject_reserved_name(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + '\n[ticket.fields.status]\ndescription = "x"\n'
    )
    with pytest.raises(ConfigError, match="canonical ticket frontmatter key"):
        load_config(repo)


def test_ticket_fields_reject_unsupported_key(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + (
            "\n[ticket.fields.docket]\n"
            'description = "d"\n'
            'kind = "string"\n'
        )
    )
    with pytest.raises(ConfigError, match="unsupported keys"):
        load_config(repo)


def test_ticket_fields_require_description(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text() + "\n[ticket.fields.docket]\n"
    )
    with pytest.raises(ConfigError, match="description must be a non-empty string"):
        load_config(repo)


def test_ticket_fields_reject_empty_values_list(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + (
            "\n[ticket.fields.priority]\n"
            'description = "p"\n'
            "values = []\n"
        )
    )
    with pytest.raises(ConfigError, match="values must not be empty"):
        load_config(repo)


def test_ticket_fields_default_must_match_values(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + (
            "\n[ticket.fields.priority]\n"
            'description = "p"\n'
            'values = ["P0", "P1"]\n'
            'default = "P9"\n'
        )
    )
    with pytest.raises(ConfigError, match="not in declared values"):
        load_config(repo)


def test_ticket_fields_required_must_be_bool(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + (
            "\n[ticket.fields.docket]\n"
            'description = "d"\n'
            'required = "yes"\n'
        )
    )
    with pytest.raises(ConfigError, match="required must be a boolean"):
        load_config(repo)

