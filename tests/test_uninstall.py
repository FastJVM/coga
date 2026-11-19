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


# --- running_cli_location --------------------------------


def _stub_executable_in(venv: Path) -> Path:
    """Create a venv-shaped tree with `bin/python` and return the python path."""
    (venv / "bin").mkdir(parents=True, exist_ok=True)
    py = venv / "bin" / "python"
    py.write_text("#!/bin/sh\n", encoding="utf-8", newline="\n")
    py.chmod(0o755)
    return py


def test_running_cli_location_detects_pipx(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    coga_os = tmp_path / "project" / "coga"
    coga_os.mkdir(parents=True)
    pipx_venv = tmp_path / "home" / ".local" / "share" / "pipx" / "venvs" / "coga"
    py = _stub_executable_in(pipx_venv)
    (pipx_venv / "pipx_metadata.json").write_text("{}\n", encoding="utf-8", newline="\n")
    monkeypatch.setattr(uninstall_cmd.sys, "executable", str(py))

    kind, where = uninstall_cmd.running_cli_location()
    assert kind == "pipx"
    assert where == pipx_venv.absolute()


def test_running_cli_location_detects_uv_tool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    uv_venv = tmp_path / "home" / ".local" / "share" / "uv" / "tools" / "coga"
    py = _stub_executable_in(uv_venv)
    (uv_venv / "uv-receipt.toml").write_text("[tool]\n", encoding="utf-8", newline="\n")
    monkeypatch.setattr(uninstall_cmd.sys, "executable", str(py))

    kind, where = uninstall_cmd.running_cli_location()
    assert kind == "uv"
    assert where == uv_venv.absolute()


def test_running_cli_location_falls_through_to_other(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    coga_os = tmp_path / "project" / "coga"
    coga_os.mkdir(parents=True)
    other_venv = tmp_path / "some-other-venv"
    py = _stub_executable_in(other_venv)
    monkeypatch.setattr(uninstall_cmd.sys, "executable", str(py))

    kind, where = uninstall_cmd.running_cli_location()
    assert kind == "other"
    assert where == other_venv.absolute()


def test_running_cli_location_detects_pipx_when_python_is_a_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression for the macOS-Homebrew pipx case.

    pipx creates `<venv>/bin/python` as a symlink to whatever Python it was
    invoked with (Homebrew, pyenv, system). Following the symlink lands in
    the host Python's framework dir, which doesn't have `pipx_metadata.json`.
    Detection must work off the unresolved venv path.
    """
    coga_os = tmp_path / "project" / "coga"
    coga_os.mkdir(parents=True)

    # Mimic Homebrew's framework Python at a totally unrelated path.
    host_py_dir = tmp_path / "opt" / "homebrew" / "Cellar" / "python@3.14" / "bin"
    host_py_dir.mkdir(parents=True)
    host_py = host_py_dir / "python3.14"
    host_py.write_text("#!/bin/sh\n", encoding="utf-8", newline="\n")
    host_py.chmod(0o755)

    pipx_venv = tmp_path / "home" / ".local" / "pipx" / "venvs" / "coga"
    (pipx_venv / "bin").mkdir(parents=True)
    (pipx_venv / "pipx_metadata.json").write_text("{}\n", encoding="utf-8", newline="\n")
    pipx_python = pipx_venv / "bin" / "python"
    pipx_python.symlink_to(host_py)
    monkeypatch.setattr(uninstall_cmd.sys, "executable", str(pipx_python))

    kind, where = uninstall_cmd.running_cli_location()
    assert kind == "pipx", (
        "symlink resolution would land in homebrew Cellar; detection must "
        "stay on the unresolved venv path so pipx_metadata.json is found"
    )
    assert where == pipx_venv.absolute()


@pytest.mark.parametrize(
    "broken", ["shared", "local", "shared-bytes", "local-bytes", "alias", "absent"],
)
def test_main_uninstall_recovers_without_launch_or_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str], broken: str,
) -> None:
    target = _seed_footprint(tmp_path, monkeypatch)
    coga_os = target / "coga"
    # This fixture has no definitions, configured user or agent.
    if broken == "shared":
        (coga_os / "coga.toml").write_text("bad = [", encoding="utf-8")
    elif broken == "local":
        (coga_os / "coga.local.toml").write_text("bad = [", encoding="utf-8")
    elif broken == "shared-bytes":
        (coga_os / "coga.toml").write_bytes(b"version = 1\n# caf\xe9\n")
    elif broken == "local-bytes":
        (coga_os / "coga.local.toml").write_bytes(b'user = "caf\xe9"\n')
    elif broken == "alias":
        (coga_os / "coga.toml").write_text(
            'version = 1\n[aliases]\nbad = "nonexistent-command"\n', encoding="utf-8",
        )
    monkeypatch.setattr(sys, "argv", ["coga", "uninstall", "--yes"])
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)

    def forbidden(*args, **kwargs):
        raise AssertionError("uninstall crossed recovery admission/teardown boundary")

    for seam in (
        "coga.cli._validate_aliases", "coga.cli._sweep_coga_state",
        "coga.git.publish", "coga.git.refresh", "coga.logfile.append_log",
        "coga.notification.post", "coga.notification.notify",
        "coga.compose.compose_prompt", "coga.usage.append_record",
    ):
        monkeypatch.setattr(seam, forbidden)
    with pytest.raises(SystemExit) as exc:
        coga_cli.main()
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "Uninstalling Coga from" in captured.out
    assert "Coga uninstalled" in captured.out
    assert not coga_os.exists()


def test_uninstall_confirmation_defaults_to_no(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _seed_footprint(tmp_path, monkeypatch)
    before = {p.relative_to(target): p.read_bytes() for p in target.rglob("*") if p.is_file()}
    result = CliRunner().invoke(app, ["uninstall"], input="\n")
    assert result.exit_code == 0, result.output
    assert "Uninstalling Coga from" in result.stdout
    assert "[y/N]" in result.stdout
    assert "Aborted" in result.stdout
    assert {p.relative_to(target): p.read_bytes() for p in target.rglob("*") if p.is_file()} == before
    assert (target / ".claude" / "skills" / "coga").is_symlink()


@pytest.mark.parametrize("failure", ["raises", "remains"])
def test_uninstall_external_context_failure_keeps_config_and_footprint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str,
) -> None:
    target = _seed_footprint(tmp_path, monkeypatch)
    (target / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    config_path = target / "coga" / "coga.toml"
    config_path.write_text('version = 1\n[layout]\ncontexts = "docs/contexts"\n', encoding="utf-8")
    contexts = target / "docs" / "contexts"
    contexts.mkdir(parents=True)
    (contexts / "keep.txt").write_text("operator context", encoding="utf-8")
    calls = []

    def refuse(path):
        calls.append(path)
        if failure == "raises":
            raise PermissionError("fake external-root refusal")

    monkeypatch.setattr(uninstall_cmd.shutil, "rmtree", refuse)
    result = CliRunner().invoke(app, ["uninstall", "--yes"])
    assert result.exit_code == 2, result.output
    assert "Failed to remove" in result.stderr
    assert calls == [contexts.resolve()]
    assert config_path.is_file()
    assert (contexts / "keep.txt").read_text(encoding="utf-8") == "operator context"
    assert (target / "AGENTS.md").is_file()
    assert "Coga uninstalled" not in result.stdout


def test_uninstall_unsafe_context_root_warns_and_leaves_external_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _seed_footprint(tmp_path, monkeypatch)
    (target / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    keep = outside / "keep.txt"
    keep.write_text("outside repo", encoding="utf-8")
    (target / "coga" / "coga.toml").write_text(
        'version = 1\n[layout]\ncontexts = "../outside"\n', encoding="utf-8",
    )
    result = CliRunner().invoke(app, ["uninstall", "--yes"])
    assert result.exit_code == 0, result.output
    assert "any relocated contexts directory will be left in place" in result.stdout
    assert keep.read_text(encoding="utf-8") == "outside repo"
    assert not (target / "coga").exists()


def test_uninstall_refuses_root_layout_without_removal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "root-layout"
    target.mkdir()
    config_path = target / "coga.toml"
    config_path.write_text("version = 1\n", encoding="utf-8")
    monkeypatch.chdir(target)
    result = CliRunner().invoke(app, ["uninstall", "--yes"])
    assert result.exit_code == 2
    assert "Refusing to guess" in result.stderr
    assert config_path.read_text(encoding="utf-8") == "version = 1\n"


def test_uninstall_prunes_only_empty_agent_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _seed_footprint(tmp_path, monkeypatch)
    keep = target / ".claude" / "skills" / "other.md"
    keep.write_text("another skill", encoding="utf-8")
    result = CliRunner().invoke(app, ["uninstall", "--yes"])
    assert result.exit_code == 0, result.output
    assert keep.read_text(encoding="utf-8") == "another skill"
    assert not (keep.parent / "coga").is_symlink()
    assert not (target / ".codex").exists()


@pytest.mark.parametrize("kind", ["pipx", "other"])
def test_uninstall_purge_failure_reports_matching_manual_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str,
) -> None:
    _seed_footprint(tmp_path, monkeypatch)
    monkeypatch.setattr(uninstall_cmd, "running_cli_location", lambda: (kind, Path("/fake/venv")))
    monkeypatch.setattr(uninstall_cmd.shutil, "which", lambda _: "/fake/pipx")
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        return SimpleNamespace(returncode=1, stdout="", stderr="fake purge failure")

    monkeypatch.setattr(uninstall_cmd.subprocess, "run", fake_run)
    result = CliRunner().invoke(app, ["uninstall", "--yes", "--purge"])
    assert result.exit_code == 0, result.output
    assert "fake purge failure" in result.stdout
    if kind == "pipx":
        assert calls == [["/fake/pipx", "uninstall", "coga"]]
        assert "pipx uninstall coga" in result.stdout
    else:
        assert calls == [[sys.executable, "-m", "pip", "uninstall", "-y", "coga"]]
        assert f"{sys.executable} -m pip uninstall coga" in result.stdout


@pytest.mark.parametrize("block", ["missing", "truncated", "complete"])
def test_remove_host_gitignore_preserves_user_rules_and_is_idempotent(
    tmp_path: Path, block: str,
) -> None:
    from coga.commands.update import HOST_GITIGNORE_BEGIN, HOST_GITIGNORE_END

    user_rules = "node_modules/\ncustom/\n"
    text = user_rules
    if block != "missing":
        text += f"\n{HOST_GITIGNORE_BEGIN}\n.coga/\n"
    if block == "complete":
        text += f"{HOST_GITIGNORE_END}\nkeep-after/\n"
    path = tmp_path / ".gitignore"
    path.write_text(text, encoding="utf-8")
    assert uninstall_cmd.remove_host_gitignore(tmp_path) == (block != "missing")
    expected = user_rules + ("\nkeep-after/\n" if block == "complete" else "")
    assert path.read_text(encoding="utf-8") == expected
    assert not uninstall_cmd.remove_host_gitignore(tmp_path)
