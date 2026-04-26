"""`relay init` — scaffolds a relay-os/ from upstream, or refreshes one with --update."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.commands import init as init_cmd
from relay.commands import update as update_cmd


EXPECTED_FILES = {
    "relay-os/.gitignore",
    "relay-os/relay.toml",
    "relay-os/rules.md",
    "relay-os/context.md",
    "relay-os/counter",
    "relay-os/scripts/cron.sh",
    "relay-os/contexts/_template/SKILL.md",
    "relay-os/skills/_template/SKILL.md",
    "relay-os/workflows/_template.md",
    "relay-os/recurring/_template.md",
    "relay-os/tasks/_template/ticket.md",
}


def _seed_fake_clone(clone_dir: Path) -> None:
    """Mimic the layout of the real repo: templates + CLI source."""
    templates = clone_dir / update_cmd.TEMPLATE_SUBPATH
    templates.mkdir(parents=True)
    (templates / ".gitignore").write_text("relay.local.toml\n.relay/\n**/task.lock\n")
    (templates / "relay.toml").write_text("version = 1\n")
    (templates / "rules.md").write_text("rules\n")
    (templates / "context.md").write_text("context\n")
    (templates / "counter").write_text("0\n")
    (templates / "scripts").mkdir()
    (templates / "scripts" / "cron.sh").write_text("#!/bin/sh\n")
    for kind, fname in [
        ("contexts", "_template/SKILL.md"),
        ("skills", "_template/SKILL.md"),
        ("tasks", "_template/ticket.md"),
        ("workflows", "_template.md"),
        ("recurring", "_template.md"),
    ]:
        path = templates / kind / fname
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {kind} template\n")

    cli_src = clone_dir / update_cmd.CLI_SRC_SUBPATH
    cli_src.mkdir(parents=True, exist_ok=True)
    (cli_src / "__init__.py").write_text("")
    (cli_src / "cli.py").write_text("# fake cli\n")

    (clone_dir / "pyproject.toml").write_text("[project]\nname = 'relay-os'\n")
    (clone_dir / "requirements.txt").write_text("typer>=0.12\nPyYAML>=6\n")


FAKE_SHA = "deadbeefcafe1234567890abcdef1234567890ab"


@pytest.fixture
def fake_clone(monkeypatch: pytest.MonkeyPatch):
    real_run = subprocess.run

    def fake_run(cmd, **kwargs):
        if cmd[:2] == ["git", "clone"]:
            _seed_fake_clone(Path(cmd[-1]))
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[:2] == ["git", "-C"] and cmd[3:] == ["rev-parse", "HEAD"]:
            # Only fake the upstream-clone rev-parse; let local-repo rev-parse
            # (used by the post-init commit step) run for real.
            if "/repo" in cmd[2] and "relay-init-" in cmd[2]:
                return subprocess.CompletedProcess(cmd, 0, stdout=f"{FAKE_SHA}\n", stderr="")
        return real_run(cmd, **kwargs)

    monkeypatch.setattr(update_cmd.subprocess, "run", fake_run)


@pytest.fixture
def fake_venv(monkeypatch: pytest.MonkeyPatch):
    """Stub out `install_venv` — actual pip-install is too slow + needs network for tests."""
    calls: list[Path] = []

    def fake_install(relay_os: Path) -> Path:
        calls.append(relay_os)
        venv_bin = relay_os / ".relay" / ".venv" / "bin"
        venv_bin.mkdir(parents=True, exist_ok=True)
        # Stand in for the pip-generated console script the wrapper symlinks to.
        relay_script = venv_bin / "relay"
        relay_script.write_text("#!/bin/sh\necho fake venv relay\n")
        relay_script.chmod(0o755)
        return relay_script.parent.parent

    monkeypatch.setattr(init_cmd, "install_venv", fake_install)
    return calls


# --- fresh init ---------------------------------------------------------------


def test_init_into_empty_dir(tmp_path: Path, fake_clone, fake_venv) -> None:
    target = tmp_path / "company"
    target.mkdir()

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output

    for rel in EXPECTED_FILES:
        assert (target / rel).is_file(), f"missing {rel}"

    assert (target / "relay-os" / "counter").read_text().strip() == "0"
    assert "version = 1" in (target / "relay-os" / "relay.toml").read_text()


def test_init_vendors_cli_and_links_wrapper_to_venv(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "company"
    monkeypatch.setenv("PATH", "")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output

    assert (target / "relay-os" / ".relay" / "src" / "relay" / "cli.py").is_file()
    assert (target / "relay-os" / ".relay" / "pyproject.toml").is_file()
    assert (target / "relay-os" / ".relay" / "requirements.txt").is_file()
    assert fake_venv == [target / "relay-os"]  # install_venv called once

    wrapper = target / "relay-os" / ".relay" / "bin" / "relay"
    venv_relay = target / "relay-os" / ".relay" / ".venv" / "bin" / "relay"
    assert wrapper.is_symlink()
    # Relative symlink so the repo is portable.
    assert Path(wrapper.readlink()) == Path("..") / ".venv" / "bin" / "relay"
    assert wrapper.resolve() == venv_relay.resolve()

    assert "Add the bin dir to your PATH" in result.output


def test_init_writes_local_toml_placeholder(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "company"
    monkeypatch.setenv("PATH", "")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output

    local_toml = target / "relay-os" / "relay.local.toml"
    assert local_toml.is_file()
    text = local_toml.read_text()
    assert 'user = ""' in text
    assert "[paths]" in text  # commented example present


def test_init_installs_shim_when_local_bin_on_path(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_home = tmp_path / "home"
    local_bin = fake_home / ".local" / "bin"
    local_bin.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("PATH", f"{local_bin}:/usr/bin")

    target = tmp_path / "company"
    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output

    shim = local_bin / "relay"
    assert shim.is_symlink()
    expected = (target / "relay-os" / ".relay" / ".venv" / "bin" / "relay").resolve()
    assert shim.resolve() == expected
    assert "is on your PATH via" in result.output
    assert "Add the bin dir to your PATH" not in result.output


def test_init_skips_shim_when_target_exists(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_home = tmp_path / "home"
    local_bin = fake_home / ".local" / "bin"
    local_bin.mkdir(parents=True)
    (local_bin / "relay").write_text("# pre-existing\n")
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("PATH", f"{local_bin}:/usr/bin")

    target = tmp_path / "company"
    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output

    # Pre-existing file untouched, instructions fall back to PATH export.
    assert (local_bin / "relay").read_text() == "# pre-existing\n"
    assert "Add the bin dir to your PATH" in result.output


def test_init_into_non_empty_dir_is_fine(tmp_path: Path, fake_clone, fake_venv) -> None:
    target = tmp_path / "existing-repo"
    target.mkdir()
    (target / "README.md").write_text("hi")
    (target / "src").mkdir()

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output
    assert (target / "relay-os" / "relay.toml").is_file()
    assert (target / "README.md").read_text() == "hi"


def test_init_refuses_existing_relay_os(tmp_path: Path, fake_clone, fake_venv) -> None:
    target = tmp_path / "occupied"
    target.mkdir()
    (target / "relay-os").mkdir()

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 2
    assert "use `relay init --update`" in result.output


def test_init_creates_missing_dir(tmp_path: Path, fake_clone, fake_venv) -> None:
    target = tmp_path / "fresh"
    assert not target.exists()

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output
    assert (target / "relay-os" / "relay.toml").is_file()


# --- --update mode ------------------------------------------------------------


def _seed_local_relay_os(root: Path) -> Path:
    """Stand in for a previously-init'd repo."""
    relay_os = root / "relay-os"
    (relay_os / "skills" / "_template").mkdir(parents=True)
    (relay_os / "tasks" / "_template").mkdir(parents=True)
    (relay_os / "skills" / "_template" / "SKILL.md").write_text("OLD skill template\n")
    (relay_os / "tasks" / "_template" / "ticket.md").write_text("OLD ticket template\n")
    (relay_os / "skills" / "myteam" / "real-skill").mkdir(parents=True)
    (relay_os / "skills" / "myteam" / "real-skill" / "SKILL.md").write_text("user content\n")
    (relay_os / "relay.toml").write_text("version = 1\n")
    (relay_os / "rules.md").write_text("user-edited rules\n")

    vendored = relay_os / ".relay" / "src" / "relay"
    vendored.mkdir(parents=True)
    (vendored / "cli.py").write_text("# OLD vendored cli\n")
    return relay_os


def _seed_fake_upstream_for_update(clone_dir: Path) -> None:
    templates = clone_dir / update_cmd.TEMPLATE_SUBPATH
    (templates / "skills" / "_template").mkdir(parents=True)
    (templates / "tasks" / "_template").mkdir(parents=True)
    (templates / "skills" / "_template" / "SKILL.md").write_text("NEW skill template\n")
    (templates / "tasks" / "_template" / "ticket.md").write_text("NEW ticket template\n")
    (templates / "rules.md").write_text("NEW upstream rules — should NOT be copied (no _ prefix)\n")

    cli_src = clone_dir / update_cmd.CLI_SRC_SUBPATH
    cli_src.mkdir(parents=True, exist_ok=True)
    (cli_src / "cli.py").write_text("# NEW vendored cli\n")

    (clone_dir / "pyproject.toml").write_text("[project]\nname = 'relay-os'\n")
    (clone_dir / "requirements.txt").write_text("typer>=0.12\nPyYAML>=6\n")


def test_init_update_refreshes_cli_and_underscore_templates(
    tmp_path: Path, fake_venv, monkeypatch: pytest.MonkeyPatch,
) -> None:
    relay_os = _seed_local_relay_os(tmp_path)
    monkeypatch.chdir(relay_os)

    real_run = subprocess.run

    def fake_run(cmd, **kwargs):
        if cmd[:2] == ["git", "clone"]:
            _seed_fake_upstream_for_update(Path(cmd[-1]))
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if (
            cmd[:2] == ["git", "-C"]
            and cmd[3:] == ["rev-parse", "HEAD"]
            and "relay-init-update-" in cmd[2]
        ):
            return subprocess.CompletedProcess(cmd, 0, stdout=f"{FAKE_SHA}\n", stderr="")
        return real_run(cmd, **kwargs)

    monkeypatch.setattr(update_cmd.subprocess, "run", fake_run)

    result = CliRunner().invoke(app, ["init", "--update"])
    assert result.exit_code == 0, result.output

    assert (relay_os / "skills" / "_template" / "SKILL.md").read_text() == "NEW skill template\n"
    assert (relay_os / "tasks" / "_template" / "ticket.md").read_text() == "NEW ticket template\n"
    # User-edited content untouched.
    assert (relay_os / "skills" / "myteam" / "real-skill" / "SKILL.md").read_text() == "user content\n"
    assert (relay_os / "rules.md").read_text() == "user-edited rules\n"

    assert (relay_os / ".relay" / "src" / "relay" / "cli.py").read_text() == "# NEW vendored cli\n"
    assert (relay_os / ".relay" / "pyproject.toml").is_file()
    assert (relay_os / ".relay" / "requirements.txt").is_file()
    assert fake_venv == [relay_os]  # install_venv called once

    wrapper = relay_os / ".relay" / "bin" / "relay"
    assert wrapper.is_symlink()
    assert wrapper.resolve() == (relay_os / ".relay" / ".venv" / "bin" / "relay").resolve()

    pin = relay_os / ".relay" / "RELAY_PIN"
    assert pin.is_file()
    assert FAKE_SHA in pin.read_text()
    assert f"Pinned to upstream {FAKE_SHA[:12]}" in result.output


def test_init_commits_relay_os_when_target_is_git_repo(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "company"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    subprocess.run(["git", "-C", str(target), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(target), "config", "user.name", "T"], check=True)
    monkeypatch.setenv("PATH", os.environ["PATH"])  # need git on PATH
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output
    assert "Committed relay-os/ as" in result.output

    log = subprocess.run(
        ["git", "-C", str(target), "log", "--oneline"],
        capture_output=True, text=True, check=True,
    )
    assert "Scaffold relay-os via `relay init`" in log.stdout

    # `.relay/` and `relay.local.toml` are gitignored — they should not be tracked.
    tracked = subprocess.run(
        ["git", "-C", str(target), "ls-files", "relay-os"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    assert any(p.startswith("relay-os/relay.toml") for p in tracked)
    assert not any(".relay/" in p for p in tracked)
    assert not any(p.endswith("relay.local.toml") for p in tracked)


def test_init_skips_commit_when_target_is_not_git_repo(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "company"
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output
    assert "Committed relay-os/" not in result.output


def test_init_writes_pin_file(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "company"
    monkeypatch.setenv("PATH", "")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output

    pin = target / "relay-os" / ".relay" / "RELAY_PIN"
    assert pin.is_file()
    lines = pin.read_text().splitlines()
    assert lines[0] == update_cmd.RELAY_REPO_URL
    assert lines[1] == FAKE_SHA
    assert f"Pinned to upstream {FAKE_SHA[:12]}" in result.output


def test_version_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`relay --version` prints the package version and (when present) the pin."""
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0, result.output
    assert "relay " in result.output
    # In test env (no pinned relay-os/), pin line is absent.
    assert "vendored from upstream" not in result.output


def test_version_flag_includes_pin_when_in_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    relay_os = tmp_path / "relay-os"
    (relay_os / ".relay").mkdir(parents=True)
    (relay_os / "relay.toml").write_text("version = 1\n")
    (relay_os / ".relay" / "RELAY_PIN").write_text(
        f"{update_cmd.RELAY_REPO_URL}\n{FAKE_SHA}\n"
    )
    monkeypatch.chdir(relay_os)

    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0, result.output
    assert FAKE_SHA[:12] in result.output


def test_init_update_fails_loudly_if_clone_fails(
    tmp_path: Path, fake_venv, monkeypatch: pytest.MonkeyPatch,
) -> None:
    relay_os = _seed_local_relay_os(tmp_path)
    monkeypatch.chdir(relay_os)

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 128, stdout="", stderr="fatal: nope\n")

    monkeypatch.setattr(update_cmd.subprocess, "run", fake_run)

    result = CliRunner().invoke(app, ["init", "--update"])
    assert result.exit_code == 2
    assert "git clone failed" in result.output
