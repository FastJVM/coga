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
    path.write_text(dedent(text).lstrip(), encoding="utf-8", newline="\n")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"

        [agents.claude]
        cli = "claude"
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
    assert result.stdout == "THEVALUE\n"
    assert result.stderr == ""


def test_secret_get_resolves_env(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOMEVAR", "env_value")
    result = CliRunner().invoke(app, ["secret", "get", "env:SOMEVAR"])
    assert result.exit_code == 0, result.output
    assert result.stdout == "env_value\n"
    assert result.stderr == ""


def test_secret_get_rejects_literal(repo: Path) -> None:
    """Literals are no longer resolvable — there is no catalog and a raw literal
    is rejected (only `op://…` or `env:VAR` references are valid)."""
    result = CliRunner().invoke(app, ["secret", "get", "just-a-value"])
    assert result.exit_code == 2
    assert result.stdout == ""
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
    assert result.stdout == ""
    # The error names the reference, never a resolved value.
    assert "op://Vault/item/field" in result.output


def test_secret_get_fails_loud_on_unset_env(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("MISSINGVAR", raising=False)
    result = CliRunner().invoke(app, ["secret", "get", "env:MISSINGVAR"])
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "MISSINGVAR" in result.stderr


@pytest.mark.parametrize(
    ("args", "code", "stdout_help"),
    [
        ([], 2, True),
        (["unknown"], 2, False),
        (["get"], 2, False),
        (["get", "env:ONE", "extra"], 2, False),
        (["get", "--help"], 0, True),
        (["--help"], 0, True),
    ],
)
def test_secret_argument_streams(
    repo: Path, args: list[str], code: int, stdout_help: bool
) -> None:
    result = CliRunner().invoke(app, ["secret", *args])
    assert result.exit_code == code, result.output
    if stdout_help:
        assert "Usage:" in result.stdout
        assert result.stderr == ""
    else:
        assert result.stdout == ""
        assert "Usage:" in result.stderr


@pytest.mark.parametrize("outcome", ["success", "failure", "missing"])
def test_secret_main_preserves_parent_auth_without_side_effects(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    outcome: str,
) -> None:
    import os
    from coga import cli, config

    # No user, agent config or terminal; dirty task/log/report/usage files must
    # remain byte-identical. All credentials and provider output are fake.
    (repo / "coga.local.toml").unlink()
    _write(repo / "coga.toml", "version = 1\n")
    for name in ("tasks/dirty.md", "log.md", "report.md", "usage.jsonl"):
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("unfinished operator edits\n", encoding="utf-8")
    before = {p.relative_to(repo): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
    token = "FAKE_OPERATOR_AUTH_SUPPORT_07"
    sentinel = "FAKE_RESOLVED_VALUE_SUPPORT_07"
    auth = {
        "OP_SERVICE_ACCOUNT_TOKEN": token,
        "OP_CONNECT_TOKEN": token,
        "OP_CONNECT_HOST": "https://fake.invalid",
        "OP_SESSION_support07": token,
    }
    for name, value in auth.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    monkeypatch.setattr(cli, "_register_alias_placeholder", lambda *_: None)
    monkeypatch.setattr("sys.argv", ["coga", "secret", "get", "op://Fake/item/field"])

    def forbidden(*args, **kwargs):
        raise AssertionError("secret query crossed a launch/publication boundary")

    for target in (
        "coga.compose.compose_prompt", "coga.compose.compose_prompt_report",
        "coga.logfile.append_log", "coga.notification.post", "coga.notification.notify",
        "coga.usage.append_record", "coga.git.publish", "coga.git.refresh",
        "coga.launch._report", "coga.agent_skills.refresh_agent_skill_view",
    ):
        monkeypatch.setattr(target, forbidden)

    def fake_run(argv, **kwargs):
        assert argv == ["op", "read", "op://Fake/item/field"]
        effective = kwargs.get("env", os.environ)
        assert all(effective.get(k) == v for k, v in auth.items())
        if outcome == "missing":
            raise FileNotFoundError("fake op absent")
        return subprocess.CompletedProcess(
            argv, 0 if outcome == "success" else 1,
            stdout=sentinel + "\n", stderr="fake provider refused",
        )

    monkeypatch.setattr(config.subprocess, "run", fake_run)
    with pytest.raises(SystemExit) as exc:
        cli.main()
    captured = capsys.readouterr()
    assert exc.value.code == (0 if outcome == "success" else 2)
    assert captured.out == (sentinel + "\n" if outcome == "success" else "")
    assert sentinel not in captured.err
    assert token not in captured.out + captured.err
    assert {p.relative_to(repo): p.read_bytes() for p in repo.rglob("*") if p.is_file()} == before
    # The same auth is deliberately absent from an ordinary task child.
    child = config.build_launch_env(None, [])
    assert all(k not in child for k in auth)


@pytest.mark.parametrize("success", [False, True])
def test_secret_subprocess_in_dirty_repo_keeps_auth_and_separate_streams(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, success: bool
) -> None:
    import os
    import sys
    from conftest import init_git_repo, write_executable
    from coga.config import is_op_auth_env_var

    git_repo = init_git_repo(tmp_path)
    root = git_repo.root
    coga_os = root / "coga"
    (coga_os / "coga.toml").write_text("version = 1\n", encoding="utf-8")
    (coga_os / "coga.local.toml").unlink(missing_ok=True)
    (coga_os / "log.md").write_text("dirty audit\n", encoding="utf-8")
    (coga_os / "unfinished.md").write_text("dirty state\n", encoding="utf-8")
    tools = tmp_path / "tools"
    tools.mkdir()
    write_executable(tools / "op", '''
        import os
        import sys
        assert sys.argv[1:] == ["read", "op://Fake/item/field"]
        assert os.environ.get("OP_SERVICE_ACCOUNT_TOKEN") == "FAKE_AUTH_SUPPORT_07"
        assert sys.stdin.read() == ""
        print("FAKE_CHILD_VALUE_SUPPORT_07")
        if os.environ["SUPPORT07_SUCCESS"] != "1":
            print("fake provider refused", file=sys.stderr)
            sys.exit(1)
    ''')
    env = {k: v for k, v in os.environ.items() if not is_op_auth_env_var(k)}
    env.update(
        OP_SERVICE_ACCOUNT_TOKEN="FAKE_AUTH_SUPPORT_07",
        SUPPORT07_SUCCESS="1" if success else "0",
        PATH=str(tools) + os.pathsep + env["PATH"],
        PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"),
        TERM="dumb",
    )
    def snapshot():
        return {
            p.relative_to(root): p.read_bytes() for p in root.rglob("*")
            if p.is_file() and ".git" not in p.relative_to(root).parts
        }

    before = snapshot()
    head = git_repo.git("rev-parse", "HEAD")
    origin = git_repo.git("rev-parse", "refs/heads/main", cwd=git_repo.origin)
    dirty = git_repo.git("status", "--porcelain")
    result = subprocess.run(
        [sys.executable, "-m", "coga.cli", "secret", "get", "op://Fake/item/field"],
        cwd=root, env=env, input="", capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == (0 if success else 2), result.stderr
    assert result.stdout == ("FAKE_CHILD_VALUE_SUPPORT_07\n" if success else "")
    assert "FAKE_CHILD_VALUE_SUPPORT_07" not in result.stderr
    assert "FAKE_AUTH_SUPPORT_07" not in result.stdout + result.stderr
    assert snapshot() == before
    assert git_repo.git("rev-parse", "HEAD") == head
    assert git_repo.git("rev-parse", "refs/heads/main", cwd=git_repo.origin) == origin
    assert git_repo.git("status", "--porcelain") == dirty


@pytest.mark.parametrize("config_text", ["invalid = [", 'version = 1\n[aliases]\nsecret = "status"\n'])
def test_secret_main_refuses_bad_config_without_stdout(
    repo: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str], config_text: str,
) -> None:
    from coga import cli

    _write(repo / "coga.toml", config_text)
    monkeypatch.setattr("sys.argv", ["coga", "secret", "get", "env:FAKE_SUPPORT07"])
    monkeypatch.setenv("FAKE_SUPPORT07", "MUST_NOT_RESOLVE_SUPPORT07")
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err
    assert "MUST_NOT_RESOLVE_SUPPORT07" not in captured.err


def test_secret_main_requires_repo_without_resolving(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    from coga import cli

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FAKE_SUPPORT07", "MUST_NOT_RESOLVE_SUPPORT07")
    monkeypatch.setattr("sys.argv", ["coga", "secret", "get", "env:FAKE_SUPPORT07"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "No coga.toml" in captured.err
    assert "coga init --user NAME" in captured.err
    assert "MUST_NOT_RESOLVE_SUPPORT07" not in captured.err


def test_secret_main_refuses_malformed_local_config_without_resolving(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    from coga import cli

    _write(repo / "coga.local.toml", "invalid = [")
    monkeypatch.setenv("FAKE_SUPPORT07", "MUST_NOT_RESOLVE_SUPPORT07")
    monkeypatch.setattr("sys.argv", ["coga", "secret", "get", "env:FAKE_SUPPORT07"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err
    assert "MUST_NOT_RESOLVE_SUPPORT07" not in captured.err
