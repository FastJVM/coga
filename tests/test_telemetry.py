from __future__ import annotations

import re
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from coga import telemetry
from coga.cli import app
from coga.config import ConfigError, load_config

runner = CliRunner()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A minimal coga repo with a couple of tickets, cwd set to it."""
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"

        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    # Two tickets — one file-form, one directory-form — so tickets_total == 2.
    _write(tmp_path / "tasks" / "alpha.md", "---\nslug: alpha\n---\n")
    _write(tmp_path / "tasks" / "beta" / "ticket.md", "---\nslug: beta\n---\n")
    monkeypatch.chdir(tmp_path)
    return tmp_path


# --- config resolution ---------------------------------------------------------


def test_telemetry_enabled_default_true(repo: Path) -> None:
    assert load_config(repo).telemetry_enabled is True


def test_telemetry_disabled_in_shared_config(repo: Path) -> None:
    _write(
        repo / "coga.toml",
        """
        version = 1
        default_status = "draft"

        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"

        [telemetry]
        enabled = false
        """,
    )
    assert load_config(repo).telemetry_enabled is False


def test_local_telemetry_overrides_shared(repo: Path) -> None:
    _write(
        repo / "coga.toml",
        """
        version = 1
        default_status = "draft"

        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"

        [telemetry]
        enabled = true
        """,
    )
    _write(repo / "coga.local.toml", 'user = "marc"\n\n[telemetry]\nenabled = false\n')
    assert load_config(repo).telemetry_enabled is False


def test_non_bool_telemetry_enabled_rejected(repo: Path) -> None:
    _write(repo / "coga.local.toml", 'user = "marc"\n\n[telemetry]\nenabled = "no"\n')
    with pytest.raises(ConfigError, match="must be a boolean"):
        load_config(repo)


def test_unknown_telemetry_key_rejected(repo: Path) -> None:
    _write(repo / "coga.local.toml", 'user = "marc"\n\n[telemetry]\nlevel = "high"\n')
    with pytest.raises(ConfigError, match="unknown key"):
        load_config(repo)


# --- disable precedence (env beats config) -------------------------------------


def test_disabled_reason_none_when_enabled(repo: Path) -> None:
    assert telemetry.disabled_reason(load_config(repo)) is None
    assert telemetry.telemetry_disabled(load_config(repo)) is False


def test_do_not_track_disables(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DO_NOT_TRACK", "1")
    assert "DO_NOT_TRACK" in telemetry.disabled_reason(load_config(repo))


def test_coga_telemetry_disable_disables(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COGA_TELEMETRY_DISABLE", "1")
    assert "COGA_TELEMETRY_DISABLE" in telemetry.disabled_reason(load_config(repo))


def test_do_not_track_takes_precedence_over_config(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Config says on, env says off — env wins.
    monkeypatch.setenv("DO_NOT_TRACK", "true")
    assert telemetry.telemetry_disabled(load_config(repo)) is True


def test_falsy_env_does_not_disable(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A falsy literal must not count as "set to disable".
    monkeypatch.setenv("COGA_TELEMETRY_DISABLE", "0")
    monkeypatch.setenv("DO_NOT_TRACK", "false")
    assert telemetry.disabled_reason(load_config(repo)) is None


# --- payload -------------------------------------------------------------------


def test_payload_has_exactly_three_keys(repo: Path) -> None:
    payload = telemetry.build_payload(load_config(repo))
    assert set(payload) == {"instance_id", "tickets_total", "last_run"}


def test_payload_no_pii(repo: Path) -> None:
    """No field leaks repo path, cwd, user, hostname, slug, or title."""
    payload = telemetry.build_payload(load_config(repo))
    blob = repr(payload)
    for leak in (str(repo), "marc", "alpha", "beta", "tasks", "coga.toml"):
        assert leak not in blob


def test_tickets_total_counts_ticket_files(repo: Path) -> None:
    assert telemetry.build_payload(load_config(repo))["tickets_total"] == 2


def test_last_run_is_iso_date(repo: Path) -> None:
    last_run = telemetry.build_payload(load_config(repo))["last_run"]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", last_run)


def test_instance_id_is_uuid4_shaped(repo: Path) -> None:
    instance_id = telemetry.build_payload(load_config(repo))["instance_id"]
    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        instance_id,
    )


def test_instance_id_persists_across_reads(repo: Path) -> None:
    first = telemetry.read_or_create_instance_id()
    assert telemetry.instance_id_path().is_file()
    assert telemetry.read_or_create_instance_id() == first


# --- send ----------------------------------------------------------------------


def test_send_skips_when_disabled(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DO_NOT_TRACK", "1")
    posted: list = []
    monkeypatch.setattr(
        "coga.telemetry.requests.post",
        lambda *a, **k: posted.append(a) or _ok_response(),
    )
    result = telemetry.send(load_config(repo))
    assert result.skipped is True
    assert result.sent is False
    assert posted == []  # zero network calls


def test_send_posts_when_enabled(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict = {}

    def _capture(url, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return _ok_response()

    monkeypatch.setattr("coga.telemetry.requests.post", _capture)
    result = telemetry.send(load_config(repo))
    assert result.sent is True
    assert set(captured["json"]) == {"instance_id", "tickets_total", "last_run"}


def test_send_never_raises_on_network_error(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import requests

    def _boom(*a, **k):
        raise requests.RequestException("offline")

    monkeypatch.setattr("coga.telemetry.requests.post", _boom)
    result = telemetry.send(load_config(repo))
    assert result.sent is False
    assert result.skipped is False
    assert "network error" in result.detail


def test_send_reports_non_2xx(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "coga.telemetry.requests.post", lambda *a, **k: _ok_response(500)
    )
    result = telemetry.send(load_config(repo))
    assert result.sent is False
    assert "500" in result.detail


def test_url_env_override(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COGA_TELEMETRY_URL", "https://test.relay/ping")
    assert telemetry.telemetry_url() == "https://test.relay/ping"


# --- CLI -----------------------------------------------------------------------


def test_show_prints_payload_without_sending(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    posted: list = []
    monkeypatch.setattr(
        "coga.telemetry.requests.post", lambda *a, **k: posted.append(a)
    )
    result = runner.invoke(app, ["telemetry", "show"])
    assert result.exit_code == 0, result.output
    assert "instance_id" in result.output
    assert "tickets_total" in result.output
    assert posted == []  # show never sends


def test_send_command_exits_zero_on_failure(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import requests

    def _boom(*a, **k):
        raise requests.RequestException("offline")

    monkeypatch.setattr("coga.telemetry.requests.post", _boom)
    result = runner.invoke(app, ["telemetry", "send"])
    assert result.exit_code == 0, result.output
    assert "network error" in result.output


def _ok_response(status: int = 204):
    class R:
        status_code = status
        text = ""

    return R()
