"""`relay init` — scaffolds a relay-os/ from upstream, or refreshes one with --update."""

from __future__ import annotations

import os
import subprocess
import sys
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
    (templates / ".gitignore").write_text(
        "relay.local.toml\n.relay/\n**/task.lock\nbootstrap/\nskills/bootstrap/\n**/_template/\n**/_template.md\n"
    )
    (templates / "relay.toml").write_text("version = 1\n")
    (templates / "rules.md").write_text("rules\n")
    (templates / "context.md").write_text("context\n")
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
    assert "[secrets]" in text  # commented example present


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
    pre_existing = local_bin / "relay"
    pre_existing.write_text("#!/bin/sh\n# pre-existing\n")
    pre_existing.chmod(0o755)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("PATH", f"{local_bin}:/usr/bin")

    target = tmp_path / "company"
    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output

    # Pre-existing file untouched and we don't nag the user about PATH —
    # `shutil.which` finds their existing `relay`, so init confirms that
    # instead of telling them to munge PATH.
    assert pre_existing.read_text() == "#!/bin/sh\n# pre-existing\n"
    assert "Add the bin dir to your PATH" not in result.output
    assert "is already on your PATH at" in result.output


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
    (relay_os / "bootstrap" / "create").mkdir(parents=True)
    (relay_os / "bootstrap" / "create" / "ticket.md").write_text("OLD bootstrap shim\n")
    (relay_os / "bootstrap" / "stale").mkdir(parents=True)
    (relay_os / "bootstrap" / "stale" / "ticket.md").write_text("STALE shim from a prior upstream\n")
    (relay_os / "relay.toml").write_text("version = 1\n")
    (relay_os / "rules.md").write_text("user-edited rules\n")

    # Stale top-level file an earlier upstream shipped (counter / numeric IDs).
    (relay_os / "counter").write_text("7\n")
    # Stale top-level dir an earlier upstream shipped (meta/ → bootstrap/ rename).
    (relay_os / "meta").mkdir()
    (relay_os / "meta" / "ticket.md").write_text("OLD meta/ shim\n")
    # Stale nested dir from a bootstrap skill rename (create → ticket in 350c4ed).
    (relay_os / "skills" / "bootstrap" / "create").mkdir(parents=True)
    (relay_os / "skills" / "bootstrap" / "create" / "SKILL.md").write_text("OLD bootstrap/create skill\n")
    # Stale `_*` scaffold upstream no longer ships (rename or removal).
    (relay_os / "recurring").mkdir(exist_ok=True)
    (relay_os / "recurring" / "_template_old.md").write_text("STALE recurring template\n")

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
    (templates / "bootstrap" / "create").mkdir(parents=True)
    (templates / "bootstrap" / "create" / "ticket.md").write_text("NEW bootstrap shim\n")
    (templates / ".gitignore").write_text(
        "relay.local.toml\n.relay/\n**/task.lock\nbootstrap/\nskills/bootstrap/\n**/_template/\n**/_template.md\n"
    )

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
    # Bootstrap shims are infra — the whole tree mirrors upstream on --update.
    assert (relay_os / "bootstrap" / "create" / "ticket.md").read_text() == "NEW bootstrap shim\n"
    # Shims dropped upstream (renamed/removed) are pruned locally.
    assert not (relay_os / "bootstrap" / "stale").exists()
    # Top-level paths upstream once shipped but no longer does are pruned.
    assert not (relay_os / "counter").exists()
    assert not (relay_os / "meta").exists()
    # Nested obsolete paths (renamed bootstrap skills etc.) are pruned too.
    assert not (relay_os / "skills" / "bootstrap" / "create").exists()
    # `_*` scaffolds upstream no longer ships are also pruned.
    assert not (relay_os / "recurring" / "_template_old.md").exists()
    assert "Pruned 4 obsolete path(s)" in result.output
    assert "  counter" in result.output
    assert "  meta" in result.output
    assert "skills/bootstrap/create" in result.output
    assert "recurring/_template_old.md" in result.output
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

    # Upstream-managed paths and machine-local files are gitignored — none should be tracked.
    tracked = subprocess.run(
        ["git", "-C", str(target), "ls-files", "relay-os"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    assert any(p.startswith("relay-os/relay.toml") for p in tracked)
    assert not any(".relay/" in p for p in tracked)
    assert not any(p.endswith("relay.local.toml") for p in tracked)
    assert not any("/bootstrap/" in p for p in tracked)
    assert not any("/_template" in p for p in tracked)


def test_init_skips_commit_when_target_is_not_git_repo(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "company"
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output
    assert "Committed relay-os/" not in result.output


# --- skill discovery wiring ---------------------------------------------------


def test_init_links_skills_into_agent_dirs(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "company"
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output

    skills_src = (target / "relay-os" / "skills").resolve()
    for dirname in (".claude", ".codex"):
        link = target / dirname / "skills" / "relay"
        assert link.is_symlink(), f"missing symlink for {dirname}"
        assert link.resolve() == skills_src
    assert "Wired skill discovery for Claude Code, Codex" in result.output


def test_init_skips_skill_link_when_agent_marker_is_a_file(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "company"
    target.mkdir()
    sentinel = target / ".codex"
    sentinel.write_text("")  # mimic the empty-file Codex marker
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output

    # Sentinel left alone.
    assert sentinel.is_file()
    assert not (target / ".codex" / "skills").exists()
    # Claude Code still wired.
    assert (target / ".claude" / "skills" / "relay").is_symlink()
    assert "Skipped Codex skill wiring" in result.output


def test_init_link_skills_is_idempotent(tmp_path: Path) -> None:
    target = tmp_path / "company"
    relay_os = target / "relay-os"
    (relay_os / "skills").mkdir(parents=True)

    wired1, blocked1 = init_cmd._link_skills_for_agents(target, relay_os)
    wired2, blocked2 = init_cmd._link_skills_for_agents(target, relay_os)
    assert wired1 == wired2 == ["Claude Code", "Codex"]
    assert blocked1 == blocked2 == []
    assert (target / ".claude" / "skills" / "relay").is_symlink()


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
    # chdir somewhere with no relay-os/ so `find_repo_root` returns nothing.
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0, result.output
    assert "relay " in result.output
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


# --- gitignore management ----------------------------------------------------


def test_init_writes_host_gitignore_block_in_git_repo(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "company"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    subprocess.run(["git", "-C", str(target), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(target), "config", "user.name", "T"], check=True)
    monkeypatch.setenv("PATH", os.environ["PATH"])
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output

    host_gi = (target / ".gitignore").read_text()
    assert update_cmd.HOST_GITIGNORE_BEGIN in host_gi
    assert update_cmd.HOST_GITIGNORE_END in host_gi
    assert ".claude/skills/relay" in host_gi
    assert ".codex/skills/relay" in host_gi

    # Block was committed alongside relay-os/ in the init commit.
    tracked = subprocess.run(
        ["git", "-C", str(target), "ls-files"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    assert ".gitignore" in tracked


def test_init_appends_to_existing_host_gitignore(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "company"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    subprocess.run(["git", "-C", str(target), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(target), "config", "user.name", "T"], check=True)
    (target / ".gitignore").write_text("node_modules/\ndist/\n")
    monkeypatch.setenv("PATH", os.environ["PATH"])
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output

    host_gi = (target / ".gitignore").read_text()
    assert "node_modules/" in host_gi
    assert "dist/" in host_gi
    assert update_cmd.HOST_GITIGNORE_BEGIN in host_gi
    assert ".claude/skills/relay" in host_gi


def test_init_skips_host_gitignore_when_not_git_repo(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "company"
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 0, result.output
    assert not (target / ".gitignore").exists()


def test_ensure_host_gitignore_is_idempotent(tmp_path: Path) -> None:
    target = tmp_path / "company"
    target.mkdir()
    (target / ".git").mkdir()

    assert update_cmd.ensure_host_gitignore(target) is True
    first = (target / ".gitignore").read_text()
    # Second call with no changes should be a no-op.
    assert update_cmd.ensure_host_gitignore(target) is False
    assert (target / ".gitignore").read_text() == first


def test_ensure_host_gitignore_replaces_malformed_block(tmp_path: Path) -> None:
    target = tmp_path / "company"
    target.mkdir()
    (target / ".git").mkdir()
    # Block with begin marker but no end marker — replace from begin to EOF.
    (target / ".gitignore").write_text(
        f"node_modules/\n{update_cmd.HOST_GITIGNORE_BEGIN}\nstale-content\n"
    )

    assert update_cmd.ensure_host_gitignore(target) is True
    text = (target / ".gitignore").read_text()
    assert "stale-content" not in text
    assert "node_modules/" in text
    assert ".claude/skills/relay" in text
    assert update_cmd.HOST_GITIGNORE_END in text


def test_init_update_refreshes_inner_gitignore(
    tmp_path: Path, fake_venv, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`--update` writes the relay-managed marker block, dropping any duplicates
    of managed entries the user copied in before the marker convention existed,
    while leaving non-managed user lines alone."""
    relay_os = _seed_local_relay_os(tmp_path)
    # Stale pre-marker gitignore: some upstream entries copied directly,
    # plus a user-added rule that should survive the update.
    (relay_os / ".gitignore").write_text(
        "relay.local.toml\n.relay/\nbootstrap/\nmy-custom-ignore/\n"
    )
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

    gi = (relay_os / ".gitignore").read_text()
    # Marker block present and contains all upstream-managed entries.
    assert update_cmd.RELAY_GITIGNORE_BEGIN in gi
    assert update_cmd.RELAY_GITIGNORE_END in gi
    assert "bootstrap/" in gi
    assert "_template/" in gi
    assert "_template.md" in gi
    # User-added rule survives outside the block.
    assert "my-custom-ignore/" in gi
    # Duplicates of managed entries that were in the user area get removed.
    after_block = gi.split(update_cmd.RELAY_GITIGNORE_END, 1)[1]
    assert "bootstrap/" not in after_block
    assert "relay.local.toml" not in after_block
    assert ".relay/" not in after_block


def test_refresh_relay_gitignore_is_idempotent(tmp_path: Path) -> None:
    """Running the refresh twice on the same input is a no-op."""
    src_root = tmp_path / "upstream"
    src_root.mkdir()
    (src_root / ".gitignore").write_text("bootstrap/\n.relay/\n")
    dst_root = tmp_path / "relay-os"
    dst_root.mkdir()

    assert update_cmd._refresh_relay_gitignore(src_root, dst_root) is True
    first = (dst_root / ".gitignore").read_text()
    assert update_cmd._refresh_relay_gitignore(src_root, dst_root) is False
    assert (dst_root / ".gitignore").read_text() == first


def test_refresh_relay_gitignore_replaces_existing_block(tmp_path: Path) -> None:
    """An existing marker block is replaced wholesale; user content outside is kept."""
    src_root = tmp_path / "upstream"
    src_root.mkdir()
    (src_root / ".gitignore").write_text("bootstrap/\n.relay/\nnew-entry/\n")
    dst_root = tmp_path / "relay-os"
    dst_root.mkdir()
    # Existing file: stale marker block + user-area content.
    (dst_root / ".gitignore").write_text(
        f"{update_cmd.RELAY_GITIGNORE_BEGIN}\nold-stale-entry/\n"
        f"{update_cmd.RELAY_GITIGNORE_END}\n\nuser-rule/\n"
    )

    assert update_cmd._refresh_relay_gitignore(src_root, dst_root) is True
    text = (dst_root / ".gitignore").read_text()
    assert "old-stale-entry/" not in text
    assert "new-entry/" in text
    assert "user-rule/" in text


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


# --- venv recreation ----------------------------------------------------------


def test_venv_python_version_parses_pyvenv_cfg(tmp_path: Path) -> None:
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / "pyvenv.cfg").write_text("home = /usr/bin\nversion = 3.11.4\n")
    assert update_cmd._venv_python_version(venv) == (3, 11)


def test_venv_python_version_returns_none_when_missing(tmp_path: Path) -> None:
    assert update_cmd._venv_python_version(tmp_path / ".venv") is None


def test_venv_python_version_handles_malformed_cfg(tmp_path: Path) -> None:
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / "pyvenv.cfg").write_text("garbage without an equals\nversion = not.a.version\n")
    assert update_cmd._venv_python_version(venv) is None


def test_install_venv_recreates_on_python_version_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A venv built against a different Python X.Y gets blown away and rebuilt."""
    relay_os = tmp_path / "relay-os"
    dst_relay = relay_os / ".relay"
    dst_relay.mkdir(parents=True)
    (dst_relay / "pyproject.toml").write_text("[project]\nname = 'relay-os'\n")

    # Stand up a fake "old" venv tagged as Python 1.0 so it can never match.
    venv_dir = dst_relay / ".venv"
    (venv_dir / "bin").mkdir(parents=True)
    venv_python = venv_dir / "bin" / "python"
    venv_python.write_text("#!/bin/sh\n")
    venv_python.chmod(0o755)
    (venv_dir / "pyvenv.cfg").write_text("home = /old\nversion = 1.0.0\n")
    sentinel = venv_dir / "lib" / "python1.0" / "leftover.txt"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text("stale")

    real_run = subprocess.run

    def fake_run(cmd, **kwargs):
        if len(cmd) >= 3 and cmd[0] == sys.executable and cmd[1:3] == ["-m", "venv"]:
            new_venv = Path(cmd[3])
            (new_venv / "bin").mkdir(parents=True, exist_ok=True)
            (new_venv / "bin" / "python").write_text("#!/bin/sh\n")
            (new_venv / "bin" / "python").chmod(0o755)
            (new_venv / "bin" / "relay").write_text("#!/bin/sh\n")
            (new_venv / "bin" / "relay").chmod(0o755)
            (new_venv / "pyvenv.cfg").write_text(
                f"version = {sys.version_info.major}.{sys.version_info.minor}.0\n"
            )
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if "pip" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return real_run(cmd, **kwargs)

    monkeypatch.setattr(update_cmd.subprocess, "run", fake_run)

    update_cmd.install_venv(relay_os)

    # Stale lib dir wiped, new venv tagged with the running Python version.
    assert not sentinel.exists()
    assert update_cmd._venv_python_version(venv_dir) == sys.version_info[:2]


def test_install_venv_keeps_matching_venv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A venv that already matches the running Python isn't recreated."""
    relay_os = tmp_path / "relay-os"
    dst_relay = relay_os / ".relay"
    dst_relay.mkdir(parents=True)
    (dst_relay / "pyproject.toml").write_text("[project]\nname = 'relay-os'\n")

    venv_dir = dst_relay / ".venv"
    (venv_dir / "bin").mkdir(parents=True)
    (venv_dir / "bin" / "python").write_text("#!/bin/sh\n")
    (venv_dir / "bin" / "python").chmod(0o755)
    (venv_dir / "pyvenv.cfg").write_text(
        f"version = {sys.version_info.major}.{sys.version_info.minor}.7\n"
    )
    sentinel = venv_dir / "marker.txt"
    sentinel.write_text("preserve me")

    venv_calls: list[list[str]] = []
    real_run = subprocess.run

    def fake_run(cmd, **kwargs):
        if len(cmd) >= 3 and cmd[0] == sys.executable and cmd[1:3] == ["-m", "venv"]:
            venv_calls.append(list(cmd))
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if "pip" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return real_run(cmd, **kwargs)

    monkeypatch.setattr(update_cmd.subprocess, "run", fake_run)

    update_cmd.install_venv(relay_os)

    assert venv_calls == []  # no recreate
    assert sentinel.read_text() == "preserve me"
