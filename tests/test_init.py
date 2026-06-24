"""`relay init` — creates relay-os/ from package templates, or refreshes one."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.commands import init as init_cmd
from relay.commands import update as update_cmd
from relay.config import load_config
from relay.managed_skills import ManagedSkillError, ManagedSkillSummary
from relay.notification import post
from relay.skill_manager import SkillResult


_PACKAGED_RELAY_TOML = (
    Path(__file__).resolve().parents[1]
    / "src" / "relay" / "resources" / "templates" / "relay-os" / "relay.toml"
)


EXPECTED_FILES = {
    "relay-os/.gitignore",
    "relay-os/relay.toml",
    "relay-os/rules.md",
    "relay-os/context.md",
    "relay-os/scripts/cron.sh",
    "relay-os/bootstrap/contexts/dev/code/SKILL.md",
    "relay-os/bootstrap/contexts/relay/sync/SKILL.md",
    "relay-os/bootstrap/skills/eval/ticket-diagnostic/SKILL.md",
    "relay-os/bootstrap/skills/relay/autoclose/sweep/SKILL.md",
    "relay-os/bootstrap/skills/relay/autoclose/sweep/run.py",
    "relay-os/contexts/_template/SKILL.md",
    "relay-os/skills/_template/SKILL.md",
    "relay-os/skills/direct/body/SKILL.md",
    "relay-os/workflows/_template.md",
    "relay-os/recurring/_template/ticket.md",
    "relay-os/recurring/autoclose-merged/ticket.md",
    "relay-os/recurring/dream/ticket.md",
    "relay-os/recurring/skill-update/ticket.md",
    "relay-os/tasks/_template/ticket.md",
    "relay-os/tasks/relay-build/ticket.md",
    "relay-os/tasks/relay-build/blackboard.md",
    "relay-os/tasks/relay-build/log.md",
    "relay-os/workflows/autoclose-merged/sweep.md",
    "relay-os/workflows/direct/body.md",
    "relay-os/workflows/skill-update/run.md",
    "relay-os/workflows/build/onboarding.md",
}


def _make_git_repo(target: Path) -> Path:
    """Mark `target` as a git repo so it clears init's git-repo precondition.

    `relay init` refuses to write relay-os/ into a non-git dir, so tests that
    exercise a successful init must look like a repo. A bare `.git` dir is enough
    for the filesystem-level check — no real `git init` is needed for tests that
    don't assert the commit itself (those still init + configure git by hand).
    """
    target.mkdir(parents=True, exist_ok=True)
    (target / ".git").mkdir(exist_ok=True)
    return target


def _seed_fake_clone(clone_dir: Path) -> None:
    """Mimic the layout of the real repo: templates + CLI source."""
    templates = clone_dir / update_cmd.TEMPLATE_SUBPATH
    templates.mkdir(parents=True)
    (templates / ".gitignore").write_text(
        "relay.local.toml\n.relay/\nbootstrap/\n.agent-skills/\n"
        "**/_template/\n**/_template.md\n"
    )
    (templates / "relay.toml").write_text("version = 1\n")
    (templates / "rules.md").write_text("rules\n")
    (templates / "context.md").write_text("context\n")
    (templates / "scripts").mkdir()
    (templates / "scripts" / "cron.sh").write_text("#!/bin/sh\n")
    # Vendored skills + canonical relay/* contexts both live under bootstrap/.
    (templates / "bootstrap" / "skills" / "bootstrap" / "ticket").mkdir(parents=True)
    (templates / "bootstrap" / "skills" / "bootstrap" / "ticket" / "SKILL.md").write_text(
        "bootstrap/ticket skill\n"
    )
    (templates / "bootstrap" / "skills" / "retro" / "done-ticket").mkdir(parents=True)
    (templates / "bootstrap" / "skills" / "retro" / "done-ticket" / "SKILL.md").write_text(
        "retro/done-ticket skill\n"
    )
    (templates / "bootstrap" / "skills" / "eval" / "ticket-diagnostic").mkdir(
        parents=True
    )
    (
        templates
        / "bootstrap"
        / "skills"
        / "eval"
        / "ticket-diagnostic"
        / "SKILL.md"
    ).write_text("---\nname: eval/ticket-diagnostic\n---\neval skill\n")
    (templates / "bootstrap" / "skills" / "relay" / "autoclose" / "sweep").mkdir(
        parents=True
    )
    (
        templates
        / "bootstrap"
        / "skills"
        / "relay"
        / "autoclose"
        / "sweep"
        / "SKILL.md"
    ).write_text("---\nname: relay/autoclose/sweep\nscript: run.py\n---\nsweep\n")
    (
        templates
        / "bootstrap"
        / "skills"
        / "relay"
        / "autoclose"
        / "sweep"
        / "run.py"
    ).write_text("#!/usr/bin/env python3\n")
    for ctx in ("architecture", "principles", "cli"):
        (templates / "bootstrap" / "contexts" / "relay" / ctx).mkdir(parents=True)
        (templates / "bootstrap" / "contexts" / "relay" / ctx / "SKILL.md").write_text(
            f"relay/{ctx} context\n"
        )
    (templates / "bootstrap" / "contexts" / "relay" / "sync").mkdir(parents=True)
    (templates / "bootstrap" / "contexts" / "relay" / "sync" / "SKILL.md").write_text(
        "relay/sync context\n"
    )
    (templates / "bootstrap" / "contexts" / "dev" / "code").mkdir(parents=True)
    (templates / "bootstrap" / "contexts" / "dev" / "code" / "SKILL.md").write_text(
        "dev/code context\n"
    )
    for kind, fname in [
        ("contexts", "_template/SKILL.md"),
        ("skills", "_template/SKILL.md"),
        ("tasks", "_template/ticket.md"),
        ("workflows", "_template.md"),
        ("recurring", "_template/ticket.md"),
    ]:
        path = templates / kind / fname
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {kind} template\n")
    # Relay-owned recurring battery — no `_` prefix, refreshed on --update.
    # Recurring tasks are ticket-format directories; only `ticket.md` is vendored.
    (templates / "recurring" / "autoclose-merged").mkdir(parents=True, exist_ok=True)
    (templates / "recurring" / "autoclose-merged" / "ticket.md").write_text(
        "autoclose merged template\n"
    )
    (templates / "recurring" / "dream").mkdir(parents=True, exist_ok=True)
    (templates / "recurring" / "dream" / "ticket.md").write_text("dream template\n")
    (templates / "recurring" / "skill-update").mkdir(parents=True, exist_ok=True)
    (templates / "recurring" / "skill-update" / "ticket.md").write_text(
        "skill update template\n"
    )
    (templates / "skills" / "direct" / "body").mkdir(parents=True, exist_ok=True)
    (templates / "skills" / "direct" / "body" / "SKILL.md").write_text(
        "direct body skill\n"
    )
    (templates / "workflows" / "direct").mkdir(parents=True, exist_ok=True)
    (templates / "workflows" / "direct" / "body.md").write_text(
        "direct body workflow\n"
    )
    (templates / "workflows" / "skill-update").mkdir(parents=True, exist_ok=True)
    (templates / "workflows" / "skill-update" / "run.md").write_text(
        "skill update workflow\n"
    )
    (templates / "workflows" / "build").mkdir(parents=True, exist_ok=True)
    (templates / "workflows" / "build" / "onboarding.md").write_text(
        "---\n"
        "name: build/onboarding\n"
        "description: Onboarding workflow.\n"
        "steps:\n"
        "  - name: gather-and-spec\n"
        "    assignee: agent\n"
        "  - name: generate-batch\n"
        "    assignee: agent\n"
        "---\n"
        "\n"
        "## gather-and-spec\n"
        "\n"
        "Ask what the user wants to build.\n"
    )
    (templates / "tasks" / "relay-build").mkdir(parents=True, exist_ok=True)
    (templates / "tasks" / "relay-build" / "ticket.md").write_text(
        "---\n"
        "title: relay-build\n"
        "status: active\n"
        "mode: interactive\n"
        "owner: new-user\n"
        "human: new-user\n"
        "agent: claude\n"
        "assignee: claude\n"
        "contexts: []\n"
        "skills: []\n"
        "workflow:\n"
        "  name: build/onboarding\n"
        "  steps:\n"
        "  - name: gather-and-spec\n"
        "    skills: []\n"
        "    assignee: agent\n"
        "step: 1 (gather-and-spec)\n"
        "---\n"
        "\n"
        "## Description\n"
        "\n"
        "Onboarding task.\n"
        "\n"
        "## Context\n"
        "\n"
        "Empty until the `gather-and-spec` step runs at first launch.\n"
    )
    (templates / "tasks" / "relay-build" / "blackboard.md").write_text("notepad\n")
    (templates / "tasks" / "relay-build" / "log.md").write_text("created\n")
    (templates / "workflows" / "autoclose-merged").mkdir(
        parents=True, exist_ok=True
    )
    (templates / "workflows" / "autoclose-merged" / "sweep.md").write_text(
        "autoclose merged workflow\n"
    )

    cli_src = clone_dir / update_cmd.CLI_SRC_SUBPATH
    cli_src.mkdir(parents=True, exist_ok=True)
    (cli_src / "__init__.py").write_text("")
    (cli_src / "cli.py").write_text("# fake cli\n")

    (clone_dir / "pyproject.toml").write_text("[project]\nname = 'relay-os'\n")
    (clone_dir / "requirements.txt").write_text("typer>=0.12\nPyYAML>=6\n")


FAKE_SHA = "deadbeefcafe1234567890abcdef1234567890ab"


def _seed_fake_packaged_templates(root: Path) -> Path:
    clone_dir = root / "package"
    _seed_fake_clone(clone_dir)
    return clone_dir / update_cmd.TEMPLATE_SUBPATH


@pytest.fixture
def fake_clone(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    package_templates = _seed_fake_packaged_templates(tmp_path)
    monkeypatch.setattr(update_cmd, "packaged_template_root", lambda: package_templates)
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


@pytest.fixture(autouse=True)
def fake_managed_skill_sync(monkeypatch: pytest.MonkeyPatch):
    state = SimpleNamespace(
        install_calls=[],
        reconcile_calls=[],
        install_summary=ManagedSkillSummary(),
        reconcile_summary=ManagedSkillSummary(),
    )

    def fake_install(relay_os: Path) -> ManagedSkillSummary:
        state.install_calls.append(relay_os)
        return state.install_summary

    def fake_reconcile(relay_os: Path) -> ManagedSkillSummary:
        state.reconcile_calls.append(relay_os)
        return state.reconcile_summary

    monkeypatch.setattr(init_cmd, "install_managed_skills", fake_install)
    monkeypatch.setattr(init_cmd, "reconcile_managed_skills", fake_reconcile)
    return state


def test_clone_upstream_uses_relay_repo_url_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_url = "git@github.com:FastJVM/relay.git"
    commands: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        command = list(cmd)
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setenv("RELAY_REPO_URL", repo_url)
    monkeypatch.setattr(update_cmd.subprocess, "run", fake_run)

    update_cmd.clone_upstream(tmp_path / "repo")

    assert commands == [
        ["git", "clone", "--depth=1", repo_url, str(tmp_path / "repo")]
    ]


def test_clone_upstream_strips_pip_git_prefix_from_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commands: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        command = list(cmd)
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setenv(
        "RELAY_REPO_URL", "git+ssh://git@github.com/FastJVM/relay.git"
    )
    monkeypatch.setattr(update_cmd.subprocess, "run", fake_run)

    update_cmd.clone_upstream(tmp_path / "repo")

    assert commands == [
        [
            "git",
            "clone",
            "--depth=1",
            "ssh://git@github.com/FastJVM/relay.git",
            str(tmp_path / "repo"),
        ]
    ]


def test_clone_upstream_redacts_credentialed_url_in_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_url = "https://relay:TOKEN@github.com/FastJVM/relay.git"
    commands: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        command = list(cmd)
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setenv("RELAY_REPO_URL", repo_url)
    monkeypatch.setattr(update_cmd.subprocess, "run", fake_run)

    update_cmd.clone_upstream(tmp_path / "repo")

    assert commands == [
        ["git", "clone", "--depth=1", repo_url, str(tmp_path / "repo")]
    ]
    captured = capsys.readouterr()
    assert "https://github.com/FastJVM/relay.git" in captured.out
    assert "TOKEN" not in captured.out
    assert "relay:TOKEN" not in captured.out


def test_resolve_relay_repo_url_detects_matching_ssh_remote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_url = "git@github.com:FastJVM/relay.git"
    commands: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        command = list(cmd)
        commands.append(command)
        if command[-1] == "upstream":
            return subprocess.CompletedProcess(command, 2, stdout="", stderr="missing")
        if command[-1] == "origin":
            return subprocess.CompletedProcess(
                command, 0, stdout=f"{repo_url}\n", stderr=""
            )
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.delenv("RELAY_REPO_URL", raising=False)
    monkeypatch.setattr(update_cmd.subprocess, "run", fake_run)

    assert update_cmd.resolve_relay_repo_url(cwd=tmp_path) == repo_url
    assert commands == [
        ["git", "-C", str(tmp_path), "remote", "get-url", "upstream"],
        ["git", "-C", str(tmp_path), "remote", "get-url", "origin"],
    ]


def test_resolve_relay_repo_url_prefers_matching_ssh_remote_over_https(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    https_url = "https://github.com/FastJVM/relay.git"
    ssh_url = "git@github.com:FastJVM/relay.git"
    commands: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        command = list(cmd)
        commands.append(command)
        if command[-1] == "upstream":
            return subprocess.CompletedProcess(
                command, 0, stdout=f"{https_url}\n", stderr=""
            )
        if command[-1] == "origin":
            return subprocess.CompletedProcess(command, 0, stdout=f"{ssh_url}\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.delenv("RELAY_REPO_URL", raising=False)
    monkeypatch.setattr(update_cmd.subprocess, "run", fake_run)

    assert update_cmd.resolve_relay_repo_url(cwd=tmp_path) == ssh_url
    assert commands == [
        ["git", "-C", str(tmp_path), "remote", "get-url", "upstream"],
        ["git", "-C", str(tmp_path), "remote", "get-url", "origin"],
    ]


def test_write_pin_records_resolved_ssh_repo_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    relay_os = tmp_path / "relay-os"
    repo_url = "git@github.com:FastJVM/relay.git"
    monkeypatch.setenv("RELAY_REPO_URL", repo_url)

    update_cmd.write_pin(relay_os, FAKE_SHA)

    assert (relay_os / ".relay" / "RELAY_PIN").read_text().splitlines() == [
        repo_url,
        FAKE_SHA,
    ]


def test_write_pin_redacts_credentialed_repo_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    relay_os = tmp_path / "relay-os"
    monkeypatch.setenv(
        "RELAY_REPO_URL", "https://relay:TOKEN@github.com/FastJVM/relay.git"
    )

    update_cmd.write_pin(relay_os, FAKE_SHA)

    assert (relay_os / ".relay" / "RELAY_PIN").read_text().splitlines() == [
        "https://github.com/FastJVM/relay.git",
        FAKE_SHA,
    ]


def test_relay_pip_git_source_converts_scp_ssh_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RELAY_REPO_URL", "git@github.com:FastJVM/relay.git")

    assert (
        update_cmd.relay_pip_git_source()
        == "git+ssh://git@github.com/FastJVM/relay.git"
    )


def test_relay_pip_git_source_redacts_credentialed_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "RELAY_REPO_URL", "https://relay:TOKEN@github.com/FastJVM/relay.git"
    )

    assert (
        update_cmd.relay_pip_git_source()
        == "git+https://github.com/FastJVM/relay.git"
    )


# --- fresh init ---------------------------------------------------------------


def test_init_into_empty_dir(
    tmp_path: Path, fake_clone, fake_venv, fake_managed_skill_sync
) -> None:
    target = _make_git_repo(tmp_path / "company")

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    for rel in EXPECTED_FILES:
        assert (target / rel).is_file(), f"missing {rel}"
    assert os.access(target / "relay-os" / "scripts" / "cron.sh", os.X_OK)
    assert not (target / "relay-os" / "skills" / "eval").exists()
    assert not (target / "relay-os" / "skills" / "relay").exists()
    assert not (target / "relay-os" / "contexts" / "dev").exists()
    assert not (target / "relay-os" / "contexts" / "relay").exists()
    assert (
        target
        / "relay-os"
        / "bootstrap"
        / "skills"
        / "eval"
        / "ticket-diagnostic"
        / "SKILL.md"
    ).read_text().startswith("---\nname: eval/ticket-diagnostic\n")
    assert (
        target / "relay-os" / ".agent-skills" / "eval" / "ticket-diagnostic"
    ).is_symlink()
    assert (
        target
        / "relay-os"
        / "bootstrap"
        / "skills"
        / "relay"
        / "autoclose"
        / "sweep"
        / "SKILL.md"
    ).read_text().startswith("---\nname: relay/autoclose/sweep\n")
    assert (
        target / "relay-os" / ".agent-skills" / "relay" / "autoclose" / "sweep"
    ).is_symlink()

    assert "version = 1" in (target / "relay-os" / "relay.toml").read_text()
    assert fake_managed_skill_sync.install_calls == [target / "relay-os"]


def test_packaged_template_first_run_works_without_slack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The shipped relay.toml lets a stranger run commands with no Slack set up.

    Reads the real packaged template (the file `relay init` ships, not a fake
    fixture) into a repo with `SLACK_WEBHOOK_URL` unset, then proves the
    first-run posture: it selects no notification channels, `post()` is
    suppressed instead of crash-loud, and a first `relay create` succeeds.
    """
    repo = tmp_path / "relay-os"
    repo.mkdir()
    shutil.copy(_PACKAGED_RELAY_TOML, repo / "relay.toml")
    (repo / "relay.local.toml").write_text('user = "marc"\n')
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)

    text = (repo / "relay.toml").read_text()
    assert "channels = []" in text

    cfg = load_config(repo)
    assert cfg.notification_channels == ()
    # A fresh repo must not crash on the notification path.
    post(cfg, "first run, no slack")

    monkeypatch.chdir(repo)
    result = CliRunner().invoke(app, ["create", "First task"])
    assert result.exit_code == 0, result.output
    assert "[notification.slack].webhook" not in result.output


def test_init_reports_installed_managed_skills(
    tmp_path: Path,
    fake_clone,
    fake_venv,
    fake_managed_skill_sync,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _make_git_repo(tmp_path / "company")

    def fake_install(relay_os: Path) -> ManagedSkillSummary:
        fake_managed_skill_sync.install_calls.append(relay_os)
        skill = relay_os / "skills" / "relay" / "calendar-reminder"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: relay/calendar-reminder\n---\n")
        return ManagedSkillSummary(
            [
                SkillResult(
                    name="relay/calendar-reminder",
                    source_type="github",
                    status="installed",
                    message="installed relay/calendar-reminder through gh skill",
                    changed=True,
                )
            ]
        )

    fake_managed_skill_sync.install_summary = ManagedSkillSummary()
    monkeypatch.setattr(init_cmd, "install_managed_skills", fake_install)

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    assert "Managed skills: installed=1" in result.output
    assert (
        target / "relay-os" / ".agent-skills" / "relay" / "calendar-reminder"
    ).is_symlink()
    assert fake_managed_skill_sync.install_calls == [target / "relay-os"]


def test_init_fails_loud_when_required_managed_skill_fails(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _make_git_repo(tmp_path / "company")

    def fail_required(_: Path) -> ManagedSkillSummary:
        raise ManagedSkillError(
            "Required managed skill `relay/core` failed from example/repo: missing gh\n"
            "Remediation: relay skill install example/repo relay/core"
        )

    monkeypatch.setattr(init_cmd, "install_managed_skills", fail_required)

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 2
    assert "Required managed skill `relay/core` failed from example/repo" in result.output
    assert "Remediation: relay skill install example/repo relay/core" in result.output


def test_init_vendors_cli_and_links_wrapper_to_venv(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _make_git_repo(tmp_path / "company")
    monkeypatch.setenv("PATH", "")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
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


def test_init_writes_captured_user_name_to_local_toml(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _make_git_repo(tmp_path / "company")
    monkeypatch.setenv("PATH", "")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    # Surrounding whitespace is stripped, same as the prompt path.
    result = CliRunner().invoke(app, ["init", str(target), "--user", "  marc  "])
    assert result.exit_code == 0, result.output

    local_toml = target / "relay-os" / "relay.local.toml"
    assert local_toml.is_file()
    text = local_toml.read_text()
    # The `--user` value lands in `user` — a fresh init never leaves it empty.
    assert 'user = "marc"' in text
    assert 'user = ""' not in text
    assert "[secrets]" in text  # commented example present
    assert 'with user = "marc"' in result.output


def test_init_without_user_errors(tmp_path: Path, fake_clone, fake_venv) -> None:
    """A fresh `relay init` with no `--user` is a hard error — the name is a
    required parameter (so init stays scriptable), and we never fall back to
    writing `user = ""`. Nothing lands on disk."""
    target = tmp_path / "company"
    target.mkdir()

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 2
    assert "--user" in result.output
    assert not (target / "relay-os").exists()


def test_init_rejects_invalid_user(tmp_path: Path, fake_clone, fake_venv) -> None:
    """An invalid `--user` (a quote or backslash, which would break the `user`
    line in relay.local.toml) is rejected up front, before anything is
    written."""
    target = tmp_path / "company"
    target.mkdir()

    result = CliRunner().invoke(app, ["init", str(target), "--user", 'a"b'])
    assert result.exit_code == 2
    assert "quotes or backslashes" in result.output
    assert not (target / "relay-os").exists()


def test_init_installs_shim_when_local_bin_on_path(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_home = tmp_path / "home"
    local_bin = fake_home / ".local" / "bin"
    local_bin.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("PATH", f"{local_bin}:/usr/bin")

    target = _make_git_repo(tmp_path / "company")
    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
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

    target = _make_git_repo(tmp_path / "company")
    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    # Pre-existing file untouched and we don't nag the user about PATH —
    # `shutil.which` finds their existing `relay`, so init confirms that
    # instead of telling them to munge PATH.
    assert pre_existing.read_text() == "#!/bin/sh\n# pre-existing\n"
    assert "Add the bin dir to your PATH" not in result.output
    assert "is already on your PATH at" in result.output


def test_init_into_non_empty_dir_is_fine(tmp_path: Path, fake_clone, fake_venv) -> None:
    target = _make_git_repo(tmp_path / "existing-repo")
    (target / "README.md").write_text("hi")
    (target / "src").mkdir()

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output
    assert (target / "relay-os" / "relay.toml").is_file()
    assert (target / "README.md").read_text() == "hi"


def test_init_refuses_existing_relay_os(tmp_path: Path, fake_clone, fake_venv) -> None:
    target = tmp_path / "occupied"
    target.mkdir()
    (target / "relay-os").mkdir()

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 2
    assert "use `relay init --update`" in result.output


def test_init_into_missing_dir_errors_not_git_repo(
    tmp_path: Path, fake_clone, fake_venv
) -> None:
    """A target that doesn't exist can't be a git repo, so init fails loud
    instead of auto-creating the dir and silently skipping the commit. Nothing
    is written — the dir stays absent."""
    target = tmp_path / "fresh"
    assert not target.exists()

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 2
    assert "not a git repository" in result.output
    assert "git init" in result.output
    assert not target.exists()


# --- init build ticket ----------------------------------------------------------


def test_init_ships_build_ticket_template(
    tmp_path: Path, fake_clone, fake_venv
) -> None:
    """The relay-build task is a static packaged template: fresh init copies
    it verbatim — no prompts, no creating code — and the onboarding chat happens
    at first launch as the workflow's first step. The `--user` name is stamped
    over the `new-user` placeholder so it never ships live."""
    target = _make_git_repo(tmp_path / "company")
    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    task_dir = target / "relay-os" / "tasks" / "relay-build"
    text = (task_dir / "ticket.md").read_text()
    assert "status: active" in text
    assert "name: build/onboarding" in text
    assert "step: 1 (gather-and-spec)" in text
    assert "Empty until the `gather-and-spec` step runs at first launch" in text
    # The placeholder is stamped with the captured name; it never ships live.
    assert "owner: tester" in text
    assert "human: tester" in text
    assert "new-user" not in text
    assert (task_dir / "blackboard.md").is_file()
    assert (task_dir / "log.md").is_file()
    # Bare init on an empty repo points at `relay build` (the alias that
    # launches this ticket) rather than at a manual launch.
    assert "Run `relay build`" in result.output


def test_init_stamps_new_user_out_of_every_delivered_ticket(
    tmp_path: Path, fake_clone, fake_venv
) -> None:
    """No delivered ticket carries the `new-user` placeholder after a fresh
    init — the `--user` name is stamped over it everywhere, including the
    `browser-automation` draft that ships on every repo."""
    target = _make_git_repo(tmp_path / "company")

    result = CliRunner().invoke(app, ["init", str(target), "--user", "marc"])
    assert result.exit_code == 0, result.output

    tasks = target / "relay-os" / "tasks"
    for ticket in tasks.glob("**/ticket.md"):
        assert "new-user" not in ticket.read_text(), f"new-user survived in {ticket}"
    # browser-automation ships on every repo (not gated) and is stamped too.
    browser = (tasks / "browser-automation" / "ticket.md").read_text()
    assert "owner: marc" in browser
    assert "human: marc" in browser


def test_init_empty_repo_seeds_onboarding_and_points_at_build(
    tmp_path: Path, fake_clone, fake_venv
) -> None:
    """An empty repo keeps the onboarding ticket and the next-steps coax
    points the user at the onboarding command."""
    target = _make_git_repo(tmp_path / "company")

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    tasks = target / "relay-os" / "tasks"
    assert (tasks / "relay-build" / "ticket.md").is_file()
    assert "Run `relay build`" in result.output
    assert 'relay ticket "' not in result.output
    assert "Skipped the onboarding ticket" not in result.output


def test_init_filled_repo_skips_onboarding_and_points_at_ticket(
    tmp_path: Path, fake_clone, fake_venv
) -> None:
    """A filled repo (any pre-existing user file) drops the onboarding ticket
    and the next-steps coax points the user at `relay ticket`.
    browser-automation is not gated, so it still ships (stamped)."""
    target = _make_git_repo(tmp_path / "existing-repo")
    (target / "README.md").write_text("hi")

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    tasks = target / "relay-os" / "tasks"
    assert not (tasks / "relay-build").exists()  # onboarding pruned
    # Not gated — still delivered, and stamped (no placeholder survives).
    browser = tasks / "browser-automation" / "ticket.md"
    assert browser.is_file()
    assert "new-user" not in browser.read_text()
    assert 'relay ticket "' in result.output
    assert "Skipped the onboarding ticket" in result.output
    assert "Run `relay build`" not in result.output


def test_init_filled_repo_ignores_relay_managed_files(
    tmp_path: Path, fake_clone, fake_venv
) -> None:
    """Pre-existing `.git`/`.DS_Store` and relay-managed names (CLAUDE.md etc.)
    don't count as a filled repo — onboarding is still seeded."""
    target = tmp_path / "company"
    target.mkdir()
    (target / ".git").mkdir()
    (target / ".DS_Store").write_text("")
    (target / "CLAUDE.md").write_text("user-authored guide")

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    assert (target / "relay-os" / "tasks" / "relay-build" / "ticket.md").is_file()
    assert "Run `relay build`" in result.output


# --- name capture + gate helpers ----------------------------------------------


def test_repo_is_empty_true_for_missing_or_relay_managed(tmp_path: Path) -> None:
    assert init_cmd._repo_is_empty(tmp_path / "nope") is True

    target = tmp_path / "fresh"
    target.mkdir()
    assert init_cmd._repo_is_empty(target) is True

    (target / ".git").mkdir()
    (target / ".DS_Store").write_text("")
    (target / "CLAUDE.md").write_text("x")
    (target / "AGENTS.md").write_text("x")
    (target / ".gitignore").write_text("x")
    assert init_cmd._repo_is_empty(target) is True


def test_repo_is_empty_false_when_user_content_present(tmp_path: Path) -> None:
    target = tmp_path / "proj"
    target.mkdir()
    (target / "README.md").write_text("hi")
    assert init_cmd._repo_is_empty(target) is False


def test_prune_onboarding_tickets_removes_build_ticket(tmp_path: Path) -> None:
    """The delivered onboarding ticket (relay-build) is pruned on a filled
    repo; other tasks are left alone."""
    relay_os = tmp_path / "relay-os"
    tasks = relay_os / "tasks"
    for name in ("relay-build", "browser-automation", "_template"):
        (tasks / name).mkdir(parents=True)
        (tasks / name / "ticket.md").write_text("---\n---\n")

    pruned = init_cmd._prune_onboarding_tickets(relay_os)

    assert set(pruned) == {"relay-build"}
    assert not (tasks / "relay-build").exists()
    assert (tasks / "browser-automation").is_dir()  # not gated
    assert (tasks / "_template").is_dir()


def test_stamp_user_into_delivered_tickets(tmp_path: Path) -> None:
    relay_os = tmp_path / "relay-os"
    tasks = relay_os / "tasks"
    (tasks / "alpha").mkdir(parents=True)
    (tasks / "alpha" / "ticket.md").write_text(
        "---\nowner: new-user\nhuman: new-user\nassignee: claude\n---\n"
    )
    (tasks / "beta").mkdir(parents=True)
    (tasks / "beta" / "ticket.md").write_text(
        "---\nowner: new-user\nhuman: new-user\nassignee: new-user\n---\n"
    )
    # The `replace-with-human-name` token is a different placeholder, owned by
    # create_task/recurring — the stamp must leave it alone.
    (tasks / "_template").mkdir(parents=True)
    (tasks / "_template" / "ticket.md").write_text(
        "---\nowner: replace-with-human-name\nhuman: replace-with-human-name\n---\n"
    )

    stamped = init_cmd._stamp_user_into_delivered_tickets(relay_os, "marc")

    assert set(stamped) == {"alpha", "beta"}
    alpha = (tasks / "alpha" / "ticket.md").read_text()
    assert "owner: marc" in alpha and "human: marc" in alpha
    assert "assignee: claude" in alpha  # non-placeholder line untouched
    assert "new-user" not in alpha
    beta = (tasks / "beta" / "ticket.md").read_text()
    assert "assignee: marc" in beta
    assert "new-user" not in beta
    template = (tasks / "_template" / "ticket.md").read_text()
    assert "replace-with-human-name" in template  # left alone


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
    # Optional Relay-owned skill content now lives in skills/ and should be
    # preserved for the managed-skill reconciler, not pruned as obsolete.
    (relay_os / "skills" / "relay" / "calendar-reminder").mkdir(parents=True)
    (relay_os / "skills" / "relay" / "calendar-reminder" / "SKILL.md").write_text(
        "OLD relay/calendar-reminder skill\n"
    )
    (relay_os / "skills" / "eval" / "ticket-diagnostic").mkdir(parents=True)
    (relay_os / "skills" / "eval" / "ticket-diagnostic" / "SKILL.md").write_text(
        "OLD eval/ticket-diagnostic skill\n"
    )
    (relay_os / ".agent-skills").mkdir()
    (relay_os / ".agent-skills" / "_template").symlink_to("../skills/_template")
    (relay_os / "contexts" / "relay" / "sync").mkdir(parents=True)
    (relay_os / "contexts" / "relay" / "sync" / "SKILL.md").write_text(
        "OLD relay/sync context\n"
    )
    (relay_os / "contexts" / "dev" / "code").mkdir(parents=True)
    (relay_os / "contexts" / "dev" / "code" / "SKILL.md").write_text(
        "OLD dev/code context\n"
    )
    # Stale `_*` create upstream no longer ships (rename or removal).
    (relay_os / "recurring").mkdir(exist_ok=True)
    (relay_os / "recurring" / "_template_old.md").write_text("STALE recurring template\n")

    vendored = relay_os / ".relay" / "src" / "relay"
    vendored.mkdir(parents=True)
    (vendored / "cli.py").write_text("# OLD vendored cli\n")
    return relay_os


def _seed_relay_source_checkout(root: Path) -> None:
    """Add the source-tree markers `init --update` uses to protect this repo."""
    (root / "pyproject.toml").write_text('[project]\nname = "relay-os"\n')
    (root / "src" / "relay" / "commands").mkdir(parents=True)
    (root / "src" / "relay" / "commands" / "init.py").write_text("# source init\n")
    (root / "src" / "relay" / "commands" / "update.py").write_text("# source update\n")
    (root / "src" / "relay" / "resources" / "templates" / "relay-os").mkdir(
        parents=True
    )


def _seed_fake_upstream_for_update(clone_dir: Path) -> None:
    templates = clone_dir / update_cmd.TEMPLATE_SUBPATH
    (templates / "skills" / "_template").mkdir(parents=True)
    (templates / "tasks" / "_template").mkdir(parents=True)
    (templates / "skills" / "_template" / "SKILL.md").write_text("NEW skill template\n")
    (templates / "tasks" / "_template" / "ticket.md").write_text("NEW ticket template\n")
    # Relay-owned recurring battery — refreshed wholesale on --update.
    # Recurring tasks are ticket-format directories; only `ticket.md` is vendored.
    (templates / "recurring" / "dream").mkdir(parents=True, exist_ok=True)
    (templates / "recurring" / "dream" / "ticket.md").write_text("NEW dream template\n")
    (templates / "recurring" / "autoclose-merged").mkdir(
        parents=True, exist_ok=True
    )
    (templates / "recurring" / "autoclose-merged" / "ticket.md").write_text(
        "NEW autoclose merged template\n"
    )
    (templates / "recurring" / "skill-update").mkdir(parents=True, exist_ok=True)
    (templates / "recurring" / "skill-update" / "ticket.md").write_text(
        "NEW skill update template\n"
    )
    (templates / "skills" / "direct" / "body").mkdir(parents=True, exist_ok=True)
    (templates / "skills" / "direct" / "body" / "SKILL.md").write_text(
        "NEW direct body skill\n"
    )
    (templates / "workflows" / "direct").mkdir(parents=True, exist_ok=True)
    (templates / "workflows" / "direct" / "body.md").write_text(
        "NEW direct body workflow\n"
    )
    (templates / "workflows" / "autoclose-merged").mkdir(
        parents=True, exist_ok=True
    )
    (templates / "workflows" / "autoclose-merged" / "sweep.md").write_text(
        "NEW autoclose merged workflow\n"
    )
    (templates / "workflows" / "skill-update").mkdir(parents=True, exist_ok=True)
    (templates / "workflows" / "skill-update" / "run.md").write_text(
        "NEW skill update workflow\n"
    )
    (templates / "rules.md").write_text("NEW upstream rules — should NOT be copied (no _ prefix)\n")
    (templates / "bootstrap" / "create").mkdir(parents=True)
    (templates / "bootstrap" / "create" / "ticket.md").write_text("NEW bootstrap shim\n")
    # All vendored skills and contexts now live under `bootstrap/`.
    (templates / "bootstrap" / "skills" / "bootstrap" / "ticket").mkdir(parents=True)
    (templates / "bootstrap" / "skills" / "bootstrap" / "ticket" / "SKILL.md").write_text(
        "NEW bootstrap/ticket skill\n"
    )
    (templates / "bootstrap" / "skills" / "retro" / "done-ticket").mkdir(parents=True)
    (templates / "bootstrap" / "skills" / "retro" / "done-ticket" / "SKILL.md").write_text(
        "NEW retro/done-ticket skill\n"
    )
    (templates / "bootstrap" / "skills" / "eval" / "ticket-diagnostic").mkdir(
        parents=True
    )
    (
        templates
        / "bootstrap"
        / "skills"
        / "eval"
        / "ticket-diagnostic"
        / "SKILL.md"
    ).write_text("NEW eval/ticket-diagnostic skill\n")
    (templates / "bootstrap" / "skills" / "relay" / "autoclose" / "sweep").mkdir(
        parents=True
    )
    (
        templates
        / "bootstrap"
        / "skills"
        / "relay"
        / "autoclose"
        / "sweep"
        / "SKILL.md"
    ).write_text("NEW relay/autoclose/sweep skill\n")
    (
        templates
        / "bootstrap"
        / "skills"
        / "relay"
        / "autoclose"
        / "sweep"
        / "run.py"
    ).write_text("#!/usr/bin/env python3\n")
    for ctx in ("architecture", "principles", "cli"):
        (templates / "bootstrap" / "contexts" / "relay" / ctx).mkdir(parents=True)
        (templates / "bootstrap" / "contexts" / "relay" / ctx / "SKILL.md").write_text(
            f"NEW relay/{ctx} context\n"
        )
    (templates / "bootstrap" / "contexts" / "relay" / "sync").mkdir(parents=True)
    (templates / "bootstrap" / "contexts" / "relay" / "sync" / "SKILL.md").write_text(
        "NEW relay/sync context\n"
    )
    (templates / "bootstrap" / "contexts" / "dev" / "code").mkdir(parents=True)
    (templates / "bootstrap" / "contexts" / "dev" / "code" / "SKILL.md").write_text(
        "NEW dev/code context\n"
    )
    (templates / ".gitignore").write_text(
        "relay.local.toml\n.relay/\nbootstrap/\n.agent-skills/\n"
        "**/_template/\n**/_template.md\n"
    )

    cli_src = clone_dir / update_cmd.CLI_SRC_SUBPATH
    cli_src.mkdir(parents=True, exist_ok=True)
    (cli_src / "cli.py").write_text("# NEW vendored cli\n")

    (clone_dir / "pyproject.toml").write_text("[project]\nname = 'relay-os'\n")
    (clone_dir / "requirements.txt").write_text("typer>=0.12\nPyYAML>=6\n")


def test_init_update_refreshes_cli_and_underscore_templates(
    tmp_path: Path, fake_venv, fake_managed_skill_sync, monkeypatch: pytest.MonkeyPatch,
) -> None:
    relay_os = _seed_local_relay_os(tmp_path)
    package_clone = tmp_path / "package"
    _seed_fake_upstream_for_update(package_clone)
    monkeypatch.setattr(
        update_cmd,
        "packaged_template_root",
        lambda: package_clone / update_cmd.TEMPLATE_SUBPATH,
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
    fake_managed_skill_sync.reconcile_summary = ManagedSkillSummary(
        [
            SkillResult(
                name="relay/calendar-reminder",
                source_type="github",
                status="delegated",
                message="delegated update to gh skill",
            )
        ]
    )

    result = CliRunner().invoke(app, ["init", "--update"])
    assert result.exit_code == 0, result.output

    assert (relay_os / "skills" / "_template" / "SKILL.md").read_text() == "NEW skill template\n"
    assert (relay_os / "tasks" / "_template" / "ticket.md").read_text() == "NEW ticket template\n"
    # Bootstrap shims are infra — the whole tree mirrors upstream on --update.
    assert (relay_os / "bootstrap" / "create" / "ticket.md").read_text() == "NEW bootstrap shim\n"
    # Vendored skills + canonical contexts live under bootstrap/.
    assert (
        (relay_os / "bootstrap" / "skills" / "bootstrap" / "ticket" / "SKILL.md").read_text()
        == "NEW bootstrap/ticket skill\n"
    )
    assert (
        (relay_os / "bootstrap" / "skills" / "retro" / "done-ticket" / "SKILL.md").read_text()
        == "NEW retro/done-ticket skill\n"
    )
    assert (
        (relay_os / "bootstrap" / "skills" / "eval" / "ticket-diagnostic" / "SKILL.md").read_text()
        == "NEW eval/ticket-diagnostic skill\n"
    )
    assert (
        relay_os / "bootstrap" / "skills" / "relay" / "autoclose" / "sweep" / "SKILL.md"
    ).read_text() == "NEW relay/autoclose/sweep skill\n"
    for ctx in ("architecture", "principles", "cli"):
        assert (
            (relay_os / "bootstrap" / "contexts" / "relay" / ctx / "SKILL.md").read_text()
            == f"NEW relay/{ctx} context\n"
        )
    assert (
        (relay_os / "bootstrap" / "contexts" / "relay" / "sync" / "SKILL.md").read_text()
        == "NEW relay/sync context\n"
    )
    assert (
        (relay_os / "bootstrap" / "contexts" / "dev" / "code" / "SKILL.md").read_text()
        == "NEW dev/code context\n"
    )
    # Generated agent view exposes the effective skill set without claiming
    # namespaces in relay-os/skills.
    assert (relay_os / ".agent-skills" / "bootstrap" / "ticket").is_symlink()
    assert (relay_os / ".agent-skills" / "eval" / "ticket-diagnostic").is_symlink()
    assert (relay_os / ".agent-skills" / "retro" / "done-ticket").is_symlink()
    assert (relay_os / ".agent-skills" / "relay" / "autoclose" / "sweep").is_symlink()
    assert (relay_os / ".agent-skills" / "relay" / "calendar-reminder").is_symlink()
    assert (relay_os / ".agent-skills" / "_template").is_symlink()
    # Shims dropped upstream (renamed/removed) are pruned locally.
    assert not (relay_os / "bootstrap" / "stale").exists()
    # Top-level paths upstream once shipped but no longer does are pruned.
    assert not (relay_os / "counter").exists()
    assert not (relay_os / "meta").exists()
    # Stale bootstrap-namespace nested skill goes away, but local namespace
    # roots are not replaced by generated symlinks.
    legacy_bootstrap_skill = relay_os / "skills" / "bootstrap"
    assert legacy_bootstrap_skill.is_dir() and not legacy_bootstrap_skill.is_symlink()
    assert (legacy_bootstrap_skill / "create").exists() is False
    # `_*` creates upstream no longer ships are also pruned.
    assert not (relay_os / "recurring" / "_template_old.md").exists()
    # Per-update prune count includes only narrow known Relay-owned paths plus
    # the underscore-template prune. Local namespace roots are preserved.
    assert "Pruned" in result.output
    assert "  counter" in result.output
    assert "  meta" in result.output
    assert "  skills/bootstrap/create" in result.output
    assert "  skills/relay/calendar-reminder" not in result.output
    assert "  skills/eval" not in result.output
    assert "  contexts/dev/code" in result.output
    assert "  contexts/relay/sync" in result.output
    assert "  contexts/dev\n" not in result.output
    assert "  contexts/relay\n" not in result.output
    assert "recurring/_template_old.md" in result.output
    # User-edited content untouched.
    assert (relay_os / "skills" / "myteam" / "real-skill" / "SKILL.md").read_text() == "user content\n"
    assert (
        (relay_os / "skills" / "relay" / "calendar-reminder" / "SKILL.md").read_text()
        == "OLD relay/calendar-reminder skill\n"
    )
    assert (relay_os / "rules.md").read_text() == "user-edited rules\n"
    assert fake_managed_skill_sync.reconcile_calls == [relay_os]
    assert "Managed skills: delegated=1" in result.output

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


@pytest.mark.parametrize(
    "preexisting",
    [None, "STALE dream template — old known-skill list\n"],
    ids=["missing", "stale"],
)
def test_init_update_refreshes_vendored_recurring_template(
    tmp_path: Path,
    fake_venv,
    monkeypatch: pytest.MonkeyPatch,
    preexisting: str | None,
) -> None:
    """Relay-owned live batteries are no-prefix files outside `bootstrap/`.

    `init --update` must restore them when missing (repos predating the
    template) and overwrite them when stale, or their launch paths have nothing
    to create.
    """
    relay_os = _seed_local_relay_os(tmp_path)
    autoclose = relay_os / "recurring" / "autoclose-merged" / "ticket.md"
    dream = relay_os / "recurring" / "dream" / "ticket.md"
    skill_update = relay_os / "recurring" / "skill-update" / "ticket.md"
    autoclose_workflow = relay_os / "workflows" / "autoclose-merged" / "sweep.md"
    direct_workflow = relay_os / "workflows" / "direct" / "body.md"
    skill_update_workflow = relay_os / "workflows" / "skill-update" / "run.md"
    direct_skill = relay_os / "skills" / "direct" / "body" / "SKILL.md"
    if preexisting is None:
        assert not autoclose.exists()
        assert not dream.exists()
        assert not skill_update.exists()
        assert not autoclose_workflow.exists()
        assert not direct_workflow.exists()
        assert not skill_update_workflow.exists()
        assert not direct_skill.exists()
    else:
        autoclose.parent.mkdir(parents=True, exist_ok=True)
        autoclose.write_text("STALE autoclose merged template\n")
        dream.parent.mkdir(parents=True, exist_ok=True)
        dream.write_text(preexisting)
        skill_update.parent.mkdir(parents=True, exist_ok=True)
        skill_update.write_text("STALE skill update template\n")
        autoclose_workflow.parent.mkdir(parents=True, exist_ok=True)
        autoclose_workflow.write_text("STALE autoclose merged workflow\n")
        direct_workflow.parent.mkdir(parents=True, exist_ok=True)
        direct_workflow.write_text("STALE direct body workflow\n")
        skill_update_workflow.parent.mkdir(parents=True, exist_ok=True)
        skill_update_workflow.write_text("STALE skill update workflow\n")
        direct_skill.parent.mkdir(parents=True, exist_ok=True)
        direct_skill.write_text("STALE direct body skill\n")

    package_clone = tmp_path / "package"
    _seed_fake_upstream_for_update(package_clone)
    monkeypatch.setattr(
        update_cmd,
        "packaged_template_root",
        lambda: package_clone / update_cmd.TEMPLATE_SUBPATH,
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

    assert autoclose.read_text() == "NEW autoclose merged template\n"
    assert dream.read_text() == "NEW dream template\n"
    assert skill_update.read_text() == "NEW skill update template\n"
    assert autoclose_workflow.read_text() == "NEW autoclose merged workflow\n"
    assert direct_workflow.read_text() == "NEW direct body workflow\n"
    assert skill_update_workflow.read_text() == "NEW skill update workflow\n"
    assert direct_skill.read_text() == "NEW direct body skill\n"
    assert "recurring/autoclose-merged/ticket.md" in result.output
    assert "recurring/dream/ticket.md" in result.output
    assert "recurring/skill-update/ticket.md" in result.output
    assert "workflows/autoclose-merged/sweep.md" in result.output
    assert "workflows/direct/body.md" in result.output
    assert "workflows/skill-update/run.md" in result.output
    assert "skills/direct/body/SKILL.md" in result.output


def test_init_update_in_relay_source_checkout_materializes_gitignored_mirrors(
    tmp_path: Path, fake_venv, fake_managed_skill_sync, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`init --update` in Relay's own repo must leave git-tracked fixtures
    alone but still materialize the gitignored package-backed mirrors
    (`bootstrap/` and `recurring/dream/`) — otherwise `relay chat` and
    `relay dream` fail in a fresh source clone.
    """
    relay_os = _seed_local_relay_os(tmp_path)
    shutil.rmtree(relay_os / "bootstrap")
    _seed_relay_source_checkout(tmp_path)
    for ctx in ("architecture", "principles", "cli"):
        path = relay_os / "contexts" / "relay" / ctx
        path.mkdir(parents=True)
        (path / "SKILL.md").write_text(f"SOURCE relay/{ctx}\n")
    (relay_os / "skills" / "retro" / "done-ticket").mkdir(parents=True)
    (relay_os / "skills" / "retro" / "done-ticket" / "SKILL.md").write_text(
        "SOURCE retro/done-ticket\n"
    )
    (relay_os / "workflows" / "skill-update").mkdir(parents=True)
    (relay_os / "workflows" / "skill-update" / "run.md").write_text(
        "SOURCE skill update workflow\n"
    )
    # An obsolete top-level path (prune-listed) must survive in a source
    # checkout, where pruning is skipped entirely.
    (relay_os / "counter").write_text("SOURCE counter\n")

    package_clone = tmp_path / "package"
    _seed_fake_upstream_for_update(package_clone)
    monkeypatch.setattr(
        update_cmd,
        "packaged_template_root",
        lambda: package_clone / update_cmd.TEMPLATE_SUBPATH,
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

    assert (
        (relay_os / ".relay" / "src" / "relay" / "cli.py").read_text()
        == "# NEW vendored cli\n"
    )
    assert fake_venv == [relay_os]
    assert "Skipped tracked-fixture refresh/prune in Relay source checkout" in result.output
    assert "Refreshed gitignored mirrors" in result.output
    assert "skipped managed skill reconciliation" in result.output
    assert "Pruned" not in result.output
    assert fake_managed_skill_sync.reconcile_calls == []

    for ctx in ("architecture", "principles", "cli"):
        path = relay_os / "contexts" / "relay" / ctx
        assert path.is_dir() and not path.is_symlink()
        assert (path / "SKILL.md").read_text() == f"SOURCE relay/{ctx}\n"
    retro = relay_os / "skills" / "retro"
    assert retro.is_dir() and not retro.is_symlink()
    assert (
        relay_os / "skills" / "retro" / "done-ticket" / "SKILL.md"
    ).read_text() == "SOURCE retro/done-ticket\n"
    assert (relay_os / "counter").read_text() == "SOURCE counter\n"
    assert not (relay_os / "recurring" / "_rem.md").exists()

    # Gitignored mirrors must still land — that's the whole point of this path.
    assert (
        relay_os / "bootstrap" / "create" / "ticket.md"
    ).read_text() == "NEW bootstrap shim\n"
    assert (
        relay_os / "bootstrap" / "skills" / "bootstrap" / "ticket" / "SKILL.md"
    ).read_text() == "NEW bootstrap/ticket skill\n"
    assert (
        relay_os / "bootstrap" / "skills" / "relay" / "autoclose" / "sweep" / "SKILL.md"
    ).read_text() == "NEW relay/autoclose/sweep skill\n"
    assert (
        relay_os / "recurring" / "dream" / "ticket.md"
    ).read_text() == "NEW dream template\n"
    assert (
        relay_os / "recurring" / "autoclose-merged" / "ticket.md"
    ).read_text() == "NEW autoclose merged template\n"
    assert (
        relay_os / "recurring" / "skill-update" / "ticket.md"
    ).read_text() == "NEW skill update template\n"
    assert (
        relay_os / "workflows" / "skill-update" / "run.md"
    ).read_text() == "SOURCE skill update workflow\n"


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

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output
    assert "Committed relay-os/ as" in result.output

    log = subprocess.run(
        ["git", "-C", str(target), "log", "--oneline"],
        capture_output=True, text=True, check=True,
    )
    assert "Create relay-os via `relay init`" in log.stdout

    # Upstream-managed paths and machine-local files are gitignored — none should be tracked.
    tracked = subprocess.run(
        ["git", "-C", str(target), "ls-files", "relay-os"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    assert any(p.startswith("relay-os/relay.toml") for p in tracked)
    assert not any(".relay/" in p for p in tracked)
    assert not any(p.endswith("relay.local.toml") for p in tracked)
    assert not any("/bootstrap/" in p for p in tracked)
    assert not any("/skills/retro/" in p for p in tracked)
    assert not any("/_template" in p for p in tracked)


def test_init_fails_loud_when_target_is_not_git_repo(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    """relay is git-backed: a non-git target is a hard error (not a silent
    skip), and nothing is written to disk — the user runs `git init` here and
    re-runs."""
    target = tmp_path / "company"
    target.mkdir()  # exists, but is not a git repo
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 2
    assert "not a git repository" in result.output
    assert "git init" in result.output
    assert not (target / "relay-os").exists()


# --- skill discovery wiring ---------------------------------------------------


def test_init_links_skills_into_agent_dirs(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _make_git_repo(tmp_path / "company")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    skills_src = (target / "relay-os" / ".agent-skills").resolve()
    for dirname in (".claude", ".codex"):
        link = target / dirname / "skills" / "relay"
        assert link.is_symlink(), f"missing symlink for {dirname}"
        assert link.resolve() == skills_src
    assert (target / "relay-os" / ".agent-skills" / "eval" / "ticket-diagnostic").is_symlink()
    assert "Wired skill discovery for Claude Code, Codex" in result.output


def test_init_skips_skill_link_when_agent_marker_is_a_file(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _make_git_repo(tmp_path / "company")
    sentinel = target / ".codex"
    sentinel.write_text("")  # mimic the empty-file Codex marker
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
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


# --- generated agent skill view ---------------------------------------------


def test_agent_skill_view_includes_bootstrap_and_local_skills(tmp_path: Path) -> None:
    target = tmp_path / "company"
    relay_os = target / "relay-os"
    (relay_os / "bootstrap" / "skills" / "eval" / "ticket-diagnostic").mkdir(
        parents=True
    )
    (
        relay_os
        / "bootstrap"
        / "skills"
        / "eval"
        / "ticket-diagnostic"
        / "SKILL.md"
    ).write_text("bundled eval\n")
    (relay_os / "skills" / "team" / "local").mkdir(parents=True)
    (relay_os / "skills" / "team" / "local" / "SKILL.md").write_text("local\n")

    wired, blocked = init_cmd._link_skills_for_agents(target, relay_os)

    assert wired == ["Claude Code", "Codex"]
    assert blocked == []
    assert (relay_os / ".agent-skills" / "eval" / "ticket-diagnostic").is_symlink()
    assert (relay_os / ".agent-skills" / "team" / "local").is_symlink()
    assert os.readlink(target / ".codex" / "skills" / "relay") == (
        "../../relay-os/.agent-skills"
    )


def test_agent_skill_view_prefers_local_skill_over_bootstrap(tmp_path: Path) -> None:
    target = tmp_path / "company"
    relay_os = target / "relay-os"
    bundled = relay_os / "bootstrap" / "skills" / "tools" / "example"
    local = relay_os / "skills" / "tools" / "example"
    bundled.mkdir(parents=True)
    local.mkdir(parents=True)
    (bundled / "SKILL.md").write_text("bundled\n")
    (local / "SKILL.md").write_text("local\n")

    init_cmd._link_skills_for_agents(target, relay_os)

    link = relay_os / ".agent-skills" / "tools" / "example"
    assert link.is_symlink()
    assert link.resolve() == local.resolve()


def test_prune_obsolete_removes_old_bootstrap_exposure_symlinks_only(
    tmp_path: Path,
) -> None:
    relay_os = tmp_path / "relay-os"
    (relay_os / "bootstrap" / "skills" / "eval").mkdir(parents=True)
    (relay_os / "skills").mkdir(parents=True)
    old_generated = relay_os / "skills" / "eval"
    old_generated.symlink_to("../bootstrap/skills/eval")
    real_local = relay_os / "skills" / "google"
    real_local.mkdir()
    (real_local / "SKILL.md").write_text("local\n")

    pruned = update_cmd.prune_obsolete(relay_os)

    assert "skills/eval" in pruned
    assert not old_generated.exists()
    assert real_local.is_dir()
    assert "skills/google" not in pruned


def test_link_skills_for_agents_replaces_old_raw_skills_link(tmp_path: Path) -> None:
    target = tmp_path / "company"
    relay_os = target / "relay-os"
    (relay_os / "skills" / "team" / "local").mkdir(parents=True)
    (relay_os / "skills" / "team" / "local" / "SKILL.md").write_text("local\n")
    old = target / ".claude" / "skills" / "relay"
    old.parent.mkdir(parents=True)
    old.symlink_to("../../relay-os/skills")

    init_cmd._link_skills_for_agents(target, relay_os)

    assert os.readlink(old) == "../../relay-os/.agent-skills"


# --- agent-guide files (CLAUDE.md / AGENTS.md) -------------------------------


def test_init_writes_agent_guides(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _make_git_repo(tmp_path / "company")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    for name in ("CLAUDE.md", "AGENTS.md"):
        path = target / name
        assert path.is_file(), f"missing {name}"
        body = path.read_text()
        # Identical content for both — orientation that points at canonical contexts.
        assert body == init_cmd.AGENT_GUIDE_TEMPLATE
        assert "relay-os/contexts/relay/" in body
        assert "relay launch bootstrap/orient" in body

    assert "Wrote CLAUDE.md, AGENTS.md" in result.output


def test_init_preserves_existing_agent_guides(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _make_git_repo(tmp_path / "company")
    (target / "CLAUDE.md").write_text("# my hand-written guide\n")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    # Pre-existing CLAUDE.md untouched; AGENTS.md still created.
    assert (target / "CLAUDE.md").read_text() == "# my hand-written guide\n"
    assert (target / "AGENTS.md").read_text() == init_cmd.AGENT_GUIDE_TEMPLATE
    assert "Wrote AGENTS.md" in result.output
    assert "CLAUDE.md" not in result.output.split("Wrote ", 1)[1].splitlines()[0]


def test_init_update_tops_up_missing_agent_guides(
    tmp_path: Path, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    relay_os = _seed_local_relay_os(tmp_path)
    monkeypatch.chdir(relay_os)
    # Simulate a repo init'd before agent guides shipped: CLAUDE.md absent,
    # AGENTS.md user-written. Update should create the missing one and
    # leave the existing one alone.
    (tmp_path / "AGENTS.md").write_text("# pre-existing AGENTS\n")

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

    assert (tmp_path / "AGENTS.md").read_text() == "# pre-existing AGENTS\n"
    assert (tmp_path / "CLAUDE.md").read_text() == init_cmd.AGENT_GUIDE_TEMPLATE
    assert "Wrote CLAUDE.md" in result.output


def test_init_commits_agent_guides_in_git_repo(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "company"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    subprocess.run(["git", "-C", str(target), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(target), "config", "user.name", "T"], check=True)
    monkeypatch.setenv("PATH", os.environ["PATH"])
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    tracked = subprocess.run(
        ["git", "-C", str(target), "ls-files"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    assert "CLAUDE.md" in tracked
    assert "AGENTS.md" in tracked


def test_init_writes_pin_file(
    tmp_path: Path, fake_clone, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _make_git_repo(tmp_path / "company")
    monkeypatch.setenv("PATH", "")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
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

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
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

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    host_gi = (target / ".gitignore").read_text()
    assert "node_modules/" in host_gi
    assert "dist/" in host_gi
    assert update_cmd.HOST_GITIGNORE_BEGIN in host_gi
    assert ".claude/skills/relay" in host_gi


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
    package_clone = tmp_path / "package"
    _seed_fake_upstream_for_update(package_clone)
    monkeypatch.setattr(
        update_cmd,
        "packaged_template_root",
        lambda: package_clone / update_cmd.TEMPLATE_SUBPATH,
    )
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
    assert ".agent-skills/" in gi
    # Bootstrap no longer claims user-facing skill/context namespaces.
    assert "skills/eval" not in gi
    assert "skills/retro" not in gi
    assert "skills/relay" not in gi
    assert "contexts/dev" not in gi
    assert "contexts/relay" not in gi
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


# --- running_cli_location / upgrade_global_cli --------------------------------


def _stub_executable_in(venv: Path) -> Path:
    """Create a venv-shaped tree with `bin/python` and return the python path."""
    (venv / "bin").mkdir(parents=True, exist_ok=True)
    py = venv / "bin" / "python"
    py.write_text("#!/bin/sh\n")
    py.chmod(0o755)
    return py


def test_running_cli_location_detects_vendored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    relay_os = tmp_path / "relay-os"
    venv = relay_os / ".relay" / ".venv"
    py = _stub_executable_in(venv)
    monkeypatch.setattr(update_cmd.sys, "executable", str(py))

    kind, where = update_cmd.running_cli_location(relay_os)
    assert kind == "vendored"
    assert where == venv.absolute()


def test_running_cli_location_detects_pipx(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    relay_os = tmp_path / "project" / "relay-os"
    relay_os.mkdir(parents=True)
    pipx_venv = tmp_path / "home" / ".local" / "share" / "pipx" / "venvs" / "relay-os"
    py = _stub_executable_in(pipx_venv)
    (pipx_venv / "pipx_metadata.json").write_text("{}\n")
    monkeypatch.setattr(update_cmd.sys, "executable", str(py))

    kind, where = update_cmd.running_cli_location(relay_os)
    assert kind == "pipx"
    assert where == pipx_venv.absolute()


def test_running_cli_location_falls_through_to_other(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    relay_os = tmp_path / "project" / "relay-os"
    relay_os.mkdir(parents=True)
    other_venv = tmp_path / "some-other-venv"
    py = _stub_executable_in(other_venv)
    monkeypatch.setattr(update_cmd.sys, "executable", str(py))

    kind, where = update_cmd.running_cli_location(relay_os)
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
    relay_os = tmp_path / "project" / "relay-os"
    relay_os.mkdir(parents=True)

    # Mimic Homebrew's framework Python at a totally unrelated path.
    host_py_dir = tmp_path / "opt" / "homebrew" / "Cellar" / "python@3.14" / "bin"
    host_py_dir.mkdir(parents=True)
    host_py = host_py_dir / "python3.14"
    host_py.write_text("#!/bin/sh\n")
    host_py.chmod(0o755)

    pipx_venv = tmp_path / "home" / ".local" / "pipx" / "venvs" / "relay-os"
    (pipx_venv / "bin").mkdir(parents=True)
    (pipx_venv / "pipx_metadata.json").write_text("{}\n")
    pipx_python = pipx_venv / "bin" / "python"
    pipx_python.symlink_to(host_py)
    monkeypatch.setattr(update_cmd.sys, "executable", str(pipx_python))

    kind, where = update_cmd.running_cli_location(relay_os)
    assert kind == "pipx", (
        "symlink resolution would land in homebrew Cellar; detection must "
        "stay on the unresolved venv path so pipx_metadata.json is found"
    )
    assert where == pipx_venv.absolute()


def test_upgrade_global_cli_vendored_is_noop() -> None:
    assert update_cmd.upgrade_global_cli("vendored") == ("vendored", None)


def test_upgrade_global_cli_other_is_noop() -> None:
    assert update_cmd.upgrade_global_cli("other") == ("other", None)


def test_upgrade_global_cli_pipx_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(update_cmd.shutil, "which", lambda name: "/usr/bin/pipx")
    captured: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        captured.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, stdout="upgraded relay 0.2.0 -> 0.3.0\n", stderr="")

    monkeypatch.setattr(update_cmd.subprocess, "run", fake_run)

    status, detail = update_cmd.upgrade_global_cli("pipx")
    assert status == "pipx-upgraded"
    assert detail == "upgraded relay 0.2.0 -> 0.3.0"
    assert captured == [["/usr/bin/pipx", "upgrade", "relay-os"]]


def test_upgrade_global_cli_pipx_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(update_cmd.shutil, "which", lambda name: "/usr/bin/pipx")

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boom\n")

    monkeypatch.setattr(update_cmd.subprocess, "run", fake_run)

    status, detail = update_cmd.upgrade_global_cli("pipx")
    assert status == "pipx-failed"
    assert detail == "boom"


def test_upgrade_global_cli_pipx_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(update_cmd.shutil, "which", lambda name: None)
    assert update_cmd.upgrade_global_cli("pipx") == ("pipx-missing", None)


def test_init_update_warns_when_running_relay_is_not_vendored(
    tmp_path: Path, fake_venv, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The colleague-on-macOS bug: pipx install runs the same `init --update`,
    but `sys.executable` lives in the pipx venv, not the vendored one. We must
    surface that — and try to upgrade the pipx install for them."""
    relay_os = _seed_local_relay_os(tmp_path)
    monkeypatch.chdir(relay_os)

    pipx_venv = tmp_path / "home" / ".local" / "share" / "pipx" / "venvs" / "relay"
    py = _stub_executable_in(pipx_venv)
    (pipx_venv / "pipx_metadata.json").write_text("{}\n")
    monkeypatch.setattr(update_cmd.sys, "executable", str(py))

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
        if cmd[:1] == ["/usr/bin/pipx"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="upgraded\n", stderr="")
        return real_run(cmd, **kwargs)

    monkeypatch.setattr(update_cmd.subprocess, "run", fake_run)
    monkeypatch.setattr(update_cmd.shutil, "which", lambda name: "/usr/bin/pipx")

    result = CliRunner().invoke(app, ["init", "--update"])
    assert result.exit_code == 0, result.output
    assert "Upgraded global `relay` (pipx)" in result.output


def test_init_update_silent_when_running_vendored(
    tmp_path: Path, fake_venv, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When sys.executable is the vendored venv, no warning, no pipx call."""
    relay_os = _seed_local_relay_os(tmp_path)
    monkeypatch.chdir(relay_os)

    vendored_venv = relay_os / ".relay" / ".venv"
    py = _stub_executable_in(vendored_venv)
    monkeypatch.setattr(update_cmd.sys, "executable", str(py))

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
    assert "global `relay`" not in result.output
    assert "pipx" not in result.output


# --- relay init --update --all (multi-repo sweep) -----------------------------


def _make_update_fake_run(real_run):
    """A `subprocess.run` stub that seeds a fake upstream on `git clone`.

    Mirrors the inline `fake_run` the single-repo update tests use, including
    the shared `relay-init-update-` clone-dir prefix (the `--all` sweep clones
    into `relay-init-update-all-`, which still matches that substring).
    """

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

    return fake_run


def test_all_flag_requires_update(tmp_path: Path) -> None:
    """`--all` without `--update` is a loud error — there is no bulk create."""
    result = CliRunner().invoke(app, ["init", "--all", str(tmp_path)])
    assert result.exit_code == 2
    assert "--all only applies with --update" in result.output
    assert "relay init --update --all <path>" in result.output


def test_update_all_requires_explicit_path() -> None:
    """`--all` must name its scan root; defaulting to cwd is too easy to misuse."""
    result = CliRunner().invoke(app, ["init", "--update", "--all"])
    assert result.exit_code == 2
    assert "--all requires an explicit PATH" in result.output
    assert "relay init --update --all <path>" in result.output


def test_discover_relay_repos_finds_nested_and_skips_non_repos(tmp_path: Path) -> None:
    """Discovery finds real relay repos at any depth and ignores look-alikes."""
    repo_a = _seed_local_relay_os(tmp_path / "alpha")
    repo_b = _seed_local_relay_os(tmp_path / "nested" / "beta")
    # A directory literally named `relay-os` but with no relay.toml: not a repo.
    (tmp_path / "decoy" / "relay-os").mkdir(parents=True)
    # A relay repo buried in a skipped noise dir is never descended into.
    buried = tmp_path / "alpha" / "node_modules" / "pkg" / "relay-os"
    buried.mkdir(parents=True)
    (buried / "relay.toml").write_text("version = 1\n")

    found = init_cmd._discover_relay_repos(tmp_path)

    assert found == sorted([repo_a, repo_b])


def test_discover_relay_repos_does_not_descend_into_found_repo(tmp_path: Path) -> None:
    """A relay-os nested inside a real relay repo is part of that repo, not a sibling.

    Catches the case where scanning ~/Code surfaces the Relay source repo's own
    fixture (`example/relay-os/`) and packaged template
    (`src/relay/resources/templates/relay-os/`) as if they were standalone repos.
    """
    repo = _seed_local_relay_os(tmp_path / "relay")
    # Fixture seeded under the repo — looks like a relay repo (has relay.toml)
    # but is part of the parent repo's source tree.
    fixture = tmp_path / "relay" / "example" / "relay-os"
    fixture.mkdir(parents=True)
    (fixture / "relay.toml").write_text("version = 1\n")
    # Packaged template at a deeper path under the same parent repo.
    template = tmp_path / "relay" / "src" / "relay" / "resources" / "templates" / "relay-os"
    template.mkdir(parents=True)
    (template / "relay.toml").write_text("version = 1\n")

    found = init_cmd._discover_relay_repos(tmp_path)

    assert found == [repo]


def test_update_all_no_repos_found_exits_nonzero(tmp_path: Path) -> None:
    """An empty scan root is a loud failure, not a silent no-op."""
    result = CliRunner().invoke(app, ["init", "--update", "--all", str(tmp_path)])
    assert result.exit_code == 1
    assert "No relay repos found" in result.output


def test_update_all_refreshes_every_repo(
    tmp_path: Path, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`init --update --all` refreshes every relay repo found under PATH."""
    repo_a = _seed_local_relay_os(tmp_path / "a")
    repo_b = _seed_local_relay_os(tmp_path / "sub" / "b")
    package_clone = tmp_path / "package"
    _seed_fake_upstream_for_update(package_clone)
    monkeypatch.setattr(
        update_cmd,
        "packaged_template_root",
        lambda: package_clone / update_cmd.TEMPLATE_SUBPATH,
    )
    monkeypatch.setattr(
        update_cmd.subprocess, "run", _make_update_fake_run(subprocess.run)
    )

    result = CliRunner().invoke(app, ["init", "--update", "--all", str(tmp_path)])
    assert result.exit_code == 0, result.output

    assert "Found 2 relay repo(s)" in result.output
    assert "Updated 2 of 2 repo(s)." in result.output
    for relay_os in (repo_a, repo_b):
        assert (
            (relay_os / ".relay" / "src" / "relay" / "cli.py").read_text()
            == "# NEW vendored cli\n"
        )
        assert (
            (relay_os / "bootstrap" / "create" / "ticket.md").read_text()
            == "NEW bootstrap shim\n"
        )
        assert (relay_os / ".relay" / "RELAY_PIN").is_file()
    # install_venv ran exactly once per repo.
    assert sorted(fake_venv) == sorted([repo_a, repo_b])


def test_update_all_continues_past_a_failing_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One repo's failure is reported but does not abort the sweep."""
    repo_a = _seed_local_relay_os(tmp_path / "a")
    repo_b = _seed_local_relay_os(tmp_path / "b")
    monkeypatch.setattr(
        update_cmd.subprocess, "run", _make_update_fake_run(subprocess.run)
    )

    swept: list[Path] = []

    def flaky_refresh(
        relay_os: Path,
        clone_dir: Path,
        *,
        repo_url: str | None = None,
    ) -> init_cmd._UpdateResult:
        swept.append(relay_os)
        if relay_os == repo_a:
            raise RuntimeError("boom")
        return init_cmd._UpdateResult(
            sha=FAKE_SHA,
            source_checkout=False,
            copied=[],
            pruned=[],
            wired_agents=[],
            blocked_agents=[],
            host_gitignore_changed=False,
            written_guides=[],
            retrofitted=[],
            managed_skills=ManagedSkillSummary(),
        )

    monkeypatch.setattr(init_cmd, "_refresh_one", flaky_refresh)

    result = CliRunner().invoke(app, ["init", "--update", "--all", str(tmp_path)])

    assert result.exit_code == 1
    assert swept == sorted([repo_a, repo_b])  # both attempted despite the failure
    assert "boom" in result.output
    assert "Updated 1 of 2 repo(s)." in result.output


# --- external dependency check --------------------------------------------------
#
# `relay init` fails loud when a required external CLI (`git`/`gh`/`op`) is not
# on PATH. Captured before the autouse `_stub_init_dep_check` fixture replaces
# the module attribute, so these tests exercise the real implementation.
_real_dep_check = init_cmd._check_external_dependencies


def _which_missing(missing: set[str]):
    """A `shutil.which` stand-in that reports `missing` tools as absent."""
    return lambda name: None if name in missing else f"/usr/bin/{name}"


def test_dep_check_passes_when_all_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("relay.commands.init.shutil.which", _which_missing(set()))
    _real_dep_check()  # must not raise


def test_dep_check_ignores_missing_op(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """`op` is not required at init (it's enforced at launch when a ticket
    actually needs an `op://` secret), so a missing `op` must not crash init."""
    monkeypatch.setattr("relay.commands.init.shutil.which", _which_missing({"op"}))
    _real_dep_check()  # must not raise


def test_dep_check_crashes_on_missing_gh(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr("relay.commands.init.shutil.which", _which_missing({"gh"}))
    with pytest.raises(SystemExit) as exc:
        _real_dep_check()
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "gh" in err and "cli.github.com" in err
    assert "op" not in err  # the optional tool isn't dragged into the crash


def test_dep_check_crashes_on_missing_git(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr("relay.commands.init.shutil.which", _which_missing({"git"}))
    with pytest.raises(SystemExit) as exc:
        _real_dep_check()
    assert exc.value.code == 2
    assert "git" in capsys.readouterr().err


def test_dep_check_reports_all_required_missing_together(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(
        "relay.commands.init.shutil.which", _which_missing({"git", "gh", "op"})
    )
    with pytest.raises(SystemExit):
        _real_dep_check()
    err = capsys.readouterr().err
    # Both required-at-init tools are reported; the optional `op` is omitted.
    assert "git" in err and "gh" in err
    assert "op" not in err


def test_init_bails_before_scaffolding_when_required_dep_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing required dep (gh) stops `relay init` before it writes anything."""
    # Restore the real check (autouse no-ops it), then make `gh` absent.
    monkeypatch.setattr(init_cmd, "_check_external_dependencies", _real_dep_check)
    monkeypatch.setattr("relay.commands.init.shutil.which", _which_missing({"gh"}))

    target = tmp_path / "fresh"
    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])

    assert result.exit_code == 2
    assert "gh" in result.output
    assert not (target / "relay-os").exists()  # bailed before scaffolding
