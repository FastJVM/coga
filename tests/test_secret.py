"""`relay secret get <key>` — resolve and print one declared secret on demand.

Mocks `subprocess.run`; no test requires a real `op` binary or 1Password account.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay.cli import app


def _write(path: Path, text: str) -> None:
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
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
        stripe_key = "op://vault/stripe/key"
        env_key = "env:SOME_ENV_SECRET"
        literal = "just-a-value"
        """,
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_secret_get_resolves_op(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(argv, **kwargs):
        assert argv == ["op", "read", "op://vault/stripe/key"]
        return subprocess.CompletedProcess(argv, 0, stdout="sk_op_secret\n", stderr="")

    monkeypatch.setattr("relay.config.subprocess.run", fake_run)
    result = CliRunner().invoke(app, ["secret", "get", "stripe_key"])
    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == "sk_op_secret"


def test_secret_get_resolves_literal(repo: Path) -> None:
    result = CliRunner().invoke(app, ["secret", "get", "literal"])
    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == "just-a-value"


def test_secret_get_fails_loud_on_op_error(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(
            argv, 1, stdout="", stderr="[ERROR] not signed in"
        )

    monkeypatch.setattr("relay.config.subprocess.run", fake_run)
    result = CliRunner().invoke(app, ["secret", "get", "stripe_key"])
    assert result.exit_code == 2
    # The error names the key and reference, never a resolved value.
    assert "stripe_key" in result.output
    assert "op://vault/stripe/key" in result.output


def test_secret_get_fails_loud_on_undeclared_key(repo: Path) -> None:
    result = CliRunner().invoke(app, ["secret", "get", "nonexistent"])
    assert result.exit_code == 2
    assert "not defined in" in result.output
