"""`coga secret get <ref>` — resolve and print one secret reference on demand.

Secrets are declared inline per-ticket (there is no `[secrets]` catalog), so
`get` takes a reference directly — `op://vault/item/field` or `env:VAR` — and
resolves it through the same launch-time path. Mocks `subprocess.run`; no test
requires a real `op` binary or 1Password account.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from coga.cli import app


def _write(path: Path, text: str) -> None:
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    _write(
        tmp_path / "coga.toml",
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
        tmp_path / "coga.local.toml",
        """
        user = "marc"
        """,
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_secret_get_resolves_op(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(argv, **kwargs):
        assert argv == ["op", "read", "op://Vault/item/field"]
        return subprocess.CompletedProcess(argv, 0, stdout="THEVALUE\n", stderr="")

    monkeypatch.setattr("coga.config.subprocess.run", fake_run)
    result = CliRunner().invoke(app, ["secret", "get", "op://Vault/item/field"])
    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == "THEVALUE"


def test_secret_get_resolves_env(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOMEVAR", "env_value")
    result = CliRunner().invoke(app, ["secret", "get", "env:SOMEVAR"])
    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == "env_value"


def test_secret_get_rejects_literal(repo: Path) -> None:
    """Literals are no longer resolvable — there is no catalog and a raw literal
    is rejected (only `op://…` or `env:VAR` references are valid)."""
    result = CliRunner().invoke(app, ["secret", "get", "just-a-value"])
    assert result.exit_code == 2
    # The error names the rejected reference, never treats it as a value...
    assert "just-a-value" in result.output
    assert "not a resolvable reference" in result.output
    # ...and is phrased for a `secret get` query, not the internal ticket form.
    assert "ticket secret" not in result.output


def test_secret_get_fails_loud_on_op_error(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="boom")

    monkeypatch.setattr("coga.config.subprocess.run", fake_run)
    result = CliRunner().invoke(app, ["secret", "get", "op://Vault/item/field"])
    assert result.exit_code == 2
    # The error names the reference, never a resolved value.
    assert "op://Vault/item/field" in result.output


def test_secret_get_fails_loud_on_unset_env(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("MISSINGVAR", raising=False)
    result = CliRunner().invoke(app, ["secret", "get", "env:MISSINGVAR"])
    assert result.exit_code == 2
    assert "MISSINGVAR" in result.output
