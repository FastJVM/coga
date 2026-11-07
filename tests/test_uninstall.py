"""`coga uninstall` — removes a repo's Coga footprint, the inverse of init."""

from __future__ import annotations

import base64
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from coga import cli as coga_cli
from coga.cli import app
from coga.commands import uninstall as uninstall_cmd
from coga.commands.init import AGENT_GUIDE_TEMPLATE
from coga.commands.update import ensure_host_gitignore


def _seed_footprint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Build the on-disk footprint `coga init` leaves behind, and return the
    host repo root (with cwd + HOME pointed at it)."""
    target = tmp_path / "company"
    coga_os = target / "coga"
    coga_os.mkdir(parents=True)
    (coga_os / "coga.toml").write_text("version = 1\n", encoding="utf-8", newline="\n")
    (coga_os / ".agent-skills").mkdir()

    # Agent skill discovery symlinks.
    for agent in (".claude", ".codex"):
        skills = target / agent / "skills"
        skills.mkdir(parents=True)
        (skills / "coga").symlink_to(coga_os / ".agent-skills")

    # Root orientation guides (shipped content, unmodified).
    (target / "CLAUDE.md").write_text(AGENT_GUIDE_TEMPLATE, encoding="utf-8", newline="\n")
    (target / "AGENTS.md").write_text(AGENT_GUIDE_TEMPLATE, encoding="utf-8", newline="\n")

    # Coga-managed .gitignore block (needs a git dir to be written).
    (target / ".git").mkdir()
    (target / ".gitignore").write_text("node_modules/\n", encoding="utf-8", newline="\n")
    ensure_host_gitignore(target)

    fake_home = tmp_path / "home"
    local_bin = fake_home / ".local" / "bin"
    local_bin.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    monkeypatch.chdir(target)
    return target


def test_uninstall_removes_full_footprint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _seed_footprint(tmp_path, monkeypatch)

    result = CliRunner().invoke(app, ["uninstall", "--yes"])
    assert result.exit_code == 0, result.output

    assert not (target / "coga").exists()
    assert not (target / ".claude").exists()  # pruned once empty
    assert not (target / ".codex").exists()
    assert not (target / "CLAUDE.md").exists()
    assert not (target / "AGENTS.md").exists()
    assert (Path(tmp_path / "home" / ".local" / "bin" / "coga")).exists() is False
    # User .gitignore line survives; managed block is gone.
    gi = (target / ".gitignore").read_text(encoding="utf-8")
    assert "node_modules/" in gi
    assert ".claude/skills/coga" not in gi


def test_uninstall_removes_relocated_contexts_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _seed_footprint(tmp_path, monkeypatch)
    (target / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8", newline="\n")
    (target / "coga" / "coga.toml").write_text(
        'version = 1\n[layout]\ncontexts = "docs/contexts"\n',
        encoding="utf-8", newline="\n",
    )
    context = target / "docs" / "contexts" / "team" / "style" / "SKILL.md"
    context.parent.mkdir(parents=True)
    context.write_text("# Style\n", encoding="utf-8", newline="\n")

    result = CliRunner().invoke(app, ["uninstall", "--yes"])

    assert result.exit_code == 0, result.output
    assert f"remove {Path('docs/contexts')}/ (configured contexts directory)" in result.output
    assert not (target / "docs" / "contexts").exists()
    assert not (target / "coga").exists()


def test_uninstall_broken_config_warns_without_guessing_external_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _seed_footprint(tmp_path, monkeypatch)
    (target / "coga" / "coga.toml").write_text("this is not = valid toml\n", encoding="utf-8", newline="\n")

    result = CliRunner().invoke(app, ["uninstall", "--yes"])

    assert result.exit_code == 0, result.output
    assert "any relocated contexts directory will be left in place" in result.output
    assert not (target / "coga").exists()


def test_uninstall_aborts_on_no_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _seed_footprint(tmp_path, monkeypatch)

    result = CliRunner().invoke(app, ["uninstall"], input="n\n")
    assert result.exit_code == 0, result.output
    assert "Aborted" in result.output
    # Nothing removed.
    assert (target / "coga").is_dir()
    assert (target / "CLAUDE.md").is_file()


def test_uninstall_confirm_yes_via_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _seed_footprint(tmp_path, monkeypatch)

    result = CliRunner().invoke(app, ["uninstall"], input="y\n")
    assert result.exit_code == 0, result.output
    assert not (target / "coga").exists()


def test_uninstall_backs_up_modified_guide(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _seed_footprint(tmp_path, monkeypatch)
    (target / "CLAUDE.md").write_text("# my own edits\n", encoding="utf-8", newline="\n")

    result = CliRunner().invoke(app, ["uninstall", "--yes"])
    assert result.exit_code == 0, result.output

    # Edited guide is preserved under a backup name; the original is gone.
    assert not (target / "CLAUDE.md").exists()
    assert (target / "CLAUDE.md.coga-bak").read_text(encoding="utf-8") == "# my own edits\n"
    # Unmodified guide is removed outright (no backup).
    assert not (target / "AGENTS.md").exists()
    assert not (target / "AGENTS.md.coga-bak").exists()


def test_uninstall_never_touches_the_operators_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Init installs no CLI, so uninstall removes none — including a `coga`
    on PATH that a previous Coga version's shim would have claimed."""
    _seed_footprint(tmp_path, monkeypatch)
    local_bin = tmp_path / "home" / ".local" / "bin"
    other = tmp_path / "other-coga"
    other.write_text("#!/bin/sh\n", encoding="utf-8", newline="\n")
    (local_bin / "coga").symlink_to(other)

    result = CliRunner().invoke(app, ["uninstall", "--yes"])
    assert result.exit_code == 0, result.output
    assert (local_bin / "coga").is_symlink()


def test_uninstall_without_purge_prints_pip_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_footprint(tmp_path, monkeypatch)

    result = CliRunner().invoke(app, ["uninstall", "--yes"])
    assert result.exit_code == 0, result.output
    assert "left installed" in result.output
    assert "uv tool uninstall coga" in result.output
    assert "pipx uninstall coga" in result.output


def test_uninstall_purge_runs_pipx_for_pipx_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_footprint(tmp_path, monkeypatch)

    calls: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(uninstall_cmd.shutil, "which", lambda name: "/usr/bin/pipx")
    monkeypatch.setattr(uninstall_cmd.subprocess, "run", fake_run)
    monkeypatch.setattr(
        uninstall_cmd, "running_cli_location", lambda: ("pipx", Path("/x"))
    )

    result = CliRunner().invoke(app, ["uninstall", "--yes", "--purge"])
    assert result.exit_code == 0, result.output
    assert calls == [["/usr/bin/pipx", "uninstall", "coga"]]
    assert "Uninstalled `coga` via pipx" in result.output


def test_uninstall_purge_runs_uv_tool_for_uv_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A `uv tool install coga` venv has no pip; --purge must go through uv."""
    _seed_footprint(tmp_path, monkeypatch)

    calls: list[list[str]] = []
    envs: list[dict[str, str] | None] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        envs.append(kwargs.get("env"))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    # A nondefault tools dir that the current environment no longer names:
    # uv must still be pointed at the dir owning the running venv.
    monkeypatch.setenv("UV_TOOL_DIR", "/somewhere/else")
    monkeypatch.setattr(uninstall_cmd.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(uninstall_cmd.subprocess, "run", fake_run)
    monkeypatch.setattr(
        uninstall_cmd,
        "running_cli_location",
        lambda: ("uv", Path("/opt/uv tools/coga")),
    )

    result = CliRunner().invoke(app, ["uninstall", "--yes", "--purge"])
    assert result.exit_code == 0, result.output
    assert calls == [["/usr/bin/uv", "tool", "uninstall", "coga"]]
    assert envs[0] is not None
    assert envs[0]["UV_TOOL_DIR"] == str(Path("/opt/uv tools"))
    assert "Uninstalled `coga` via uv" in result.output
    assert "-m pip" not in result.output


def _native_uv_hint(tool_dir: str) -> str:
    """The uv recovery line this host's native shell expects."""
    if os.name == "nt":
        escaped = tool_dir.replace("'", "''")
        return f"$env:UV_TOOL_DIR='{escaped}'; uv tool uninstall coga"
    return f"UV_TOOL_DIR={shlex.quote(tool_dir)} uv tool uninstall coga"


def test_uninstall_purge_uv_failure_prints_command_with_tool_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_footprint(tmp_path, monkeypatch)

    def fake_run(cmd, *args, **kwargs):
        return SimpleNamespace(returncode=2, stdout="", stderr="boom")

    monkeypatch.setattr(uninstall_cmd.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(uninstall_cmd.subprocess, "run", fake_run)
    monkeypatch.setattr(
        uninstall_cmd,
        "running_cli_location",
        lambda: ("uv", Path("/opt/uv tools/coga")),
    )

    result = CliRunner().invoke(app, ["uninstall", "--yes", "--purge"])
    assert result.exit_code == 0, result.output
    assert "uv uninstall failed" in result.output
    assert _native_uv_hint(str(Path("/opt/uv tools"))) in result.output
    assert ("in PowerShell" in result.output) == (os.name == "nt")


def test_uninstall_purge_uv_install_without_uv_prints_uv_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_footprint(tmp_path, monkeypatch)

    def fake_run(cmd, *args, **kwargs):
        raise AssertionError(f"unexpected subprocess: {cmd}")

    monkeypatch.setattr(uninstall_cmd.shutil, "which", lambda name: None)
    monkeypatch.setattr(uninstall_cmd.subprocess, "run", fake_run)
    monkeypatch.setattr(
        uninstall_cmd, "running_cli_location", lambda: ("uv", Path("/x"))
    )

    result = CliRunner().invoke(app, ["uninstall", "--yes", "--purge"])
    assert result.exit_code == 0, result.output
    assert "Couldn't find uv on PATH" in result.output
    assert _native_uv_hint(str(Path("/"))) in result.output
    assert ("in PowerShell" in result.output) == (os.name == "nt")
    assert "pip uninstall" not in result.output


@pytest.mark.parametrize(
    ("env", "windows", "expected"),
    [
        ({}, False, "pipx uninstall coga"),
        ({}, True, "pipx uninstall coga"),
        ({"UV_TOOL_DIR": "/opt/uv"}, False, "UV_TOOL_DIR=/opt/uv uv tool uninstall coga"),
        (
            {"UV_TOOL_DIR": "/opt/uv tools"},
            False,
            "UV_TOOL_DIR='/opt/uv tools' uv tool uninstall coga",
        ),
        (
            {"UV_TOOL_DIR": "/home/o'brien/uv"},
            False,
            "UV_TOOL_DIR='/home/o'\"'\"'brien/uv' uv tool uninstall coga",
        ),
        (
            {"UV_TOOL_DIR": "C:\\Users\\O'Brien\\uv tools"},
            True,
            "$env:UV_TOOL_DIR='C:\\Users\\O''Brien\\uv tools'; uv tool uninstall coga",
        ),
        (
            # Expanding/statement metacharacters stay literal inside '...';
            # typographic single quotes are delimiters too and are doubled.
            {"UV_TOOL_DIR": "C:\\$HOME `n & ; \u00e9\u2018x\u2019"},
            True,
            "$env:UV_TOOL_DIR='C:\\$HOME `n & ; \u00e9\u2018\u2018x\u2019\u2019'; "
            "uv tool uninstall coga",
        ),
        (
            {"A": "1", "B": "2"},
            True,
            "$env:A='1'; $env:B='2'; uv tool uninstall coga",
        ),
        ({"A": "1", "B": "2"}, False, "A=1 B=2 uv tool uninstall coga"),
    ],
)
def test_format_tool_command_renders_platform_syntax(
    env: dict[str, str], windows: bool, expected: str
) -> None:
    tool, sub = ("pipx", ["uninstall"]) if not env else ("uv", ["tool", "uninstall"])
    before = dict(env)
    environ_before = dict(os.environ)
    assert uninstall_cmd._format_tool_command(tool, sub, env, windows=windows) == expected
    assert env == before
    assert dict(os.environ) == environ_before


@pytest.mark.parametrize("windows", [False, True])
@pytest.mark.parametrize("found", [False, True])
def test_uninstall_via_tool_hints_use_selected_platform(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    windows: bool,
    found: bool,
) -> None:
    """Progress and both recovery paths share one rendering; execution is
    unchanged whichever syntax is displayed."""
    calls: list[tuple[list[str], dict | None]] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append((cmd, kwargs.get("env")))
        return SimpleNamespace(returncode=2, stdout="", stderr="boom")

    monkeypatch.setattr(uninstall_cmd, "_native_windows", lambda: windows)
    monkeypatch.setattr(
        uninstall_cmd.shutil, "which", lambda name: "/bin/uv" if found else None
    )
    monkeypatch.setattr(uninstall_cmd.subprocess, "run", fake_run)
    overrides = {"UV_TOOL_DIR": "/o'b/uv tools"}

    uninstall_cmd._uninstall_via_tool("uv", ["tool", "uninstall"], env=overrides)
    out = capsys.readouterr().out

    if windows:
        hint = "$env:UV_TOOL_DIR='/o''b/uv tools'; uv tool uninstall coga"
        label = "by hand in PowerShell:"
    else:
        hint = "UV_TOOL_DIR='/o'\"'\"'b/uv tools' uv tool uninstall coga"
        label = "by hand:"
    assert overrides == {"UV_TOOL_DIR": "/o'b/uv tools"}
    if found:
        assert out == (
            f"Uninstalling global package ({hint})…\n"
            f"uv uninstall failed — remove it {label}\n    {hint}\nboom\n"
        )
        assert len(calls) == 1
        cmd, env = calls[0]
        assert cmd == ["/bin/uv", "tool", "uninstall", "coga"]
        assert env == {**os.environ, **overrides}
    else:
        assert out == (
            f"Couldn't find uv on PATH. Remove the global package {label}\n"
            f"    {hint}\n"
            f"(installed however you set Coga up — see {uninstall_cmd.COGA_REPO_URL}).\n"
        )
        assert calls == []


@pytest.mark.parametrize("windows", [False, True])
def test_uninstall_via_tool_without_overrides_is_unchanged(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    windows: bool,
) -> None:
    calls: list[tuple[list[str], dict | None]] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append((cmd, kwargs.get("env")))
        return SimpleNamespace(returncode=1, stdout="nope", stderr="")

    monkeypatch.setattr(uninstall_cmd, "_native_windows", lambda: windows)
    monkeypatch.setattr(uninstall_cmd.shutil, "which", lambda name: "/bin/pipx")
    monkeypatch.setattr(uninstall_cmd.subprocess, "run", fake_run)

    uninstall_cmd._uninstall_via_tool("pipx", ["uninstall"])

    assert capsys.readouterr().out == (
        "Uninstalling global package (pipx uninstall coga)…\n"
        "pipx uninstall failed — remove it by hand:\n"
        "    pipx uninstall coga\n"
        "nope\n"
    )
    assert calls == [(["/bin/pipx", "uninstall", "coga"], None)]


@pytest.mark.skipif(os.name != "nt", reason="Requires native Windows PowerShell")
def test_windows_uv_hint_runs_in_powershell(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Paste the emitted hint into PowerShell with a stub `uv` function (never
    a real uninstaller) and check the literal value and arguments it sees."""
    tool_dir = "C:\\Users\\O'Brien\\uv tools $HOME `n & ; \u00e9 \u2019x\u2018 \u65e5"

    monkeypatch.setattr(uninstall_cmd.shutil, "which", lambda name: None)
    uninstall_cmd._uninstall_via_tool(
        "uv", ["tool", "uninstall"], env={"UV_TOOL_DIR": tool_dir}
    )
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert "in PowerShell" in lines[0]
    hint = lines[1].removeprefix("    ")

    result_path = tmp_path / "uv-stub.json"
    stub_path = str(result_path).replace("'", "''")
    script = (
        "$ErrorActionPreference = 'Stop'\n"
        "function uv {\n"
        "  $data = @{ dir = $env:UV_TOOL_DIR; args = @($args) } | ConvertTo-Json -Compress\n"
        f"  [IO.File]::WriteAllText('{stub_path}', $data, (New-Object Text.UTF8Encoding $false))\n"
        "}\n"
        f"{hint}\n"
    )
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-EncodedCommand", encoded],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    seen = json.loads(result_path.read_text(encoding="utf-8-sig"))
    assert seen["dir"] == tool_dir
    assert seen["args"] == ["tool", "uninstall", "coga"]


def test_uninstall_purge_runs_pip_for_other_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_footprint(tmp_path, monkeypatch)

    calls: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(uninstall_cmd.sys, "executable", "/venv/bin/python")
    monkeypatch.setattr(uninstall_cmd.subprocess, "run", fake_run)
    monkeypatch.setattr(
        uninstall_cmd, "running_cli_location", lambda: ("other", Path("/x"))
    )

    result = CliRunner().invoke(app, ["uninstall", "--yes", "--purge"])
    assert result.exit_code == 0, result.output
    assert calls == [
        ["/venv/bin/python", "-m", "pip", "uninstall", "-y", "coga"]
    ]
    assert "Uninstalled `coga` via pip" in result.output


def test_uninstall_errors_if_coga_os_remains(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _seed_footprint(tmp_path, monkeypatch)

    monkeypatch.setattr(uninstall_cmd.shutil, "rmtree", lambda path: None)

    result = CliRunner().invoke(app, ["uninstall", "--yes"])
    assert result.exit_code == 2
    assert "path still exists" in result.output
    assert (target / "coga").is_dir()
    assert "Coga uninstalled" not in result.output


def test_main_uninstall_ignores_legacy_uninstall_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target = _seed_footprint(tmp_path, monkeypatch)
    (target / "coga" / "coga.local.toml").write_text('user = "me"\n', encoding="utf-8", newline="\n")
    (target / "coga" / "coga.toml").write_text(
        'version = 1\n[aliases]\nuninstall = "status"\n',
        encoding="utf-8", newline="\n",
    )
    monkeypatch.setattr(sys, "argv", ["coga", "uninstall", "--yes"])

    with pytest.raises(SystemExit) as exc:
        coga_cli.main()

    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "ignoring legacy alias 'uninstall'" in captured.err
    assert not (target / "coga").exists()


def test_uninstall_outside_repo_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    empty = tmp_path / "nowhere"
    empty.mkdir()
    monkeypatch.chdir(empty)

    result = CliRunner().invoke(app, ["uninstall", "--yes"])
    assert result.exit_code == 2
    assert "No coga.toml" in result.output
