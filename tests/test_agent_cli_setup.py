from __future__ import annotations

import subprocess

import pytest

from coga.agent_cli_setup import offer_agent_cli


def _machine(
    monkeypatch: pytest.MonkeyPatch,
    *,
    have: set[str],
    answers: list[bool],
    platform: str = "darwin",
    install_ok: bool = True,
) -> list[list[str]]:
    """Fake a machine with the binaries in `have`; installs add the agent.

    Returns the argv of every subprocess run; `answers` feed the confirm
    prompts in order."""
    present = set(have)
    calls: list[list[str]] = []
    monkeypatch.setattr("coga.agent_cli_setup.sys.platform", platform)
    monkeypatch.setattr(
        "coga.agent_cli_setup.shutil.which",
        lambda name: f"/usr/bin/{name}" if name in present else None,
    )
    prompts = iter(answers)
    monkeypatch.setattr(
        "coga.agent_cli_setup.typer.confirm", lambda *a, **kw: next(prompts)
    )

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        if argv[0] in {"brew", "npm"} and install_ok:
            present.add("codex" if "codex" in argv[-1] else "claude")
        return subprocess.CompletedProcess(argv, 0 if install_ok else 1)

    monkeypatch.setattr("coga.agent_cli_setup.subprocess.run", fake_run)
    return calls


def test_agent_cli_already_on_path_asks_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _machine(monkeypatch, have={"claude"}, answers=[])
    assert offer_agent_cli("claude")
    assert calls == []


def test_macos_installs_the_brew_cask_then_logs_in(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    calls = _machine(monkeypatch, have={"brew", "npm"}, answers=[True, True])
    assert offer_agent_cli("claude")
    assert calls == [
        ["brew", "install", "--cask", "claude-code"],
        ["/usr/bin/claude"],
    ]
    assert "Will run: brew install --cask claude-code" in capsys.readouterr().out


def test_linux_installs_with_npm_then_runs_codex_login(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _machine(
        monkeypatch, have={"brew", "npm"}, answers=[True, True], platform="linux"
    )
    assert offer_agent_cli("codex")
    assert calls == [
        ["npm", "install", "-g", "@openai/codex"],
        ["/usr/bin/codex", "login"],
    ]


def test_login_declined_still_reports_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _machine(monkeypatch, have={"npm"}, answers=[True, False])
    assert offer_agent_cli("codex")
    assert calls == [["npm", "install", "-g", "@openai/codex"]]


def test_declined_install_runs_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _machine(monkeypatch, have={"brew"}, answers=[False])
    assert not offer_agent_cli("claude")
    assert calls == []


def test_failed_install_points_at_the_install_url(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    calls = _machine(monkeypatch, have={"npm"}, answers=[True], install_ok=False)
    assert not offer_agent_cli("claude")
    assert calls == [["npm", "install", "-g", "@anthropic-ai/claude-code"]]
    assert "https://claude.com/claude-code" in capsys.readouterr().err


def test_no_installer_prints_the_url_without_prompting(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """No `curl | sh`: without brew (macOS) or npm, coga only names the URL."""
    calls = _machine(monkeypatch, have={"brew"}, answers=[], platform="linux")
    assert not offer_agent_cli("codex")
    assert calls == []
    assert "https://github.com/openai/codex" in capsys.readouterr().err


def test_unknown_agent_cli_is_never_offered(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _machine(monkeypatch, have={"brew", "npm"}, answers=[])
    assert not offer_agent_cli("some-custom-agent")
    assert calls == []
