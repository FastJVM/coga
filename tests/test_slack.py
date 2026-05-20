from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
import requests
import typer

from relay.config import load_config
from relay.slack import post


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _scaffold_min(tmp_path: Path) -> None:
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        """,
    )
    _write(tmp_path / "relay.local.toml", 'user = "marc"\n')


@pytest.fixture
def cfg_with_webhook(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _scaffold_min(tmp_path)
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test")
    return load_config(tmp_path)


def test_post_calls_webhook(cfg_with_webhook, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    def fake_post(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        calls.append({"url": url, "json": json})

        class R:
            pass

        return R()

    monkeypatch.setattr("relay.slack.requests.post", fake_post)
    post(cfg_with_webhook, "task done")
    assert len(calls) == 1
    assert calls[0]["url"] == "https://hooks.slack.com/services/test"
    assert calls[0]["json"] == {"text": f"[{cfg_with_webhook.project_name}] task done"}


def test_post_with_owner_prefixes_human(
    cfg_with_webhook, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict] = []
    monkeypatch.setattr(
        "relay.slack.requests.post",
        lambda url, json=None, timeout=None: (calls.append({"json": json}), type("R", (), {})())[1],
    )
    post(cfg_with_webhook, "task done", owner="marc")
    assert calls[0]["json"]["text"] == (
        f"[{cfg_with_webhook.project_name}] [marc] task done"
    )


def test_post_with_image_url_attaches(
    cfg_with_webhook, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict] = []

    def fake_post(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        calls.append({"url": url, "json": json})
        class R:
            pass
        return R()

    monkeypatch.setattr("relay.slack.requests.post", fake_post)
    post(cfg_with_webhook, "🎉 done", image_url="https://media.giphy.com/x.gif")
    payload = calls[0]["json"]
    expected_text = f"[{cfg_with_webhook.project_name}] 🎉 done"
    assert payload["text"] == expected_text
    assert payload["attachments"] == [
        {"image_url": "https://media.giphy.com/x.gif", "fallback": expected_text}
    ]


def test_post_without_image_url_omits_attachments(
    cfg_with_webhook, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict] = []
    monkeypatch.setattr(
        "relay.slack.requests.post",
        lambda url, json=None, timeout=None: (calls.append({"json": json}), type("R", (), {})())[1],
    )
    post(cfg_with_webhook, "plain")
    assert "attachments" not in calls[0]["json"]


def test_gif_for_returns_none_when_unconfigured(tmp_path: Path) -> None:
    _scaffold_min(tmp_path)
    cfg = load_config(tmp_path)
    assert cfg.gif_for("done") is None
    assert cfg.gif_for("panic") is None


def test_gif_for_picks_from_configured_list(tmp_path: Path) -> None:
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        [slack.gifs]
        done = ["https://media.giphy.com/done-1.gif"]
        panic = ["https://media.giphy.com/panic-1.gif", "https://media.giphy.com/panic-2.gif"]
        """,
    )
    _write(tmp_path / "relay.local.toml", 'user = "marc"\n')
    cfg = load_config(tmp_path)
    assert cfg.gif_for("done") == "https://media.giphy.com/done-1.gif"
    assert cfg.gif_for("panic") in {
        "https://media.giphy.com/panic-1.gif",
        "https://media.giphy.com/panic-2.gif",
    }
    assert cfg.gif_for("undefined-kind") is None


def test_gifs_invalid_shape_raises_config_error(tmp_path: Path) -> None:
    from relay.config import ConfigError

    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        [slack.gifs]
        done = "not-a-list"
        """,
    )
    _write(tmp_path / "relay.local.toml", 'user = "marc"\n')
    with pytest.raises(ConfigError, match=r"\[slack\.gifs\]"):
        load_config(tmp_path)


def test_env_var_only_is_the_webhook_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _scaffold_min(tmp_path)
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/from-env")
    cfg = load_config(tmp_path)
    assert cfg.slack_webhook == "https://hooks.slack.com/services/from-env"


def test_toml_webhook_field_is_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A leftover [slack].webhook in relay.toml must not be read — env var only."""
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        [slack]
        webhook = "https://hooks.slack.com/services/from-toml"
        """,
    )
    _write(tmp_path / "relay.local.toml", 'user = "marc"\n')
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    cfg = load_config(tmp_path)
    assert cfg.slack_webhook is None


def test_enabled_default_is_true(tmp_path: Path) -> None:
    _scaffold_min(tmp_path)
    cfg = load_config(tmp_path)
    assert cfg.slack_enabled is True


def test_enabled_false_in_local_toml_opts_out(tmp_path: Path) -> None:
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        """,
    )
    _write(
        tmp_path / "relay.local.toml",
        """
        user = "marc"
        [slack]
        enabled = false
        """,
    )
    cfg = load_config(tmp_path)
    assert cfg.slack_enabled is False


def test_local_enabled_overrides_shared(tmp_path: Path) -> None:
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        [slack]
        enabled = true
        """,
    )
    _write(
        tmp_path / "relay.local.toml",
        """
        user = "marc"
        [slack]
        enabled = false
        """,
    )
    cfg = load_config(tmp_path)
    assert cfg.slack_enabled is False


def test_disabled_post_writes_to_stderr_no_crash(
    tmp_path: Path, capsys
) -> None:
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        [slack]
        enabled = false
        """,
    )
    _write(tmp_path / "relay.local.toml", 'user = "marc"\n')
    cfg = load_config(tmp_path)
    post(cfg, "muted hello", owner="marc")
    err = capsys.readouterr().err
    assert "[slack] disabled" in err
    assert f"[{cfg.project_name}] [marc] muted hello" in err


def test_enabled_but_no_webhook_crashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    _scaffold_min(tmp_path)
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    cfg = load_config(tmp_path)
    with pytest.raises(typer.Exit) as exc:
        post(cfg, "should crash")
    assert exc.value.exit_code == 1
    err = capsys.readouterr().err
    assert "$SLACK_WEBHOOK_URL" in err


def test_post_failure_crashes(
    cfg_with_webhook, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    def fake_post(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise requests.ConnectionError("no network")

    monkeypatch.setattr("relay.slack.requests.post", fake_post)
    with pytest.raises(typer.Exit) as exc:
        post(cfg_with_webhook, "lost message")
    assert exc.value.exit_code == 1

    err = capsys.readouterr().err
    assert "post failed" in err
    assert f"[{cfg_with_webhook.project_name}] lost message" in err


def test_post_failure_with_task_path_appends_to_log_then_crashes(
    cfg_with_webhook, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task_path = tmp_path / "tasks" / "001-x"
    task_path.mkdir(parents=True)
    (task_path / "log.md").write_text("")

    def fake_post(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise requests.ConnectionError("no network")

    monkeypatch.setattr("relay.slack.requests.post", fake_post)
    with pytest.raises(typer.Exit):
        post(cfg_with_webhook, "daemon message", task_path=task_path)

    log_text = (task_path / "log.md").read_text()
    assert "[slack]" in log_text
    assert "post failed" in log_text
    assert "ConnectionError" in log_text


def test_invalid_enabled_type_raises_config_error(tmp_path: Path) -> None:
    from relay.config import ConfigError

    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        [slack]
        enabled = "yes"
        """,
    )
    _write(tmp_path / "relay.local.toml", 'user = "marc"\n')
    with pytest.raises(ConfigError):
        load_config(tmp_path)
