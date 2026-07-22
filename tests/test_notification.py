from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
import requests
import typer

from coga.config import load_config
from coga.notification import post
from coga.slack_response import classify_slack_response, format_slack_request_error


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _create_min(tmp_path: Path) -> None:
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [notification]
        channels = ["slack"]
        [notification.slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')


@pytest.fixture
def cfg_with_webhook(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _create_min(tmp_path)
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test")
    return load_config(tmp_path)


class _SlackResponse:
    def __init__(self, status_code: int = 200, text: str = "ok") -> None:
        self.status_code = status_code
        self.text = text


def test_post_calls_webhook(cfg_with_webhook, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    def fake_post(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        calls.append({"url": url, "json": json})
        return _SlackResponse()

    monkeypatch.setattr("coga.notification.slack.requests.post", fake_post)
    post(cfg_with_webhook, "task done")
    assert len(calls) == 1
    assert calls[0]["url"] == "https://hooks.slack.com/services/test"
    assert calls[0]["json"] == {"text": f"[{cfg_with_webhook.project_name}] task done"}


def test_post_with_owner_prefixes_human(
    cfg_with_webhook, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict] = []
    monkeypatch.setattr(
        "coga.notification.slack.requests.post",
        lambda url, json=None, timeout=None: (calls.append({"json": json}), _SlackResponse())[1],
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
        return _SlackResponse()

    monkeypatch.setattr("coga.notification.slack.requests.post", fake_post)
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
        "coga.notification.slack.requests.post",
        lambda url, json=None, timeout=None: (calls.append({"json": json}), _SlackResponse())[1],
    )
    post(cfg_with_webhook, "plain")
    assert "attachments" not in calls[0]["json"]


def test_gif_for_returns_none_when_unconfigured(tmp_path: Path) -> None:
    _create_min(tmp_path)
    cfg = load_config(tmp_path)
    assert cfg.gif_for("done") is None
    assert cfg.gif_for("block") is None


def test_gif_for_picks_from_configured_list(tmp_path: Path) -> None:
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [notification.slack.gifs]
        done = ["https://media.giphy.com/done-1.gif"]
        block = ["https://media.giphy.com/block-1.gif", "https://media.giphy.com/block-2.gif"]
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    cfg = load_config(tmp_path)
    assert cfg.gif_for("done") == "https://media.giphy.com/done-1.gif"
    assert cfg.gif_for("block") in {
        "https://media.giphy.com/block-1.gif",
        "https://media.giphy.com/block-2.gif",
    }
    assert cfg.gif_for("undefined-kind") is None


def test_gifs_invalid_shape_raises_config_error(tmp_path: Path) -> None:
    from coga.config import ConfigError

    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [notification.slack.gifs]
        done = "not-a-list"
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    with pytest.raises(ConfigError, match=r"\[notification\.slack\.gifs\]"):
        load_config(tmp_path)


def test_toml_webhook_env_indirection_resolves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`[notification.slack].webhook = "env:VAR"` resolves the env var."""
    # `_create_min` ships `webhook = "env:SLACK_WEBHOOK_URL"`.
    _create_min(tmp_path)
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/from-env")
    cfg = load_config(tmp_path)
    assert cfg.slack_webhook == "https://hooks.slack.com/services/from-env"
    assert cfg.notification_channels == ("slack",)


def test_notification_channels_dispatch_enabled(
    cfg_with_webhook, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict] = []
    monkeypatch.setattr(
        "coga.notification.slack.requests.post",
        lambda url, json=None, timeout=None: (
            calls.append({"url": url, "json": json}),
            _SlackResponse(),
        )[1],
    )

    post(cfg_with_webhook, "channel dispatch")

    assert calls == [
        {
            "url": "https://hooks.slack.com/services/test",
            "json": {"text": f"[{cfg_with_webhook.project_name}] channel dispatch"},
        }
    ]


def test_unknown_notification_channel_raises_config_error(tmp_path: Path) -> None:
    from coga.config import ConfigError

    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [notification]
        channels = ["email"]
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    with pytest.raises(ConfigError, match="unsupported channel"):
        load_config(tmp_path)


def test_notification_channels_dedupe(tmp_path: Path) -> None:
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [notification]
        channels = ["slack", "slack"]
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    cfg = load_config(tmp_path)
    assert cfg.notification_channels == ("slack",)


def test_no_notification_config_and_no_env_resolves_to_no_channels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A fresh repo with no notification config and no env selects no channels.

    This is the first-run posture: a stranger who hasn't set up Slack can run
    commands without a missing-webhook crash. With no `[notification].channels`
    key, no `[notification.slack]`/`[slack]` table, and no `SLACK_WEBHOOK_URL`,
    channels resolve to `()` (not the old `("slack",)` default) and `post`
    takes the no-channel branch instead of crashing.
    """
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    cfg = load_config(tmp_path)
    assert cfg.notification_channels == ()
    post(cfg, "first run, no slack")
    assert "[notification] no channels configured" in capsys.readouterr().err


def test_notification_slack_table_without_channels_infers_slack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A `[notification.slack]` table is opt-in evidence even with no `channels`."""
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [notification.slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    cfg = load_config(tmp_path)
    assert cfg.notification_channels == ("slack",)


def test_bare_env_without_config_infers_slack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bare exported `SLACK_WEBHOOK_URL` is opt-in evidence on its own."""
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/x")
    cfg = load_config(tmp_path)
    assert cfg.notification_channels == ("slack",)


def test_empty_notification_channels_suppresses_post(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [notification]
        channels = []
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    cfg = load_config(tmp_path)
    post(cfg, "no channel")
    assert "[notification] no channels configured" in capsys.readouterr().err


def test_legacy_slack_webhook_still_resolves_with_deprecation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/legacy")

    cfg = load_config(tmp_path)

    assert cfg.slack_webhook == "https://hooks.slack.com/services/legacy"
    assert cfg.notification_channels == ("slack",)
    assert any("[slack].webhook" in n for n in cfg.notification_deprecation_notes)


def test_bare_env_without_toml_key_is_deprecated_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bare exported SLACK_WEBHOOK_URL remains a deprecated compatibility path."""
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/from-env")
    cfg = load_config(tmp_path)
    assert cfg.slack_webhook == "https://hooks.slack.com/services/from-env"
    assert any("SLACK_WEBHOOK_URL" in n for n in cfg.notification_deprecation_notes)


def test_toml_env_indirection_unset_var_is_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`webhook = "env:VAR"` with the var unset resolves to None, not empty string."""
    _create_min(tmp_path)
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    cfg = load_config(tmp_path)
    assert cfg.slack_webhook is None


def test_toml_literal_webhook_accepted(tmp_path: Path) -> None:
    """A literal URL is accepted by the parser (docs steer to `env:`, but it works)."""
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [notification.slack]
        webhook = "https://hooks.slack.com/services/literal"
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    cfg = load_config(tmp_path)
    assert cfg.slack_webhook == "https://hooks.slack.com/services/literal"


def test_local_webhook_overrides_shared(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If both shared and local set `[notification.slack].webhook`, local wins."""
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [notification.slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        """,
    )
    _write(
        tmp_path / "coga.local.toml",
        """
        user = "marc"
        [notification.slack]
        webhook = "https://hooks.slack.com/services/local-machine"
        """,
    )
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/shared-env")
    cfg = load_config(tmp_path)
    assert cfg.slack_webhook == "https://hooks.slack.com/services/local-machine"


def test_webhook_non_string_raises_config_error(tmp_path: Path) -> None:
    from coga.config import ConfigError

    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [notification.slack]
        webhook = 123
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    with pytest.raises(ConfigError, match=r"\[notification\.slack\]\.webhook"):
        load_config(tmp_path)


# --- important_webhook (the coga-important channel) ----------------------------


def _create_min_both_webhooks(tmp_path: Path) -> None:
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [notification]
        channels = ["slack"]
        [notification.slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        important_webhook = "env:COGA_IMPORTANT_WEBHOOK_URL"
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')


@pytest.fixture
def cfg_with_both_webhooks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _create_min_both_webhooks(tmp_path)
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/flow")
    monkeypatch.setenv(
        "COGA_IMPORTANT_WEBHOOK_URL", "https://hooks.slack.com/services/important"
    )
    return load_config(tmp_path)


def test_toml_important_webhook_env_indirection_resolves(
    cfg_with_both_webhooks,
) -> None:
    """`important_webhook = "env:VAR"` resolves alongside the primary webhook."""
    assert (
        cfg_with_both_webhooks.slack_important_webhook
        == "https://hooks.slack.com/services/important"
    )
    assert cfg_with_both_webhooks.slack_webhook == "https://hooks.slack.com/services/flow"


def test_important_webhook_unset_env_is_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _create_min_both_webhooks(tmp_path)
    monkeypatch.delenv("COGA_IMPORTANT_WEBHOOK_URL", raising=False)
    cfg = load_config(tmp_path)
    assert cfg.slack_important_webhook is None


def test_important_webhook_absent_is_none(tmp_path: Path) -> None:
    """A repo that never opted into a second channel resolves it to None."""
    _create_min(tmp_path)
    cfg = load_config(tmp_path)
    assert cfg.slack_important_webhook is None


def test_important_post_uses_important_webhook(
    cfg_with_both_webhooks, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict] = []

    def fake_post(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        calls.append({"url": url, "json": json})
        return _SlackResponse()

    monkeypatch.setattr("coga.notification.slack.requests.post", fake_post)
    post(cfg_with_both_webhooks, "fee window closes 2027-01-15", important=True)
    assert len(calls) == 1
    assert calls[0]["url"] == "https://hooks.slack.com/services/important"


def test_routine_post_still_uses_default_webhook(
    cfg_with_both_webhooks, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Configuring a second webhook must not divert ordinary state transitions."""
    calls: list[dict] = []

    def fake_post(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        calls.append({"url": url, "json": json})
        return _SlackResponse()

    monkeypatch.setattr("coga.notification.slack.requests.post", fake_post)
    post(cfg_with_both_webhooks, "task done")
    assert len(calls) == 1
    assert calls[0]["url"] == "https://hooks.slack.com/services/flow"


def test_important_post_without_important_webhook_crashes(
    cfg_with_webhook,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An `--important` post crashes when the key is unset — never reroutes.

    Delivering a human-action alert to the wrong channel while reporting success
    is worse than crashing; the crash is what gets the config fixed. See the
    ticket blackboard.
    """
    calls: list[dict] = []

    def fake_post(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        calls.append({"url": url, "json": json})
        return _SlackResponse()

    monkeypatch.setattr("coga.notification.slack.requests.post", fake_post)
    with pytest.raises(typer.Exit) as exc:
        post(cfg_with_webhook, "fee window closes 2027-01-15", important=True)
    assert exc.value.exit_code == 1
    assert calls == []
    assert "important_webhook" in capsys.readouterr().err


def test_local_important_webhook_overrides_shared(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _create_min_both_webhooks(tmp_path)
    _write(
        tmp_path / "coga.local.toml",
        """
        user = "marc"
        [notification.slack]
        important_webhook = "https://hooks.slack.com/services/local-important"
        """,
    )
    monkeypatch.setenv(
        "COGA_IMPORTANT_WEBHOOK_URL", "https://hooks.slack.com/services/shared-important"
    )
    cfg = load_config(tmp_path)
    assert cfg.slack_important_webhook == "https://hooks.slack.com/services/local-important"


def test_important_webhook_non_string_raises_config_error(tmp_path: Path) -> None:
    from coga.config import ConfigError

    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [notification.slack]
        important_webhook = 123
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    with pytest.raises(ConfigError, match=r"\[notification\.slack\]\.important_webhook"):
        load_config(tmp_path)


def test_important_webhook_rejected_in_legacy_slack_table(tmp_path: Path) -> None:
    """The legacy `[slack]` table has no resolver for the new key, so reject it.

    Accepting it there would silently drop the second channel's URL — the repo
    would look configured and still post every alert to coga-flow.
    """
    from coga.config import ConfigError

    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        important_webhook = "env:COGA_IMPORTANT_WEBHOOK_URL"
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    with pytest.raises(ConfigError, match="unknown key"):
        load_config(tmp_path)


# --- important_recipient (the coga-important triage owner) ---------------------


def _create_min_with_recipient(tmp_path: Path, recipient: str = '"triage"') -> None:
    _write(
        tmp_path / "coga.toml",
        f"""
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [notification.slack]
        important_recipient = {recipient}
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')


def test_important_recipient_resolves(tmp_path: Path) -> None:
    """`important_recipient` is a plain coga name — no `env:` indirection."""
    _create_min_with_recipient(tmp_path)
    cfg = load_config(tmp_path)
    assert cfg.slack_important_recipient == "triage"


def test_important_recipient_absent_is_none(tmp_path: Path) -> None:
    """A repo that never named a triage owner resolves it to None."""
    _create_min(tmp_path)
    cfg = load_config(tmp_path)
    assert cfg.slack_important_recipient is None


def test_important_recipient_empty_string_is_none(tmp_path: Path) -> None:
    """An empty name collapses to None so the ordinary owner mention stands."""
    _create_min_with_recipient(tmp_path, recipient='""')
    cfg = load_config(tmp_path)
    assert cfg.slack_important_recipient is None


def test_local_important_recipient_overrides_shared(tmp_path: Path) -> None:
    _create_min_with_recipient(tmp_path)
    _write(
        tmp_path / "coga.local.toml",
        """
        user = "marc"
        [notification.slack]
        important_recipient = "ada"
        """,
    )
    cfg = load_config(tmp_path)
    assert cfg.slack_important_recipient == "ada"


def test_important_recipient_non_string_raises_config_error(tmp_path: Path) -> None:
    from coga.config import ConfigError

    _create_min_with_recipient(tmp_path, recipient="123")
    with pytest.raises(
        ConfigError, match=r"\[notification\.slack\]\.important_recipient"
    ):
        load_config(tmp_path)


def test_important_recipient_rejected_in_legacy_slack_table(tmp_path: Path) -> None:
    """The legacy `[slack]` table has no resolver for the new key, so reject it.

    Accepting it there would silently drop the triage name — every `--important`
    alert would keep @'ing the ticket owner with no error to explain why.
    """
    from coga.config import ConfigError

    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [slack]
        important_recipient = "triage"
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    with pytest.raises(ConfigError, match="unknown key"):
        load_config(tmp_path)


def test_enabled_default_is_true(tmp_path: Path) -> None:
    _create_min(tmp_path)
    cfg = load_config(tmp_path)
    assert cfg.slack_enabled is True


def test_enabled_false_in_local_toml_opts_out(tmp_path: Path) -> None:
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(
        tmp_path / "coga.local.toml",
        """
        user = "marc"
        [notification.slack]
        enabled = false
        """,
    )
    cfg = load_config(tmp_path)
    assert cfg.slack_enabled is False


def test_local_enabled_overrides_shared(tmp_path: Path) -> None:
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [notification.slack]
        enabled = true
        """,
    )
    _write(
        tmp_path / "coga.local.toml",
        """
        user = "marc"
        [notification.slack]
        enabled = false
        """,
    )
    cfg = load_config(tmp_path)
    assert cfg.slack_enabled is False


def test_disabled_post_writes_to_stderr_no_crash(
    tmp_path: Path, capsys
) -> None:
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [notification.slack]
        enabled = false
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    cfg = load_config(tmp_path)
    post(cfg, "muted hello", owner="marc")
    err = capsys.readouterr().err
    assert "[slack] disabled" in err
    assert f"[{cfg.project_name}] [marc] muted hello" in err


def test_enabled_but_no_webhook_crashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    _create_min(tmp_path)
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    cfg = load_config(tmp_path)
    with pytest.raises(typer.Exit) as exc:
        post(cfg, "should crash")
    assert exc.value.exit_code == 1
    err = capsys.readouterr().err
    assert "[notification.slack].webhook" in err


def test_post_failure_crashes(
    cfg_with_webhook, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    def fake_post(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise requests.ConnectionError("no network")

    monkeypatch.setattr("coga.notification.slack.requests.post", fake_post)
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

    def fake_post(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise requests.ConnectionError("no network")

    monkeypatch.setattr("coga.notification.slack.requests.post", fake_post)
    with pytest.raises(typer.Exit):
        post(cfg_with_webhook, "daemon message", task_path=task_path)

    # Single-file format: the failure lands in the repo-global audit log,
    # tagged with the task ref, not a per-task log.md.
    log_text = (cfg_with_webhook.repo_root / "log.md").read_text()
    assert "[001-x]" in log_text
    assert "[slack]" in log_text
    assert "post failed" in log_text
    assert "ConnectionError" in log_text


_FAKE_SLACK_WEBHOOK_SECRET = "C0GA_FAKE_WEBHOOK_TOKEN_7D3A9B"


@pytest.mark.parametrize(
    ("failure", "safe_detail"),
    [
        (
            requests.ConnectionError("NameResolutionError: failed to resolve"),
            "DNS/name-resolution failure",
        ),
        (requests.exceptions.Timeout("read timed out"), "request timed out"),
        (requests.ConnectionError("connection reset"), "connection failure"),
        (
            requests.exceptions.ProxyError("proxy unavailable"),
            "proxy connection failure",
        ),
        (requests.exceptions.SSLError("certificate verify failed"), "TLS/SSL failure"),
    ],
)
def test_slack_request_error_formatter_keeps_only_safe_network_context(
    failure: requests.RequestException,
    safe_detail: str,
) -> None:
    failure.args = (
        f"{failure} at /services/TFAKE/BFAKE/{_FAKE_SLACK_WEBHOOK_SECRET}",
    )

    detail = format_slack_request_error(failure)

    assert type(failure).__name__ in detail
    assert safe_detail in detail
    assert _FAKE_SLACK_WEBHOOK_SECRET not in detail
    assert "/services/" not in detail


def test_slack_response_detail_redacts_echoed_webhook_path() -> None:
    status, detail = classify_slack_response(
        502,
        "proxy failed for https://hooks.slack.com/services/TFAKE/BFAKE/"
        f"{_FAKE_SLACK_WEBHOOK_SECRET}",
    )

    assert status == "unreachable"
    assert "[redacted Slack webhook]" in detail
    assert _FAKE_SLACK_WEBHOOK_SECRET not in detail
    assert "/services/" not in detail


@pytest.mark.parametrize(
    ("important", "failure", "safe_detail"),
    [
        (
            False,
            requests.ConnectionError(
                "HTTPSConnectionPool(host='hooks.slack.com', port=443): "
                "Max retries exceeded with url: "
                "https://hooks.slack.com/services/TFAKE/BFAKE/"
                f"{_FAKE_SLACK_WEBHOOK_SECRET} (Caused by "
                "NameResolutionError(\"Failed to resolve 'hooks.slack.com'\"))"
            ),
            "DNS/name-resolution failure",
        ),
        (
            True,
            requests.exceptions.SSLError(
                "HTTPSConnectionPool(host='hooks.slack.com', port=443): "
                "Max retries exceeded with url: /services/TFAKE/BFAKE/"
                f"{_FAKE_SLACK_WEBHOOK_SECRET} (Caused by "
                "SSLCertVerificationError('certificate verify failed'))"
            ),
            "TLS/SSL failure",
        ),
    ],
)
def test_post_request_failure_redacts_webhook_from_stderr_and_log(
    cfg_with_both_webhooks,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    important: bool,
    failure: requests.RequestException,
    safe_detail: str,
) -> None:
    task_path = cfg_with_both_webhooks.repo_root / "tasks" / "001-x"
    task_path.mkdir(parents=True)

    def fake_post(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise failure

    monkeypatch.setattr("coga.notification.slack.requests.post", fake_post)
    with pytest.raises(typer.Exit) as exc:
        post(
            cfg_with_both_webhooks,
            "credential-safe failure",
            task_path=task_path,
            important=important,
        )
    assert exc.value.exit_code == 1

    captured = capsys.readouterr()
    log_text = (cfg_with_both_webhooks.repo_root / "log.md").read_text()
    for diagnostic in (captured.out, captured.err, log_text):
        assert _FAKE_SLACK_WEBHOOK_SECRET not in diagnostic
        assert "/services/" not in diagnostic
    assert type(failure).__name__ in captured.err
    assert type(failure).__name__ in log_text
    assert safe_detail in captured.err
    assert safe_detail in log_text


def test_post_revoked_webhook_response_logs_then_crashes(
    cfg_with_webhook,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    task_path = tmp_path / "tasks" / "001-x"
    task_path.mkdir(parents=True)

    def fake_post(*args, **kwargs):  # type: ignore[no-untyped-def]
        return _SlackResponse(404, "no_service")

    monkeypatch.setattr("coga.notification.slack.requests.post", fake_post)
    with pytest.raises(typer.Exit) as exc:
        post(cfg_with_webhook, "daemon message", task_path=task_path)
    assert exc.value.exit_code == 1

    err = capsys.readouterr().err
    assert "revoked/invalid webhook" in err
    assert "HTTP 404" in err
    assert f"[{cfg_with_webhook.project_name}] daemon message" in err

    # Single-file format: the failure lands in the repo-global audit log,
    # tagged with the task ref, not a per-task log.md.
    log_text = (cfg_with_webhook.repo_root / "log.md").read_text()
    assert "[001-x]" in log_text
    assert "[slack]" in log_text
    assert "revoked/invalid webhook" in log_text
    assert "HTTP 404" in log_text


def _capture(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Stub requests.post and return the list it appends each call's json to."""
    calls: list[dict] = []
    monkeypatch.setattr(
        "coga.notification.slack.requests.post",
        lambda url, json=None, timeout=None: (
            calls.append({"json": json}),
            _SlackResponse(),
        )[1],
    )
    return calls


@pytest.fixture
def cfg_with_users(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [notification.slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [notification.slack.users]
        marc = "U01MARC"
        ada = "U02ADA"
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test")
    return load_config(tmp_path)


def test_slack_users_default_empty(tmp_path: Path) -> None:
    _create_min(tmp_path)
    cfg = load_config(tmp_path)
    assert cfg.slack_users == {}


def test_slack_users_load_and_strip(cfg_with_users) -> None:
    assert cfg_with_users.slack_users == {"marc": "U01MARC", "ada": "U02ADA"}


def test_slack_users_invalid_shape_raises_config_error(tmp_path: Path) -> None:
    from coga.config import ConfigError

    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [notification.slack]
        users = "not-a-table"
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    with pytest.raises(ConfigError, match=r"\[notification\.slack\.users\]"):
        load_config(tmp_path)


def test_slack_users_empty_id_raises_config_error(tmp_path: Path) -> None:
    from coga.config import ConfigError

    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [notification.slack.users]
        marc = ""
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    with pytest.raises(ConfigError, match=r"\[notification\.slack\.users\]\.marc"):
        load_config(tmp_path)


def test_post_owner_with_mapped_id_renders_mention(
    cfg_with_users, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _capture(monkeypatch)
    post(cfg_with_users, "task done", owner="marc")
    assert calls[0]["json"]["text"] == (
        f"[{cfg_with_users.project_name}] [<@U01MARC>] task done"
    )


def test_post_owner_without_mapping_stays_plain(
    cfg_with_users, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _capture(monkeypatch)
    post(cfg_with_users, "task done", owner="stranger")
    assert calls[0]["json"]["text"] == (
        f"[{cfg_with_users.project_name}] [stranger] task done"
    )


def test_post_watchers_cc_only_mapped_names(
    cfg_with_users, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _capture(monkeypatch)
    post(cfg_with_users, "task done", owner="marc", watchers=["ada", "stranger"])
    assert calls[0]["json"]["text"] == (
        f"[{cfg_with_users.project_name}] [<@U01MARC>] task done (cc <@U02ADA>)"
    )


def test_post_watchers_all_unmapped_omits_trailer(
    cfg_with_users, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _capture(monkeypatch)
    post(cfg_with_users, "task done", owner="marc", watchers=["nobody", "stranger"])
    assert "(cc" not in calls[0]["json"]["text"]


def test_invalid_enabled_type_raises_config_error(tmp_path: Path) -> None:
    from coga.config import ConfigError

    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [notification.slack]
        enabled = "yes"
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    with pytest.raises(ConfigError):
        load_config(tmp_path)
