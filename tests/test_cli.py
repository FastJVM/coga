"""Config leniency at the CLI surface — a clone without `coga.local.toml`.

A teammate's fresh clone of a coga repo has no gitignored `coga.local.toml`
yet. `coga --help`, per-command `--help`, and the read-only commands must
still run there; only commands that act *as* someone keep the hard
"No `user` set" error (raised from their own strict `load_config()`).
"""

from __future__ import annotations

from report_helpers import report_cli

import json
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from coga.cli import app, main


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip(), encoding="utf-8", newline="\n")


TICKET = """
---
title: X
status: draft
mode: agent
owner: marc
agent: claude
workflow: null
---

## Description

<!-- coga:blackboard -->
"""


@pytest.fixture
def clone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A coga repo as a teammate first sees it: shared config committed,
    no gitignored `coga.local.toml`."""
    company = tmp_path / "coga"
    _write(
        company / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "tasks" / "fix-retry-logic" / "ticket.md", TICKET)
    monkeypatch.chdir(company)
    # main() registers alias placeholders on the module-global `app`;
    # re-registering across tests would accumulate duplicates.
    monkeypatch.setattr("coga.cli._register_alias_placeholder", lambda *_: None)
    return company


def test_root_help_runs_without_user(
    clone: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["coga", "--help"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert "Organize agent work" in capsys.readouterr().out


def test_windows_cli_uses_utf8_when_output_is_redirected(clone, monkeypatch):
    import io
    import sys
    from types import SimpleNamespace
    from coga import cli

    def command():
        print("Café → 語")
        print("Café → 語", file=sys.stderr)
        raise SystemExit(0)

    output, errors = io.BytesIO(), io.BytesIO()
    stdout = io.TextIOWrapper(output, encoding="cp1252")
    stderr = io.TextIOWrapper(errors, encoding="cp1252")
    monkeypatch.setattr(cli, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(cli, "app", command)
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", stderr)
    monkeypatch.setattr(sys, "argv", ["coga", "--help"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    stdout.flush()
    stderr.flush()
    assert output.getvalue().decode("utf-8").strip() == "Café → 語"
    assert errors.getvalue().decode("utf-8").strip() == "Café → 語"


def test_command_help_runs_without_user(
    clone: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Even a mutating command's `--help` must work — Typer prints help before
    the command body ever loads config strictly."""
    monkeypatch.setattr("sys.argv", ["coga", "create", "--help"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert "--help" in capsys.readouterr().out


def test_pick_alias_expands_to_megalaunch(
    clone: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`coga pick` is a built-in default alias for `megalaunch --pick`."""
    monkeypatch.setattr("sys.argv", ["coga", "pick"])
    # megalaunch needs a TTY, so the picker exits — but the expansion banner
    # printed before dispatch proves the alias resolves.
    with pytest.raises(SystemExit):
        main()
    assert "→ coga launch bootstrap/megalaunch -- --pick" in capsys.readouterr().err


def test_status_runs_without_user(clone: Path) -> None:
    result = report_cli(["status"])
    assert result.exit_code == 0
    assert "fix-retry-logic" in result.output


def test_show_runs_without_user(clone: Path) -> None:
    result = report_cli(["show", "fix-retry-logic"])
    assert result.exit_code == 0
    assert "fix-retry-logic" in result.output


def test_validate_runs_and_warns_without_user(clone: Path) -> None:
    """`coga validate` still runs on a fresh clone and points at the setup
    step as a warn-level finding instead of dying (or validating clean)."""
    result = CliRunner().invoke(app, ["validate", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    missing_user = [i for i in payload["issues"] if i["kind"] == "missing-user"]
    assert len(missing_user) == 1
    assert missing_user[0]["severity"] == "warn"
    assert "coga.local.toml" in missing_user[0]["message"]


def test_task_validate_runs_and_warns_without_user(clone: Path) -> None:
    result = CliRunner().invoke(
        app, ["validate", "--task", "fix-retry-logic", "--json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    missing_user = [i for i in payload["issues"] if i["kind"] == "missing-user"]
    assert len(missing_user) == 1
    assert missing_user[0]["severity"] == "warn"


def test_usage_runs_without_user(clone: Path) -> None:
    result = report_cli(["usage"])
    assert result.exit_code == 0


def test_skill_status_runs_without_user(clone: Path) -> None:
    result = CliRunner().invoke(app, ["skill", "status"])
    assert result.exit_code == 0
    assert "No `user` set" not in result.output


def test_recurring_list_runs_without_user(clone: Path) -> None:
    result = report_cli(["recurring", "list"])
    assert result.exit_code == 0
    assert "(no recurring templates)" in result.output


def test_mutating_command_still_requires_user(clone: Path) -> None:
    result = CliRunner().invoke(app, ["bump", "fix-retry-logic"])
    assert result.exit_code == 2
    assert "No `user` set in coga.local.toml" in result.output


def test_validate_does_not_warn_when_user_set(clone: Path) -> None:
    _write(clone / "coga.local.toml", 'user = "marc"\n')
    result = CliRunner().invoke(app, ["validate", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert [i for i in payload["issues"] if i["kind"] == "missing-user"] == []


def test_windows_idle_timeout_refusal_keeps_checkout_and_control(
    git_repo, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """`--idle-timeout` refuses on Windows with exit 2 and no state sweep."""
    from coga import launch as launch_module

    ticket = git_repo.coga_os / "tasks" / "windows-agent.md"
    _write(ticket, TICKET)
    git_repo.git("add", ".")
    git_repo.git("commit", "-m", "seed Windows agent ticket")
    git_repo.git("push", "origin", "main")
    git_repo.checkout_branch("feature/keep-this-checkout")
    ticket.write_text(ticket.read_text(encoding="utf-8") + "\nUnpublished Café notes.\n", encoding="utf-8", newline="\n")
    (git_repo.coga_os / "log.md").write_text("Unpublished log.\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "log.md", cwd=git_repo.coga_os)
    monkeypatch.chdir(git_repo.coga_os)
    monkeypatch.setattr("coga.commands.launch._idle_timeout_unavailable", lambda: True)

    def launched(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("the launch service ran")

    monkeypatch.setattr(launch_module, "launch", launched)
    monkeypatch.setattr("sys.argv", ["coga", "launch", "windows-agent", "--idle-timeout", "30"])
    before = {p.relative_to(git_repo.root): p.read_bytes() for p in git_repo.coga_os.rglob("*") if p.is_file()}
    head = git_repo.git("rev-parse", "HEAD")
    control = git_repo.git("rev-parse", "main", cwd=git_repo.origin)
    index = git_repo.git("ls-files", "--stage")

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "--idle-timeout is unavailable on native Windows" in err
    assert "--max-session" in err
    assert "refused before changing state" in err
    assert {p.relative_to(git_repo.root): p.read_bytes() for p in git_repo.coga_os.rglob("*") if p.is_file()} == before
    assert git_repo.git("branch", "--show-current").strip() == "feature/keep-this-checkout"
    assert git_repo.git("rev-parse", "HEAD") == head
    assert git_repo.git("rev-parse", "main", cwd=git_repo.origin) == control
    assert git_repo.git("ls-files", "--stage") == index


def test_idle_timeout_is_not_refused_off_windows(
    clone: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from coga import launch as launch_module
    from coga.launch import LaunchResult

    seen: list[object] = []

    def launched(task, **kwargs):  # type: ignore[no-untyped-def]
        seen.append(kwargs["idle_timeout"])
        return LaunchResult()

    monkeypatch.setattr("coga.commands.launch._idle_timeout_unavailable", lambda: False)
    monkeypatch.setattr(launch_module, "launch", launched)
    result = CliRunner().invoke(app, ["launch", "x", "--idle-timeout", "30"])
    assert result.exit_code == 0, result.output
    assert seen == [30.0]


@pytest.mark.parametrize(
    ("code", "expected"),
    [(7, 7), (0xC000013A, 0xC000013A - 0x100000000), (0xC0000005, 0xC0000005 - 0x100000000)],
)
def test_launch_adapter_keeps_windows_dword_exit_codes(
    clone: Path, monkeypatch: pytest.MonkeyPatch, code: int, expected: int
) -> None:
    """A Windows agent's DWORD exit survives Python 3.11's signed SystemExit."""
    from coga import launch as launch_module
    from coga import oscompat
    from coga.launch import LaunchBail

    monkeypatch.setattr(
        "coga.commands.launch.process_exit_status",
        lambda value: oscompat.process_exit_status(value, windows=True),
    )

    def launched(task, **kwargs):  # type: ignore[no-untyped-def]
        raise LaunchBail(code)

    monkeypatch.setattr(launch_module, "launch", launched)
    result = CliRunner().invoke(app, ["launch", "x"])
    assert result.exit_code == expected
    assert expected & 0xFFFFFFFF == code
