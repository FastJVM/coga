"""`coga init` — creates coga/ from package templates, or refreshes one."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

import coga.agent_skills as agent_skills
from coga.cli import app
from coga.commands import init as init_cmd
from coga.commands import update as update_cmd
from coga.config import load_config
from coga.managed_skills import ManagedSkillError, ManagedSkillSummary
from coga.notification import post
from coga.skill_manager import SkillResult


_PACKAGED_COGA_TOML = (
    Path(__file__).resolve().parents[1]
    / "src" / "coga" / "resources" / "templates" / "coga" / "coga.toml"
)


def _fake_package_skill_root(
    monkeypatch: pytest.MonkeyPatch, root: Path, missing: Path
) -> None:
    def fake_packaged_template_path(*parts: str) -> Path:
        if parts == ("bootstrap", "skills"):
            return root
        return missing

    monkeypatch.setattr(
        agent_skills, "packaged_template_path", fake_packaged_template_path
    )


EXPECTED_FILES = {
    "coga/.gitignore",
    "coga/coga.toml",
    "coga/context.md",
    "coga/contexts/_template/SKILL.md",
    "coga/skills/_template/SKILL.md",
    "coga/skills/direct/body/SKILL.md",
    "coga/workflows/_template.md",
    "coga/recurring/_template/ticket.md",
    "coga/recurring/autoclose-merged/ticket.md",
    "coga/recurring/dream/ticket.md",
    "coga/recurring/skill-update/ticket.md",
    "coga/tasks/_template/ticket.md",
    "coga/tasks/coga-build.md",
    # Single-file format: the repo-global audit log + its union-merge attribute
    # ship at the coga root; tasks no longer carry per-dir blackboard.md/log.md.
    "coga/log.md",
    "coga/.gitattributes",
    "coga/workflows/autoclose-merged/sweep.md",
    "coga/workflows/direct/body.md",
    "coga/workflows/skill-update/run.md",
    "coga/workflows/build/onboarding.md",
}


def _make_git_repo(target: Path) -> Path:
    """Mark `target` as a git repo so it clears init's git-repo precondition.

    `coga init` refuses to write coga/ into a non-git dir, so tests that
    exercise a successful init must look like a repo. A bare `.git` dir is enough
    for the filesystem-level check — no real `git init` is needed for tests that
    don't assert the commit itself (those still init + configure git by hand).
    """
    target.mkdir(parents=True, exist_ok=True)
    (target / ".git").mkdir(exist_ok=True)
    return target


def _seed_fake_templates(templates: Path) -> None:
    """Mimic the packaged coga template tree (`templates/coga` resources)."""
    templates.mkdir(parents=True)
    (templates / ".gitignore").write_text(
        "coga.local.toml\n.coga/\n.agent-skills/\n"
        "**/_template/\n**/_template.md\n"
    )
    (templates / "coga.toml").write_text("version = 1\n")
    (templates / "context.md").write_text("context\n")
    # Packaged skills + canonical coga/* contexts live under bootstrap/ in the
    # package resource tree, not in initialized repos.
    (templates / "bootstrap" / "skills" / "bootstrap" / "ticket").mkdir(parents=True)
    (templates / "bootstrap" / "skills" / "bootstrap" / "ticket" / "SKILL.md").write_text(
        "bootstrap/ticket skill\n"
    )
    for name in ("orient", "project", "ticket"):
        (templates / "bootstrap" / name).mkdir(parents=True)
        (templates / "bootstrap" / name / "ticket.md").write_text(
            f"{name} bootstrap ticket\n"
        )
    (templates / "bootstrap" / "skills" / "retro" / "done-ticket").mkdir(parents=True)
    (templates / "bootstrap" / "skills" / "retro" / "done-ticket" / "SKILL.md").write_text(
        "retro/done-ticket skill\n"
    )
    (templates / "bootstrap" / "skills" / "coga" / "autoclose" / "sweep").mkdir(
        parents=True
    )
    (
        templates
        / "bootstrap"
        / "skills"
        / "coga"
        / "autoclose"
        / "sweep"
        / "SKILL.md"
    ).write_text("---\nname: coga/autoclose/sweep\nscript: run.py\n---\nsweep\n")
    (
        templates
        / "bootstrap"
        / "skills"
        / "coga"
        / "autoclose"
        / "sweep"
        / "run.py"
    ).write_text("#!/usr/bin/env python3\n")
    for ctx in ("architecture", "principles", "cli"):
        (templates / "bootstrap" / "contexts" / "coga" / ctx).mkdir(parents=True)
        (templates / "bootstrap" / "contexts" / "coga" / ctx / "SKILL.md").write_text(
            f"coga/{ctx} context\n"
        )
    (templates / "bootstrap" / "contexts" / "coga" / "sync").mkdir(parents=True)
    (templates / "bootstrap" / "contexts" / "coga" / "sync" / "SKILL.md").write_text(
        "coga/sync context\n"
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
    # Coga-owned recurring battery — no `_` prefix.
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
    (templates / "tasks" / "coga-build").mkdir(parents=True, exist_ok=True)
    (templates / "tasks" / "coga-build" / "ticket.md").write_text(
        "---\n"
        "title: coga-build\n"
        "status: active\n"
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
        "\n"
        "<!-- coga:blackboard -->\n"
        "\n"
        "notepad\n"
    )
    # Single-file format: the audit log + its union-merge attribute ship at the
    # coga root, not as per-task siblings.
    (templates / "log.md").write_text("")
    (templates / ".gitattributes").write_text("/log.md merge=union\n")
    (templates / "workflows" / "autoclose-merged").mkdir(
        parents=True, exist_ok=True
    )
    (templates / "workflows" / "autoclose-merged" / "sweep.md").write_text(
        "autoclose merged workflow\n"
    )


FAKE_VERSION = "9.9.9"


def _fake_install_source(
    requires_python: str | None = None,
) -> update_cmd.InstallSource:
    return update_cmd.InstallSource(
        kind="release",
        pip_spec=f"coga=={FAKE_VERSION}",
        display=f"coga=={FAKE_VERSION} (PyPI)",
        requires_python=requires_python,
    )


FAKE_SOURCE = _fake_install_source()


@pytest.fixture
def fake_vendor(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Fake the packaged templates and the vendor source/version resolution.

    Resolving the install source and reading the installed version back from
    the venv both depend on the environment (installed dist, venv python);
    init tests pin them to `FAKE_SOURCE` / `FAKE_VERSION` instead.
    """
    package_templates = tmp_path / "package" / "templates" / "coga"
    _seed_fake_templates(package_templates)
    monkeypatch.setattr(update_cmd, "packaged_template_root", lambda: package_templates)
    monkeypatch.setattr(init_cmd, "resolve_install_source", lambda: FAKE_SOURCE)
    monkeypatch.setattr(init_cmd, "vendored_cli_version", lambda venv_dir: FAKE_VERSION)


@pytest.fixture
def fake_venv(monkeypatch: pytest.MonkeyPatch):
    """Stub out `install_venv` — actual pip-install is too slow + needs network for tests."""
    calls: list[Path] = []

    def fake_install(
        coga_os: Path, source: update_cmd.InstallSource | None = None
    ) -> Path:
        calls.append(coga_os)
        venv_bin = coga_os / ".coga" / ".venv" / "bin"
        venv_bin.mkdir(parents=True, exist_ok=True)
        # Stand in for the pip-generated console script the wrapper symlinks to.
        coga_script = venv_bin / "coga"
        coga_script.write_text("#!/bin/sh\necho fake venv coga\n")
        coga_script.chmod(0o755)
        return coga_script.parent.parent

    monkeypatch.setattr(init_cmd, "install_venv", fake_install)
    return calls


@pytest.fixture(autouse=True)
def fake_managed_skill_sync(monkeypatch: pytest.MonkeyPatch):
    state = SimpleNamespace(
        install_calls=[],
        install_summary=ManagedSkillSummary(),
    )

    def fake_install(coga_os: Path) -> ManagedSkillSummary:
        state.install_calls.append(coga_os)
        return state.install_summary

    monkeypatch.setattr(init_cmd, "install_managed_skills", fake_install)
    return state


def _make_fake_checkout(root: Path, requires_python: str = ">=3.11") -> Path:
    """A directory shaped like a coga source checkout (pyproject naming coga)."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(
        f"[project]\nname = 'coga'\nrequires-python = \"{requires_python}\"\n"
    )
    return root


def test_resolve_install_source_env_override_checkout_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """COGA_REPO_URL pointing at a local checkout installs from that path."""
    checkout = _make_fake_checkout(tmp_path / "checkout")
    monkeypatch.setenv("COGA_REPO_URL", str(checkout))

    source = update_cmd.resolve_install_source()

    assert source.kind == "checkout"
    assert source.pip_spec == str(checkout)
    assert source.display == str(checkout)
    assert source.requires_python == ">=3.11"


def test_resolve_install_source_env_override_rejects_non_coga_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A directory override that isn't a coga checkout fails loud, never installs."""
    monkeypatch.setenv("COGA_REPO_URL", str(tmp_path))

    with pytest.raises(SystemExit) as exc:
        update_cmd.resolve_install_source()

    assert exc.value.code == 2
    assert "not a coga source checkout" in capsys.readouterr().err


def test_resolve_install_source_env_override_git_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A URL override becomes a pip git requirement (git+ prefix added)."""
    monkeypatch.setenv("COGA_REPO_URL", "https://github.com/FastJVM/coga")

    source = update_cmd.resolve_install_source()

    assert source.kind == "url"
    assert source.pip_spec == "git+https://github.com/FastJVM/coga"
    # No requires-python is knowable pre-install; pip enforces it instead.
    assert source.requires_python is None


def test_resolve_install_source_env_override_keeps_pip_git_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COGA_REPO_URL", "git+ssh://git@github.com/FastJVM/coga.git")

    source = update_cmd.resolve_install_source()

    assert source.pip_spec == "git+ssh://git@github.com/FastJVM/coga.git"


def test_resolve_install_source_redacts_credentialed_url_in_display(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "COGA_REPO_URL", "https://coga:TOKEN@github.com/FastJVM/coga.git"
    )

    source = update_cmd.resolve_install_source()

    assert source.display == "https://github.com/FastJVM/coga.git"
    assert "TOKEN" in source.pip_spec  # pip still gets the credentials
    assert "TOKEN" not in source.display


def test_resolve_install_source_prefers_running_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An editable/in-tree run vendors from its own source checkout."""
    checkout = _make_fake_checkout(tmp_path / "checkout")
    monkeypatch.delenv("COGA_REPO_URL", raising=False)
    monkeypatch.setattr(update_cmd, "_running_checkout_root", lambda: checkout)

    source = update_cmd.resolve_install_source()

    assert source.kind == "checkout"
    assert source.pip_spec == str(checkout)


def test_resolve_install_source_wheel_install_pins_running_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A wheel install vendors `coga==<running version>` — never upstream main."""
    monkeypatch.delenv("COGA_REPO_URL", raising=False)
    monkeypatch.setattr(update_cmd, "_running_checkout_root", lambda: None)
    monkeypatch.setattr(update_cmd, "_pkg_version", lambda name: "1.2.3")
    monkeypatch.setattr(update_cmd, "_running_requires_python", lambda: ">=3.11")

    source = update_cmd.resolve_install_source()

    assert source.kind == "release"
    assert source.pip_spec == "coga==1.2.3"
    assert source.display == "coga==1.2.3 (PyPI)"
    assert source.requires_python == ">=3.11"


def test_running_checkout_root_finds_this_checkout() -> None:
    """The dev-suite run imports coga from this repo's src/coga — detect it."""
    root = update_cmd._running_checkout_root()
    assert root == Path(__file__).resolve().parents[1]


def test_write_pin_records_source_and_version(tmp_path: Path) -> None:
    coga_os = tmp_path / "coga"

    update_cmd.write_pin(coga_os, FAKE_SOURCE, FAKE_VERSION)

    assert (coga_os / ".coga" / "COGA_PIN").read_text().splitlines() == [
        FAKE_SOURCE.display,
        FAKE_VERSION,
    ]
    assert update_cmd.read_pin(coga_os) == FAKE_VERSION
    assert update_cmd.read_pin_source(coga_os) == FAKE_SOURCE.display


def test_vendored_cli_version_reads_venv(tmp_path: Path) -> None:
    venv_dir = tmp_path / ".venv"
    (venv_dir / "bin").mkdir(parents=True)
    fake_python = venv_dir / "bin" / "python"
    fake_python.write_text("#!/bin/sh\necho 1.2.3\n")
    fake_python.chmod(0o755)

    assert update_cmd.vendored_cli_version(venv_dir) == "1.2.3"


def test_vendored_cli_version_fails_loud_without_venv_python(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc:
        update_cmd.vendored_cli_version(tmp_path / ".venv")

    assert exc.value.code == 2
    assert "Cannot determine the coga version installed" in capsys.readouterr().err


def test_vendored_cli_version_fails_loud_when_probe_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    venv_dir = tmp_path / ".venv"
    (venv_dir / "bin").mkdir(parents=True)
    fake_python = venv_dir / "bin" / "python"
    fake_python.write_text("#!/bin/sh\necho broken metadata >&2\nexit 1\n")
    fake_python.chmod(0o755)

    with pytest.raises(SystemExit) as exc:
        update_cmd.vendored_cli_version(venv_dir)

    assert exc.value.code == 2
    assert "broken metadata" in capsys.readouterr().err


# --- fresh init ---------------------------------------------------------------


def test_init_into_empty_dir(
    tmp_path: Path, fake_vendor, fake_venv, fake_managed_skill_sync
) -> None:
    target = _make_git_repo(tmp_path / "company")

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    for rel in EXPECTED_FILES:
        assert (target / rel).is_file(), f"missing {rel}"
    assert not (target / "coga" / "bootstrap").exists()
    assert not (target / "coga" / "skills" / "retro").exists()
    assert not (target / "coga" / "skills" / "coga").exists()
    assert not (target / "coga" / "contexts" / "dev").exists()
    assert not (target / "coga" / "contexts" / "coga").exists()
    assert (
        target / "coga" / ".agent-skills" / "retro" / "done-ticket"
    ).is_symlink()
    assert (
        target / "coga" / ".agent-skills" / "coga" / "autoclose" / "sweep"
    ).is_symlink()

    assert "version = 1" in (target / "coga" / "coga.toml").read_text()
    assert fake_managed_skill_sync.install_calls == [target / "coga"]


@pytest.mark.parametrize(
    "exc", [RuntimeError("venv build failed"), KeyboardInterrupt()]
)
def test_failed_init_rolls_back_partial_coga_os(
    tmp_path: Path,
    fake_vendor,
    monkeypatch: pytest.MonkeyPatch,
    exc: BaseException,
) -> None:
    """A first init that dies after coga/ is created must leave nothing
    behind — for a normal error and a Ctrl-C alike (hence `except BaseException`)
    — so re-running isn't wedged behind an "already exists" refusal sitting on
    a half-built venv / missing user.

    Ticket: install/init-does-not-persist-user-then-blocks-on-reinit.
    """
    target = _make_git_repo(tmp_path / "company")
    coga_os = target / "coga"

    def boom(_coga_os: Path, _source=None):
        # copy_fresh_templates has already created coga/ by now — that's the
        # half-built state the old code stranded.
        assert coga_os.exists(), "coga/ should exist before the failing step"
        raise exc

    monkeypatch.setattr(init_cmd, "install_venv", boom)

    with pytest.raises(type(exc)):
        init_cmd._do_init(target, user="tester")

    assert not coga_os.exists(), "partial coga/ left behind — rollback didn't fire"


def test_packaged_template_first_run_works_without_slack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The shipped coga.toml lets a stranger run commands with no Slack set up.

    Reads the real packaged template (the file `coga init` ships, not a fake
    fixture) into a repo with `SLACK_WEBHOOK_URL` unset, then proves the
    first-run posture: it selects no notification channels, `post()` is
    suppressed instead of crash-loud, and a first `coga create` succeeds.
    """
    repo = tmp_path / "coga"
    repo.mkdir()
    shutil.copy(_PACKAGED_COGA_TOML, repo / "coga.toml")
    (repo / "coga.local.toml").write_text('user = "marc"\n')
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)

    text = (repo / "coga.toml").read_text()
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
    fake_vendor,
    fake_venv,
    fake_managed_skill_sync,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _make_git_repo(tmp_path / "company")

    def fake_install(coga_os: Path) -> ManagedSkillSummary:
        fake_managed_skill_sync.install_calls.append(coga_os)
        skill = coga_os / "skills" / "coga" / "calendar-reminder"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: coga/calendar-reminder\n---\n")
        return ManagedSkillSummary(
            [
                SkillResult(
                    name="coga/calendar-reminder",
                    source_type="github",
                    status="installed",
                    message="installed coga/calendar-reminder through gh skill",
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
        target / "coga" / ".agent-skills" / "coga" / "calendar-reminder"
    ).is_symlink()
    assert fake_managed_skill_sync.install_calls == [target / "coga"]


def test_init_prints_one_compact_warning_for_old_gh_skips(
    tmp_path: Path,
    fake_vendor,
    fake_venv,
    fake_managed_skill_sync,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _make_git_repo(tmp_path / "company")

    def old_gh_result(name: str) -> SkillResult:
        return SkillResult(
            name=name,
            source_type="github",
            status="skipped-old-gh",
            message=init_cmd.GH_SKILL_REQUIRED,
            details={
                "source": "google/agents-cli",
                "required": False,
                "remediation": f"coga skill install google/agents-cli {name}",
            },
        )

    fake_managed_skill_sync.install_summary = ManagedSkillSummary(
        [old_gh_result("tools/one"), old_gh_result("tools/two")]
    )

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    assert "Managed skills: skipped-old-gh=2" in result.output
    assert "Warning: skipped 2 optional managed skills" in result.output
    assert "  Skipped: tools/one, tools/two" in result.output
    # One compact upgrade line, not one warning per skill.
    assert result.output.count("GitHub CLI 2.90.0+") == 1
    assert "failed" not in result.output


def test_init_notes_skipped_no_access_managed_skills(
    tmp_path: Path,
    fake_vendor,
    fake_venv,
    fake_managed_skill_sync,
) -> None:
    target = _make_git_repo(tmp_path / "company")
    fake_managed_skill_sync.install_summary = ManagedSkillSummary(
        [
            SkillResult(
                name=f"tools/{name}",
                source_type="github",
                status="skipped-no-access",
                message=(
                    "optional skill skipped — owner/private is not accessible "
                    "with your GitHub credentials (HTTP 404: Not Found)"
                ),
                details={
                    "source": "owner/private",
                    "required": False,
                    "remediation": f"coga skill install owner/private tools/{name}",
                    "reason": "HTTP 404: Not Found",
                },
            )
            for name in ("one", "two")
        ]
    )

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    assert "Managed skills: skipped-no-access=2" in result.output
    # One consolidated note per source — not a warning per skill.
    assert (
        "Note: skipped 2 optional managed skills from owner/private" in result.output
    )
    assert "Coga works without them" in result.output
    assert "gh auth login" in result.output
    assert "Warning: optional managed skill" not in result.output


def test_init_notes_rate_limited_managed_skills(
    tmp_path: Path,
    fake_vendor,
    fake_venv,
    fake_managed_skill_sync,
) -> None:
    target = _make_git_repo(tmp_path / "company")
    reason = "HTTP 403: API rate limit exceeded for 203.0.113.9."
    fake_managed_skill_sync.install_summary = ManagedSkillSummary(
        [
            SkillResult(
                name=f"tools/{name}",
                source_type="github",
                status="skipped-rate-limited",
                message=(
                    "optional skill skipped — GitHub API rate limit reached "
                    f"while fetching from google/agents-cli ({reason})"
                ),
                details={
                    "source": "google/agents-cli",
                    "required": False,
                    "remediation": "gh auth login",
                    "reason": reason,
                },
            )
            for name in ("one", "two")
        ]
    )

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    assert "Managed skills: skipped-rate-limited=2" in result.output
    # One consolidated note per source — not a warning per skill.
    assert (
        "Note: skipped 2 optional managed skills from google/agents-cli"
        in result.output
    )
    assert "Coga works without them" in result.output
    assert "gh auth login" in result.output
    assert "Warning: optional managed skill" not in result.output


def test_init_tells_user_to_install_missing_gh_for_managed_skills(
    tmp_path: Path,
    fake_vendor,
    fake_venv,
    fake_managed_skill_sync,
) -> None:
    target = _make_git_repo(tmp_path / "company")
    fake_managed_skill_sync.install_summary = ManagedSkillSummary(
        [
            SkillResult(
                name="tools/example",
                source_type="github",
                status="skipped-no-access",
                message="optional skill skipped",
                details={
                    "source": "owner/private",
                    "required": False,
                    "remediation": "coga skill install owner/private tools/example",
                    "reason": "GitHub CLI (`gh`) is not installed",
                },
            )
        ]
    )

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])

    assert result.exit_code == 0, result.output
    assert "Install GitHub CLI 2.90.0+ from https://cli.github.com" in result.output
    assert "authenticate with `gh auth login`" in result.output


def test_init_fails_loud_when_required_managed_skill_fails(
    tmp_path: Path, fake_vendor, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _make_git_repo(tmp_path / "company")

    def fail_required(_: Path) -> ManagedSkillSummary:
        raise ManagedSkillError(
            "Required managed skill `coga/core` failed from example/repo: missing gh\n"
            "Remediation: coga skill install example/repo coga/core"
        )

    monkeypatch.setattr(init_cmd, "install_managed_skills", fail_required)

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 2
    assert "Required managed skill `coga/core` failed from example/repo" in result.output
    assert "Remediation: coga skill install example/repo coga/core" in result.output


def test_init_vendors_cli_and_links_wrapper_to_venv(
    tmp_path: Path, fake_vendor, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _make_git_repo(tmp_path / "company")
    monkeypatch.setenv("PATH", "")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    assert fake_venv == [target / "coga"]  # install_venv called once
    # The CLI installs into the venv from the running distribution — no source
    # copy is vendored into `.coga/` anymore.
    assert not (target / "coga" / ".coga" / "src").exists()
    assert not (target / "coga" / ".coga" / "pyproject.toml").exists()

    wrapper = target / "coga" / ".coga" / "bin" / "coga"
    venv_coga = target / "coga" / ".coga" / ".venv" / "bin" / "coga"
    assert wrapper.is_symlink()
    # Relative symlink so the repo is portable.
    assert Path(wrapper.readlink()) == Path("..") / ".venv" / "bin" / "coga"
    assert wrapper.resolve() == venv_coga.resolve()

    assert "Add the bin dir to your PATH" in result.output


def test_init_writes_captured_user_name_to_local_toml(
    tmp_path: Path, fake_vendor, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _make_git_repo(tmp_path / "company")
    monkeypatch.setenv("PATH", "")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    # Surrounding whitespace is stripped, same as the prompt path.
    result = CliRunner().invoke(app, ["init", str(target), "--user", "  marc  "])
    assert result.exit_code == 0, result.output

    local_toml = target / "coga" / "coga.local.toml"
    assert local_toml.is_file()
    text = local_toml.read_text()
    # The `--user` value lands in `user` — a fresh init never leaves it empty.
    assert 'user = "marc"' in text
    assert 'user = ""' not in text
    assert "[secrets]" in text  # commented example present
    assert 'with user = "marc"' in result.output


def test_init_without_user_fails_loud(
    tmp_path: Path, fake_vendor, fake_venv
) -> None:
    """A fresh `coga init` with no `--user` fails loud rather than guessing a
    name — coga never derives the operator's name. Nothing is written."""
    target = _make_git_repo(tmp_path / "company")

    result = CliRunner().invoke(app, ["init", str(target)])
    assert result.exit_code == 2
    assert "needs your name" in result.output
    assert "--user" in result.output
    assert not (target / "coga").exists()


def test_init_rejects_invalid_user(tmp_path: Path, fake_vendor, fake_venv) -> None:
    """An invalid `--user` (a quote or backslash, which would break the `user`
    line in coga.local.toml) is rejected up front, before anything is
    written."""
    target = tmp_path / "company"
    target.mkdir()

    result = CliRunner().invoke(app, ["init", str(target), "--user", 'a"b'])
    assert result.exit_code == 2
    assert "quotes or backslashes" in result.output
    assert not (target / "coga").exists()


def test_init_installs_shim_when_local_bin_on_path(
    tmp_path: Path, fake_vendor, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_home = tmp_path / "home"
    local_bin = fake_home / ".local" / "bin"
    local_bin.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("PATH", f"{local_bin}:/usr/bin")

    target = _make_git_repo(tmp_path / "company")
    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    shim = local_bin / "coga"
    assert shim.is_symlink()
    expected = (target / "coga" / ".coga" / ".venv" / "bin" / "coga").resolve()
    assert shim.resolve() == expected
    assert "is on your PATH via" in result.output
    assert "Add the bin dir to your PATH" not in result.output


def test_init_skips_shim_when_target_exists(
    tmp_path: Path, fake_vendor, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_home = tmp_path / "home"
    local_bin = fake_home / ".local" / "bin"
    local_bin.mkdir(parents=True)
    pre_existing = local_bin / "coga"
    pre_existing.write_text("#!/bin/sh\n# pre-existing\n")
    pre_existing.chmod(0o755)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("PATH", f"{local_bin}:/usr/bin")

    target = _make_git_repo(tmp_path / "company")
    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    # Pre-existing file untouched and we don't nag the user about PATH —
    # `shutil.which` finds their existing `coga`, so init confirms that
    # instead of telling them to munge PATH.
    assert pre_existing.read_text() == "#!/bin/sh\n# pre-existing\n"
    assert "Add the bin dir to your PATH" not in result.output
    assert "is already on your PATH at" in result.output


def test_init_into_non_empty_dir_is_fine(tmp_path: Path, fake_vendor, fake_venv) -> None:
    target = _make_git_repo(tmp_path / "existing-repo")
    (target / "README.md").write_text("hi")
    (target / "src").mkdir()

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output
    assert (target / "coga" / "coga.toml").is_file()
    assert (target / "README.md").read_text() == "hi"


def test_init_refuses_existing_coga_os(tmp_path: Path, fake_vendor, fake_venv) -> None:
    """The refusal names the actual remedies — `--update` is gone, so the
    message must say what re-running init was probably reaching for: upgrade
    the CLI with its owning installer, recover a broken coga/ by fixing/removing
    it, or run `coga uninstall` from inside the target to drop the footprint."""
    target = tmp_path / "occupied"
    target.mkdir()
    (target / "coga").mkdir()
    (target / "coga" / "coga.toml").write_text("version = 1\n")

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 2
    assert "repo is already initialized" in result.output
    assert "uv tool upgrade coga" in result.output
    assert "pip install --upgrade coga" in result.output
    assert "coga uninstall" in result.output
    assert f"from inside {target}" in result.output
    assert "remove the dir" in result.output


def test_init_does_not_misidentify_unrelated_coga_path(
    tmp_path: Path, fake_vendor, fake_venv
) -> None:
    target = tmp_path / "occupied"
    target.mkdir()
    (target / "coga").mkdir()

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])

    assert result.exit_code == 2
    assert "does not look like an initialized Coga repo" in result.output
    assert "coga.toml is missing" in result.output
    assert "broken or partial Coga install" in result.output
    assert "move or rename the existing path" in result.output
    assert "repo is already initialized" not in result.output
    assert "coga uninstall" not in result.output


def test_init_into_missing_dir_errors_not_git_repo(
    tmp_path: Path, fake_vendor, fake_venv
) -> None:
    """A target that doesn't exist and has no git repo above it fails loud
    instead of auto-creating the dir and silently skipping the commit. Nothing
    is written — the dir stays absent. (A missing target *below* a git root is
    fine — that's the nested monorepo init.)"""
    target = tmp_path / "fresh"
    assert not target.exists()

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 2
    assert "not inside a git repository" in result.output
    assert "git init" in result.output
    assert not target.exists()


# --- init build ticket ----------------------------------------------------------


def test_init_ships_build_ticket_template(
    tmp_path: Path, fake_vendor, fake_venv
) -> None:
    """The coga-build task is a static packaged template: fresh init copies
    it verbatim — no prompts, no creating code — and the onboarding chat happens
    at first launch as the workflow's first step. The `--user` name is stamped
    over the `new-user` placeholder so it never ships live."""
    target = _make_git_repo(tmp_path / "company")
    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    tasks = target / "coga" / "tasks"
    ticket = tasks / "coga-build.md"
    text = ticket.read_text()
    assert "status: active" in text
    assert "name: build/onboarding" in text
    assert "step: 1 (gather-and-spec)" in text
    assert "Empty until the `gather-and-spec` step runs at first launch" in text
    # The placeholder is stamped with the captured name; it never ships live.
    assert "owner: tester" in text
    assert "human: tester" in text
    assert "new-user" not in text
    # Single-file format: the blackboard rides inside ticket.md behind one
    # fence; no per-task blackboard.md / log.md siblings.
    from coga.taskfile import fence_count

    assert fence_count(text) == 1
    # File-form task: a self-contained `.md`, no companion directory.
    assert not (tasks / "coga-build").exists()
    assert not (tasks / "coga-build" / "blackboard.md").exists()
    assert not (tasks / "coga-build" / "log.md").exists()
    # Bare init on an empty repo points at `coga build` (the alias that
    # launches this ticket) rather than at a manual launch.
    assert "Run `coga build`" in result.output


def test_init_stamps_new_user_out_of_every_delivered_ticket(
    tmp_path: Path, fake_vendor, fake_venv
) -> None:
    """No delivered ticket carries the `new-user` placeholder after a fresh
    init — the `--user` name is stamped over it everywhere, including the
    `browser-automation` draft that ships on every repo."""
    target = _make_git_repo(tmp_path / "company")

    result = CliRunner().invoke(app, ["init", str(target), "--user", "marc"])
    assert result.exit_code == 0, result.output

    tasks = target / "coga" / "tasks"
    # File-form tasks are `<slug>.md`; dir-form (the `_template`) keep `ticket.md`.
    for ticket in tasks.glob("**/*.md"):
        assert "new-user" not in ticket.read_text(), f"new-user survived in {ticket}"
    # browser-automation ships on every repo (not gated) and is stamped too.
    browser = (tasks / "browser-automation.md").read_text()
    assert "owner: marc" in browser
    assert "human: marc" in browser


def test_init_empty_repo_seeds_onboarding_and_points_at_build(
    tmp_path: Path, fake_vendor, fake_venv
) -> None:
    """An empty repo keeps the onboarding ticket and the next-steps coax
    points the user at the onboarding command."""
    target = _make_git_repo(tmp_path / "company")

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    tasks = target / "coga" / "tasks"
    assert (tasks / "coga-build.md").is_file()
    assert "Run `coga build`" in result.output
    assert 'coga ticket "' not in result.output
    assert "Skipped the onboarding ticket" not in result.output


def test_init_filled_repo_skips_onboarding_and_points_at_ticket(
    tmp_path: Path, fake_vendor, fake_venv
) -> None:
    """A filled repo (any pre-existing user file) drops the onboarding ticket
    and the next-steps coax points the user at `coga ticket`.
    browser-automation is not gated, so it still ships (stamped)."""
    target = _make_git_repo(tmp_path / "existing-repo")
    (target / "README.md").write_text("hi")

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    tasks = target / "coga" / "tasks"
    assert not (tasks / "coga-build.md").exists()  # onboarding pruned
    # Not gated — still delivered, and stamped (no placeholder survives).
    browser = tasks / "browser-automation.md"
    assert browser.is_file()
    assert "new-user" not in browser.read_text()
    assert 'coga ticket "' in result.output
    assert "Skipped the onboarding ticket" in result.output
    assert "Run `coga build`" not in result.output


def test_init_next_steps_name_the_agent_cli_prerequisite(
    tmp_path: Path, fake_vendor, fake_venv
) -> None:
    """Init's next steps name the agent-CLI prerequisite with install URLs —
    the `coga build` coax otherwise sends a fresh user into a flow whose
    "not found in PATH" failure arrives only after they've committed to it."""
    target = _make_git_repo(tmp_path / "company")

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    assert "Install an agent CLI" in result.output
    assert "https://claude.com/claude-code" in result.output
    assert "https://github.com/openai/codex" in result.output


def test_init_filled_repo_ignores_coga_managed_files(
    tmp_path: Path, fake_vendor, fake_venv
) -> None:
    """Pre-existing `.git`/`.DS_Store` and coga-managed names (CLAUDE.md etc.)
    don't count as a filled repo — onboarding is still seeded."""
    target = tmp_path / "company"
    target.mkdir()
    (target / ".git").mkdir()
    (target / ".DS_Store").write_text("")
    (target / "CLAUDE.md").write_text("user-authored guide")

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    assert (target / "coga" / "tasks" / "coga-build.md").is_file()
    assert "Run `coga build`" in result.output


# --- name capture + gate helpers ----------------------------------------------


def test_repo_is_empty_true_for_missing_or_coga_managed(tmp_path: Path) -> None:
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
    """The delivered onboarding ticket (coga-build) is pruned on a filled
    repo; other tasks are left alone."""
    coga_os = tmp_path / "coga"
    tasks = coga_os / "tasks"
    for name in ("coga-build", "browser-automation", "_template"):
        (tasks / name).mkdir(parents=True)
        (tasks / name / "ticket.md").write_text("---\n---\n")

    pruned = init_cmd._prune_onboarding_tickets(coga_os)

    assert set(pruned) == {"coga-build"}
    assert not (tasks / "coga-build").exists()
    assert (tasks / "browser-automation").is_dir()  # not gated
    assert (tasks / "_template").is_dir()


def test_stamp_user_into_delivered_tickets(tmp_path: Path) -> None:
    coga_os = tmp_path / "coga"
    tasks = coga_os / "tasks"
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

    stamped = init_cmd._stamp_user_into_delivered_tickets(coga_os, "marc")

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


# --- vendored-CLI location, pin, and host gitignore --------------------------


def _seed_local_coga_os(root: Path) -> Path:
    """Stand in for a previously-init'd repo."""
    coga_os = root / "coga"
    (coga_os / "skills" / "_template").mkdir(parents=True)
    (coga_os / "tasks" / "_template").mkdir(parents=True)
    (coga_os / "skills" / "_template" / "SKILL.md").write_text("OLD skill template\n")
    (coga_os / "tasks" / "_template" / "ticket.md").write_text("OLD ticket template\n")
    (coga_os / "skills" / "myteam" / "real-skill").mkdir(parents=True)
    (coga_os / "skills" / "myteam" / "real-skill" / "SKILL.md").write_text("user content\n")
    (coga_os / "bootstrap" / "create").mkdir(parents=True)
    (coga_os / "bootstrap" / "create" / "ticket.md").write_text("OLD bootstrap ticket\n")
    (coga_os / "bootstrap" / "stale").mkdir(parents=True)
    (coga_os / "bootstrap" / "stale" / "ticket.md").write_text("STALE ticket from a prior upstream\n")
    (coga_os / "coga.toml").write_text("version = 1\n")
    (coga_os / "rules.md").write_text("obsolete global rules\n")
    (coga_os / "scripts").mkdir()
    (coga_os / "scripts" / "cron.sh").write_text("#!/bin/sh\n")

    # Stale top-level file an earlier upstream shipped (counter / numeric IDs).
    (coga_os / "counter").write_text("7\n")
    # Stale top-level dir an earlier upstream shipped (meta/ → bootstrap/ rename).
    (coga_os / "meta").mkdir()
    (coga_os / "meta" / "ticket.md").write_text("OLD meta/ ticket\n")
    # Stale nested dir from a bootstrap skill rename (create → ticket in 350c4ed).
    (coga_os / "skills" / "bootstrap" / "create").mkdir(parents=True)
    (coga_os / "skills" / "bootstrap" / "create" / "SKILL.md").write_text("OLD bootstrap/create skill\n")
    # Optional Coga-owned skill content now lives in skills/ and should be
    # preserved for the managed-skill reconciler, not pruned as obsolete.
    (coga_os / "skills" / "coga" / "calendar-reminder").mkdir(parents=True)
    (coga_os / "skills" / "coga" / "calendar-reminder" / "SKILL.md").write_text(
        "OLD coga/calendar-reminder skill\n"
    )
    (coga_os / "skills" / "retro" / "done-ticket").mkdir(parents=True)
    (coga_os / "skills" / "retro" / "done-ticket" / "SKILL.md").write_text(
        "OLD retro/done-ticket skill\n"
    )
    (coga_os / ".agent-skills").mkdir()
    (coga_os / ".agent-skills" / "_template").symlink_to("../skills/_template")
    (coga_os / "contexts" / "coga" / "sync").mkdir(parents=True)
    (coga_os / "contexts" / "coga" / "sync" / "SKILL.md").write_text(
        "OLD coga/sync context\n"
    )
    (coga_os / "contexts" / "dev" / "code").mkdir(parents=True)
    (coga_os / "contexts" / "dev" / "code" / "SKILL.md").write_text(
        "OLD dev/code context\n"
    )
    # Stale `_*` create upstream no longer ships (rename or removal).
    (coga_os / "recurring").mkdir(exist_ok=True)
    (coga_os / "recurring" / "_template_old.md").write_text("STALE recurring template\n")

    vendored = coga_os / ".coga" / "src" / "coga"
    vendored.mkdir(parents=True)
    (vendored / "cli.py").write_text("# OLD vendored cli\n")
    return coga_os


def test_init_commits_coga_os_when_target_is_git_repo(
    tmp_path: Path, fake_vendor, fake_venv, monkeypatch: pytest.MonkeyPatch
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
    assert "Committed coga/ as" in result.output

    log = subprocess.run(
        ["git", "-C", str(target), "log", "--oneline"],
        capture_output=True, text=True, check=True,
    )
    assert "Create coga via `coga init`" in log.stdout

    # Upstream-managed paths and machine-local files are gitignored — none should be tracked.
    tracked = subprocess.run(
        ["git", "-C", str(target), "ls-files", "coga"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    assert any(p.startswith("coga/coga.toml") for p in tracked)
    assert not any(".coga/" in p for p in tracked)
    assert not any(p.endswith("coga.local.toml") for p in tracked)
    assert not any("/bootstrap/" in p for p in tracked)
    assert not any("/skills/retro/" in p for p in tracked)
    assert not any("/_template" in p for p in tracked)


def test_init_fails_loud_when_target_is_not_git_repo(
    tmp_path: Path, fake_vendor, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    """coga is git-backed: a target outside any git work tree is a hard error
    (not a silent skip), and nothing is written to disk — the user runs
    `git init` here and re-runs."""
    target = tmp_path / "company"
    target.mkdir()  # exists, but is not a git repo (nor inside one)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 2
    assert "not inside a git repository" in result.output
    assert "git init" in result.output
    assert not (target / "coga").exists()


# --- git identity check --------------------------------------------------------
#
# `coga init` fails loud up front when git has no committer identity — the
# commit at the end would fail, historically silently (coga/ staged but
# uncommitted, and the first `coga create` dying on a raw `fatal: ambiguous
# argument 'HEAD'`). Captured before the autouse `_stub_init_identity_check`
# fixture replaces the module attribute, so these tests exercise the real
# implementation.
_real_identity_check = init_cmd._check_git_identity


def _force_missing_git_identity(
    target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Make `target`'s repo deterministically identity-less on any host.

    `user.useConfigOnly` forbids git's hostname auto-detection (which succeeds
    on some hosts and fails on others), and the env vars would override config
    entirely, so both are cleared.
    """
    subprocess.run(
        ["git", "-C", str(target), "config", "user.useConfigOnly", "true"],
        check=True,
    )
    for var in (
        "GIT_AUTHOR_NAME",
        "GIT_AUTHOR_EMAIL",
        "GIT_COMMITTER_NAME",
        "GIT_COMMITTER_EMAIL",
        "EMAIL",
    ):
        monkeypatch.delenv(var, raising=False)


def test_init_fails_loud_when_git_has_no_identity(
    tmp_path: Path, fake_vendor, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A truly fresh machine has no `user.email`/`user.name`: init probes git
    identity up front and fails loud with the remedy, before writing anything."""
    target = tmp_path / "company"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    _force_missing_git_identity(target, monkeypatch)
    monkeypatch.setattr(init_cmd, "_check_git_identity", _real_identity_check)

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 2
    assert "git has no identity configured" in result.output
    assert 'git config --global user.email "you@example.com"' in result.output
    assert not (target / "coga").exists()


def test_init_fails_up_front_when_only_committer_identity_exists(
    tmp_path: Path, fake_vendor, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Git requires author and committer identities independently; a CI-style
    committer-only environment must fail before init writes anything."""
    target = tmp_path / "company"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    _force_missing_git_identity(target, monkeypatch)
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Coga CI")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "coga@example.com")
    monkeypatch.setattr(init_cmd, "_check_git_identity", _real_identity_check)

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 2
    assert "Author identity unknown" in result.output
    assert not (target / "coga").exists()


def test_identity_check_passes_with_repo_local_identity(tmp_path: Path) -> None:
    """Repo-local `user.email`/`user.name` is enough — the probe runs from the
    target, so per-repo config counts and the check stays quiet."""
    target = tmp_path / "company"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    subprocess.run(["git", "-C", str(target), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(target), "config", "user.name", "T"], check=True)

    _real_identity_check(target)  # must not raise


def test_identity_check_probes_nearest_ancestor_for_missing_target(
    tmp_path: Path,
) -> None:
    """A nested init (`coga init tools/ops`) may name a target that doesn't
    exist yet — the probe falls back to the nearest existing ancestor, where
    the host repo's identity config applies."""
    host = tmp_path / "monorepo"
    host.mkdir()
    subprocess.run(["git", "init", "-q", str(host)], check=True)
    subprocess.run(["git", "-C", str(host), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(host), "config", "user.name", "T"], check=True)

    _real_identity_check(host / "tools" / "ops")  # must not raise


def test_init_warns_loud_when_commit_fails(
    tmp_path: Path, fake_vendor, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The backstop for commit failures the identity check can't see (here a
    failing pre-commit hook): init still succeeds — coga/ is written and
    staged — but the skipped commit is a loud warning naming git's error and
    the manual commit remedy, never a silent absence of the "Committed" line."""
    target = tmp_path / "company"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    subprocess.run(["git", "-C", str(target), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(target), "config", "user.name", "T"], check=True)
    hook = target / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\necho 'hook says no' >&2\nexit 1\n")
    hook.chmod(0o755)
    monkeypatch.setenv("PATH", os.environ["PATH"])  # need git on PATH

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output
    assert "Committed coga/ as" not in result.output
    assert "NOT committed" in result.output
    assert "git commit failed" in result.output
    assert "hook says no" in result.output  # git's own stderr is surfaced
    # Recovery re-stages and commits the complete generated path set, not just
    # coga/, so following it leaves the same clean tree as the success path.
    assert "git -C" in result.output
    assert "add -- coga .gitignore CLAUDE.md AGENTS.md" in result.output
    assert (
        "commit -m 'Create coga via `coga init`' -- coga .gitignore "
        "CLAUDE.md AGENTS.md"
    ) in result.output
    # coga/ survived on disk and is staged, ready to commit once fixed.
    staged = subprocess.run(
        ["git", "-C", str(target), "diff", "--cached", "--name-only"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert "coga/coga.toml" in staged


def test_init_add_failure_warns_without_claiming_files_are_staged(
    tmp_path: Path, fake_vendor, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed `git add` gets an honest warning plus safely quoted, complete
    stage-and-commit recovery commands."""
    target = tmp_path / "company repo"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    subprocess.run(["git", "-C", str(target), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(target), "config", "user.name", "T"], check=True)
    real_run = subprocess.run

    def fail_generated_path_add(args, *run_args, **run_kwargs):
        if (
            args[:3] == ["git", "-C", str(target)]
            and len(args) > 3
            and args[3] == "add"
        ):
            raise subprocess.CalledProcessError(
                128, args, stderr="fatal: Unable to create '.git/index.lock'"
            )
        return real_run(args, *run_args, **run_kwargs)

    monkeypatch.setattr(init_cmd.subprocess, "run", fail_generated_path_add)

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output
    assert "written but NOT committed" in result.output
    assert "written and staged" not in result.output
    assert "git add failed" in result.output
    assert "index.lock" in result.output
    expected_prefix = f"git -C '{target}'"
    assert (
        f"{expected_prefix} add -- coga .gitignore CLAUDE.md AGENTS.md"
        in result.output
    )
    assert (
        f"{expected_prefix} commit -m 'Create coga via `coga init`' -- "
        "coga .gitignore CLAUDE.md AGENTS.md"
        in result.output
    )


# --- nested init (coga/ in a subdir of a host repo) ---------------------------


def test_init_into_subdir_of_git_repo(
    tmp_path: Path, fake_vendor, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`coga init tools/ops` inside a monorepo scaffolds a nested coga/ and
    commits it into the host repo — the target doesn't have to be the git
    root, just inside its work tree. The missing subdir is created."""
    host = tmp_path / "monorepo"
    host.mkdir()
    subprocess.run(["git", "init", "-q", str(host)], check=True)
    subprocess.run(["git", "-C", str(host), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(host), "config", "user.name", "T"], check=True)
    (host / "README.md").write_text("host project\n")
    subprocess.run(["git", "-C", str(host), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(host), "commit", "-qm", "host"], check=True)
    target = host / "tools" / "ops"
    assert not target.exists()
    monkeypatch.setenv("PATH", os.environ["PATH"])  # need git on PATH
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output
    assert "Committed coga/ as" in result.output

    assert (target / "coga" / "coga.toml").is_file()
    # Committed into the *host* repo, with paths below the git root.
    tracked = subprocess.run(
        ["git", "-C", str(host), "ls-files"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    assert "tools/ops/coga/coga.toml" in tracked
    # The coga-managed ignore block lands at the nested target — git scopes a
    # nested .gitignore to its own dir, where the symlinks and .coga/ live.
    host_gi = (target / ".gitignore").read_text()
    assert update_cmd.HOST_GITIGNORE_BEGIN in host_gi
    assert ".claude/skills/coga" in host_gi
    # A nested init sits in an established host project: onboarding is never
    # seeded, even though the subdir itself started empty.
    assert not (target / "coga" / "tasks" / "coga-build.md").exists()
    assert "Run `coga build`" not in result.output
    assert 'coga ticket "' in result.output


def test_init_refuses_target_inside_existing_coga_repo(
    tmp_path: Path, fake_vendor, fake_venv
) -> None:
    """A coga/ nested inside an existing coga OS tree can't work — discovery
    walks up and resolves the enclosing repo — so init refuses before writing
    anything, both for a subdir of the coga tree and the coga dir itself."""
    host = _make_git_repo(tmp_path / "company")
    coga_os = host / "coga"
    coga_os.mkdir()
    (coga_os / "coga.toml").write_text("version = 1\n")

    for target in (coga_os / "sub", coga_os):
        result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
        assert result.exit_code == 2, result.output
        assert "inside an existing coga repo" in result.output
    assert not (coga_os / "sub").exists()
    assert not (coga_os / "coga").exists()


def test_init_refuses_sibling_subdir_of_root_level_coga(
    tmp_path: Path, fake_vendor, fake_venv
) -> None:
    """The common layout — a git repo whose coga lives at `<repo>/coga/` —
    governs every subdir via `find_repo_root`'s sibling-`coga/` descent. So
    `coga init <repo>/data` must be refused too: it would shadow the root coga
    for that subtree, not just when the target sits literally inside coga/."""
    host = _make_git_repo(tmp_path / "company")
    coga_os = host / "coga"
    coga_os.mkdir()
    (coga_os / "coga.toml").write_text("version = 1\n")

    target = host / "data"  # sibling of coga/, governed by the root coga
    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 2, result.output
    assert "inside an existing coga repo" in result.output
    assert str(coga_os / "coga.toml") in result.output
    assert not (target / "coga").exists()


def test_init_refuses_target_gitignored_by_host_repo(
    tmp_path: Path, fake_vendor, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the host repo gitignores the target subtree, `git add` would refuse
    coga/ and the commit would be silently skipped. Init fails loud up front
    instead — nothing is written to disk."""
    host = tmp_path / "monorepo"
    host.mkdir()
    subprocess.run(["git", "init", "-q", str(host)], check=True)
    subprocess.run(["git", "-C", str(host), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(host), "config", "user.name", "T"], check=True)
    (host / ".gitignore").write_text("build/\n")
    subprocess.run(["git", "-C", str(host), "add", ".gitignore"], check=True)
    subprocess.run(["git", "-C", str(host), "commit", "-qm", "host"], check=True)
    target = host / "build" / "ops"
    monkeypatch.setenv("PATH", os.environ["PATH"])  # need git on PATH
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 2, result.output
    assert "gitignored by the host repo" in result.output
    assert not (target / "coga").exists()


def test_init_into_subdir_leaves_unrelated_staged_files_alone(
    tmp_path: Path, fake_vendor, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A nested init commits only coga/ (and its host files), never the user's
    pre-existing staged changes in the live host repo."""
    host = tmp_path / "monorepo"
    host.mkdir()
    subprocess.run(["git", "init", "-q", str(host)], check=True)
    subprocess.run(["git", "-C", str(host), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(host), "config", "user.name", "T"], check=True)
    (host / "README.md").write_text("host project\n")
    subprocess.run(["git", "-C", str(host), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(host), "commit", "-qm", "host"], check=True)
    # The user has unrelated work staged when they run `coga init`.
    (host / "wip.py").write_text("print('wip')\n")
    subprocess.run(["git", "-C", str(host), "add", "wip.py"], check=True)
    target = host / "tools" / "ops"
    monkeypatch.setenv("PATH", os.environ["PATH"])  # need git on PATH
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    committed = subprocess.run(
        ["git", "-C", str(host), "show", "--name-only", "--format=", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    assert "wip.py" not in committed
    assert "tools/ops/coga/coga.toml" in committed
    # The user's staged file is untouched — still staged, not committed.
    staged = subprocess.run(
        ["git", "-C", str(host), "diff", "--cached", "--name-only"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    assert "wip.py" in staged


def test_is_git_repo_accepts_missing_subdir_below_work_tree(tmp_path: Path) -> None:
    """The shared git predicate walks to the nearest existing ancestor, so a
    not-yet-created nested target inside a work tree passes, while anything
    outside a work tree still fails."""
    host = tmp_path / "host"
    host.mkdir()
    subprocess.run(["git", "init", "-q", str(host)], check=True)

    assert update_cmd.is_git_repo(host / "tools" / "ops") is True
    assert update_cmd.is_git_repo(tmp_path / "elsewhere" / "deep") is False


def test_is_git_repo_fast_path_on_git_marker(tmp_path: Path) -> None:
    """A bare `.git` entry (dir or worktree/submodule file) short-circuits
    without invoking git — the same filesystem check init always used."""
    target = _make_git_repo(tmp_path / "company")
    assert update_cmd.is_git_repo(target) is True


# --- skill discovery wiring ---------------------------------------------------


def test_init_links_skills_into_agent_dirs(
    tmp_path: Path, fake_vendor, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _make_git_repo(tmp_path / "company")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    skills_src = (target / "coga" / ".agent-skills").resolve()
    for dirname in (".claude", ".codex"):
        link = target / dirname / "skills" / "coga"
        assert link.is_symlink(), f"missing symlink for {dirname}"
        assert link.resolve() == skills_src
    assert (target / "coga" / ".agent-skills" / "retro" / "done-ticket").is_symlink()
    assert "Wired skill discovery for Claude Code, Codex" in result.output


def test_init_skips_skill_link_when_agent_marker_is_a_file(
    tmp_path: Path, fake_vendor, fake_venv, monkeypatch: pytest.MonkeyPatch
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
    assert (target / ".claude" / "skills" / "coga").is_symlink()
    assert "Skipped Codex skill wiring" in result.output


def test_init_link_skills_is_idempotent(tmp_path: Path) -> None:
    target = tmp_path / "company"
    coga_os = target / "coga"
    (coga_os / "skills").mkdir(parents=True)

    wired1, blocked1 = init_cmd._link_skills_for_agents(target, coga_os)
    wired2, blocked2 = init_cmd._link_skills_for_agents(target, coga_os)
    assert wired1 == wired2 == ["Claude Code", "Codex"]
    assert blocked1 == blocked2 == []
    assert (target / ".claude" / "skills" / "coga").is_symlink()


# --- generated agent skill view ---------------------------------------------


def test_agent_skill_view_includes_bootstrap_and_local_skills(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "company"
    coga_os = target / "coga"
    bundled_root = tmp_path / "package-skills"
    bundled = bundled_root / "retro" / "done-ticket"
    bundled.mkdir(parents=True)
    (bundled / "SKILL.md").write_text("bundled retro\n")
    _fake_package_skill_root(monkeypatch, bundled_root, tmp_path / "missing")
    (coga_os / "skills" / "team" / "local").mkdir(parents=True)
    (coga_os / "skills" / "team" / "local" / "SKILL.md").write_text("local\n")

    wired, blocked = init_cmd._link_skills_for_agents(target, coga_os)

    assert wired == ["Claude Code", "Codex"]
    assert blocked == []
    assert (coga_os / ".agent-skills" / "retro" / "done-ticket").is_symlink()
    assert (coga_os / ".agent-skills" / "team" / "local").is_symlink()
    assert os.readlink(target / ".codex" / "skills" / "coga") == (
        "../../coga/.agent-skills"
    )


def test_agent_skill_view_prefers_local_skill_over_bootstrap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "company"
    coga_os = target / "coga"
    bundled_root = tmp_path / "package-skills"
    bundled = bundled_root / "tools" / "example"
    local = coga_os / "skills" / "tools" / "example"
    bundled.mkdir(parents=True)
    local.mkdir(parents=True)
    (bundled / "SKILL.md").write_text("bundled\n")
    (local / "SKILL.md").write_text("local\n")
    _fake_package_skill_root(monkeypatch, bundled_root, tmp_path / "missing")

    init_cmd._link_skills_for_agents(target, coga_os)

    link = coga_os / ".agent-skills" / "tools" / "example"
    assert link.is_symlink()
    assert link.resolve() == local.resolve()


def test_link_skills_for_agents_replaces_old_raw_skills_link(tmp_path: Path) -> None:
    target = tmp_path / "company"
    coga_os = target / "coga"
    (coga_os / "skills" / "team" / "local").mkdir(parents=True)
    (coga_os / "skills" / "team" / "local" / "SKILL.md").write_text("local\n")
    old = target / ".claude" / "skills" / "coga"
    old.parent.mkdir(parents=True)
    old.symlink_to("../../coga/skills")

    init_cmd._link_skills_for_agents(target, coga_os)

    assert os.readlink(old) == "../../coga/.agent-skills"


# --- agent-guide files (CLAUDE.md / AGENTS.md) -------------------------------


def test_init_writes_agent_guides(
    tmp_path: Path, fake_vendor, fake_venv, monkeypatch: pytest.MonkeyPatch
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
        assert "canonical contexts are package-backed" in body
        assert "override them with local files under `coga/contexts/coga/`" in body
        assert "coga launch bootstrap/orient" in body

    assert "Wrote CLAUDE.md, AGENTS.md" in result.output


def test_init_preserves_existing_agent_guides(
    tmp_path: Path, fake_vendor, fake_venv, monkeypatch: pytest.MonkeyPatch
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


def test_init_commits_agent_guides_in_git_repo(
    tmp_path: Path, fake_vendor, fake_venv, monkeypatch: pytest.MonkeyPatch
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
    tmp_path: Path, fake_vendor, fake_venv, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _make_git_repo(tmp_path / "company")
    monkeypatch.setenv("PATH", "")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])
    assert result.exit_code == 0, result.output

    pin = target / "coga" / ".coga" / "COGA_PIN"
    assert pin.is_file()
    lines = pin.read_text().splitlines()
    assert lines[0] == FAKE_SOURCE.display
    assert lines[1] == FAKE_VERSION
    assert f"Vendored CLI coga {FAKE_VERSION} from {FAKE_SOURCE.display}" in result.output


def test_version_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`coga --version` prints the package version and (when present) the pin."""
    # chdir somewhere with no coga/ so `find_repo_root` returns nothing.
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0, result.output
    assert "coga " in result.output
    assert "vendored CLI" not in result.output


def test_version_flag_help_describes_vendored_cli() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0, result.output
    assert "Print the coga package and vendored CLI versions." in result.output


def test_version_flag_includes_pin_when_in_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    coga_os = tmp_path / "coga"
    (coga_os / ".coga").mkdir(parents=True)
    (coga_os / "coga.toml").write_text("version = 1\n")
    (coga_os / ".coga" / "COGA_PIN").write_text(
        f"{FAKE_SOURCE.display}\n{FAKE_VERSION}\n"
    )
    monkeypatch.chdir(coga_os)

    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0, result.output
    assert f"vendored CLI {FAKE_VERSION} (from {FAKE_SOURCE.display})" in result.output


# --- gitignore management ----------------------------------------------------


def test_init_writes_host_gitignore_block_in_git_repo(
    tmp_path: Path, fake_vendor, fake_venv, monkeypatch: pytest.MonkeyPatch
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
    assert ".claude/skills/coga" in host_gi
    assert ".codex/skills/coga" in host_gi

    # Block was committed alongside coga/ in the init commit.
    tracked = subprocess.run(
        ["git", "-C", str(target), "ls-files"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    assert ".gitignore" in tracked


def test_init_appends_to_existing_host_gitignore(
    tmp_path: Path, fake_vendor, fake_venv, monkeypatch: pytest.MonkeyPatch
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
    assert ".claude/skills/coga" in host_gi


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
    assert ".claude/skills/coga" in text
    assert update_cmd.HOST_GITIGNORE_END in text


def test_refresh_coga_gitignore_is_idempotent(tmp_path: Path) -> None:
    """Running the refresh twice on the same input is a no-op."""
    src_root = tmp_path / "upstream"
    src_root.mkdir()
    (src_root / ".gitignore").write_text(".agent-skills/\n.coga/\n")
    dst_root = tmp_path / "coga"
    dst_root.mkdir()

    assert update_cmd._refresh_coga_gitignore(src_root, dst_root) is True
    first = (dst_root / ".gitignore").read_text()
    assert update_cmd._refresh_coga_gitignore(src_root, dst_root) is False
    assert (dst_root / ".gitignore").read_text() == first


def test_refresh_coga_gitignore_replaces_existing_block(tmp_path: Path) -> None:
    """An existing marker block is replaced wholesale; user content outside is kept."""
    src_root = tmp_path / "upstream"
    src_root.mkdir()
    (src_root / ".gitignore").write_text(".agent-skills/\n.coga/\nnew-entry/\n")
    dst_root = tmp_path / "coga"
    dst_root.mkdir()
    # Existing file: stale marker block + user-area content.
    (dst_root / ".gitignore").write_text(
        f"{update_cmd.COGA_GITIGNORE_BEGIN}\nold-stale-entry/\n"
        f"{update_cmd.COGA_GITIGNORE_END}\n\nuser-rule/\n"
    )

    assert update_cmd._refresh_coga_gitignore(src_root, dst_root) is True
    text = (dst_root / ".gitignore").read_text()
    assert "old-stale-entry/" not in text
    assert "new-entry/" in text
    assert "user-rule/" in text


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


def test_venv_python_executable_parses_pyvenv_cfg(tmp_path: Path) -> None:
    venv = tmp_path / ".venv"
    venv.mkdir()
    base_python = tmp_path / "python3.11"
    (venv / "pyvenv.cfg").write_text(f"executable = {base_python}\n")
    assert update_cmd._venv_python_executable(venv) == base_python.resolve()


def test_install_venv_recreates_on_python_version_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A venv built against a different Python X.Y gets blown away and rebuilt."""
    coga_os = tmp_path / "coga"
    dst_coga = coga_os / ".coga"
    dst_coga.mkdir(parents=True)

    # Stand up a fake "old" venv tagged as Python 1.0 so it can never match.
    venv_dir = dst_coga / ".venv"
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
            (new_venv / "bin" / "coga").write_text("#!/bin/sh\n")
            (new_venv / "bin" / "coga").chmod(0o755)
            (new_venv / "pyvenv.cfg").write_text(
                f"version = {sys.version_info.major}.{sys.version_info.minor}.0\n"
            )
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if "pip" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return real_run(cmd, **kwargs)

    monkeypatch.setattr(update_cmd.subprocess, "run", fake_run)

    update_cmd.install_venv(coga_os, _fake_install_source())

    # Stale lib dir wiped, new venv tagged with the running Python version.
    assert not sentinel.exists()
    assert update_cmd._venv_python_version(venv_dir) == sys.version_info[:2]


def test_install_venv_keeps_matching_venv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A venv that already matches the running Python isn't recreated."""
    coga_os = tmp_path / "coga"
    dst_coga = coga_os / ".coga"
    dst_coga.mkdir(parents=True)

    venv_dir = dst_coga / ".venv"
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

    update_cmd.install_venv(coga_os, _fake_install_source())

    assert venv_calls == []  # no recreate
    assert sentinel.read_text() == "preserve me"


# --- venv interpreter selection ------------------------------------------------


def test_resolve_venv_python_defaults_to_sys_executable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(update_cmd.COGA_PYTHON_ENV, raising=False)
    assert update_cmd.resolve_venv_python() == sys.executable


def test_resolve_venv_python_honors_coga_python(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub = tmp_path / "python3.11"
    stub.write_text("#!/bin/sh\n")
    stub.chmod(0o755)
    monkeypatch.setenv(update_cmd.COGA_PYTHON_ENV, str(stub))
    assert update_cmd.resolve_venv_python() == str(stub)


def test_resolve_venv_python_exits_on_dangling_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:
    """An explicit COGA_PYTHON that doesn't exist fails loud, never falls back."""
    monkeypatch.setenv(update_cmd.COGA_PYTHON_ENV, str(tmp_path / "no-such-python"))
    with pytest.raises(SystemExit) as exc:
        update_cmd.resolve_venv_python()
    assert exc.value.code == 2
    assert update_cmd.COGA_PYTHON_ENV in capsys.readouterr().err


def test_requires_python_spec_reads_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'coga'\nrequires-python = \">=3.11\"\n")
    assert update_cmd._requires_python_spec(pyproject) == ">=3.11"


def test_requires_python_spec_none_when_absent(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'coga'\n")
    assert update_cmd._requires_python_spec(pyproject) is None


@pytest.mark.parametrize(
    ("version", "spec", "expected"),
    [
        ((3, 11, 4), ">=3.11", True),
        ((3, 10, 9), ">=3.11", False),
        ((3, 12, 0), ">=3.11,<3.12", False),
        ((3, 11, 9), ">=3.11,<3.12", True),
        ((4, 0, 0), "<4", False),
        ((3, 12, 1), "!=3.12.*", False),
        ((3, 13, 0), "!=3.12.*", True),
        ((3, 11, 2), "~=3.11", True),
        ((4, 0, 0), "~=3.11", False),
        ((3, 11, 0), "==3.11", True),
        # Unparseable clauses count as satisfied — never brick the bootstrap.
        ((3, 11, 0), ">=3.11, unparseable-nonsense", True),
    ],
)
def test_version_satisfies_spec(
    version: tuple[int, int, int], spec: str, expected: bool,
) -> None:
    assert update_cmd._version_satisfies(version, spec) is expected


def test_install_venv_rejects_python_outside_requires_python(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:
    """The requires-python check runs before any venv is built."""
    monkeypatch.delenv(update_cmd.COGA_PYTHON_ENV, raising=False)
    coga_os = tmp_path / "coga"

    with pytest.raises(SystemExit) as exc:
        update_cmd.install_venv(coga_os, _fake_install_source(">=99.0"))

    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert ">=99.0" in err
    assert update_cmd.COGA_PYTHON_ENV in err
    assert not (coga_os / ".coga" / ".venv").exists()


def test_install_venv_builds_with_coga_python_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """COGA_PYTHON picks the interpreter the venv is created with."""
    override = tmp_path / "python3.11"
    override.write_text("#!/bin/sh\n")
    override.chmod(0o755)
    monkeypatch.setenv(update_cmd.COGA_PYTHON_ENV, str(override))
    coga_os = tmp_path / "coga"

    venv_calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        if cmd[1] == "-c":  # version probe of the override interpreter
            return subprocess.CompletedProcess(cmd, 0, stdout="3.11.9\n", stderr="")
        if cmd[1:3] == ["-m", "venv"]:
            venv_calls.append(list(cmd))
            new_venv = Path(cmd[3])
            (new_venv / "bin").mkdir(parents=True)
            (new_venv / "bin" / "python").write_text("#!/bin/sh\n")
            (new_venv / "bin" / "python").chmod(0o755)
            (new_venv / "pyvenv.cfg").write_text("version = 3.11.9\n")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if "pip" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected subprocess call: {cmd}")

    monkeypatch.setattr(update_cmd.subprocess, "run", fake_run)

    update_cmd.install_venv(coga_os, _fake_install_source(">=3.11"))

    assert [cmd[0] for cmd in venv_calls] == [str(override)]


def test_install_venv_recreates_when_override_changes_same_minor_interpreter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """COGA_PYTHON replaces a same-X.Y venv built by another interpreter."""
    override = tmp_path / "new" / "python3.11"
    override.parent.mkdir()
    override.write_text("#!/bin/sh\n")
    override.chmod(0o755)
    monkeypatch.setenv(update_cmd.COGA_PYTHON_ENV, str(override))
    coga_os = tmp_path / "coga"

    venv_dir = coga_os / ".coga" / ".venv"
    (venv_dir / "bin").mkdir(parents=True)
    (venv_dir / "bin" / "python").write_text("#!/bin/sh\n")
    (venv_dir / "bin" / "python").chmod(0o755)
    old_python = tmp_path / "old" / "python3.11"
    (venv_dir / "pyvenv.cfg").write_text(
        f"version = 3.11.8\nexecutable = {old_python}\n"
    )
    sentinel = venv_dir / "old-interpreter.txt"
    sentinel.write_text("stale")

    venv_calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        if cmd[1] == "-c" and "sys.executable" in cmd[2]:
            return subprocess.CompletedProcess(
                cmd, 0, stdout=f"{override}\n", stderr=""
            )
        if cmd[1] == "-c":
            return subprocess.CompletedProcess(cmd, 0, stdout="3.11.9\n", stderr="")
        if cmd[1:3] == ["-m", "venv"]:
            venv_calls.append(list(cmd))
            new_venv = Path(cmd[3])
            (new_venv / "bin").mkdir(parents=True)
            (new_venv / "bin" / "python").write_text("#!/bin/sh\n")
            (new_venv / "bin" / "python").chmod(0o755)
            (new_venv / "pyvenv.cfg").write_text(
                f"version = 3.11.9\nexecutable = {override}\n"
            )
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if "pip" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected subprocess call: {cmd}")

    monkeypatch.setattr(update_cmd.subprocess, "run", fake_run)

    update_cmd.install_venv(coga_os, _fake_install_source(">=3.11"))

    assert not sentinel.exists()
    assert [cmd[0] for cmd in venv_calls] == [str(override)]
    assert update_cmd._venv_python_executable(venv_dir) == override.resolve()


def test_install_venv_missing_ensurepip_prints_remediation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:
    """A Debian-style venv failure names the python3.X-venv package to install."""
    monkeypatch.delenv(update_cmd.COGA_PYTHON_ENV, raising=False)
    coga_os = tmp_path / "coga"

    def fake_run(cmd, **kwargs):
        if cmd[1:3] == ["-m", "venv"]:
            return subprocess.CompletedProcess(
                cmd, 1, stdout="",
                stderr="Error: ensurepip is not available.\n",
            )
        raise AssertionError(f"unexpected subprocess call: {cmd}")

    monkeypatch.setattr(update_cmd.subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as exc:
        update_cmd.install_venv(coga_os, _fake_install_source())

    assert exc.value.code == 2
    err = capsys.readouterr().err
    major, minor = sys.version_info[:2]
    assert f"apt install python{major}.{minor}-venv" in err
    assert update_cmd.COGA_PYTHON_ENV in err


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
    coga_os = tmp_path / "coga"
    venv = coga_os / ".coga" / ".venv"
    py = _stub_executable_in(venv)
    monkeypatch.setattr(update_cmd.sys, "executable", str(py))

    kind, where = update_cmd.running_cli_location(coga_os)
    assert kind == "vendored"
    assert where == venv.absolute()


def test_running_cli_location_detects_pipx(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    coga_os = tmp_path / "project" / "coga"
    coga_os.mkdir(parents=True)
    pipx_venv = tmp_path / "home" / ".local" / "share" / "pipx" / "venvs" / "coga"
    py = _stub_executable_in(pipx_venv)
    (pipx_venv / "pipx_metadata.json").write_text("{}\n")
    monkeypatch.setattr(update_cmd.sys, "executable", str(py))

    kind, where = update_cmd.running_cli_location(coga_os)
    assert kind == "pipx"
    assert where == pipx_venv.absolute()


def test_running_cli_location_falls_through_to_other(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    coga_os = tmp_path / "project" / "coga"
    coga_os.mkdir(parents=True)
    other_venv = tmp_path / "some-other-venv"
    py = _stub_executable_in(other_venv)
    monkeypatch.setattr(update_cmd.sys, "executable", str(py))

    kind, where = update_cmd.running_cli_location(coga_os)
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
    host_py.write_text("#!/bin/sh\n")
    host_py.chmod(0o755)

    pipx_venv = tmp_path / "home" / ".local" / "pipx" / "venvs" / "coga"
    (pipx_venv / "bin").mkdir(parents=True)
    (pipx_venv / "pipx_metadata.json").write_text("{}\n")
    pipx_python = pipx_venv / "bin" / "python"
    pipx_python.symlink_to(host_py)
    monkeypatch.setattr(update_cmd.sys, "executable", str(pipx_python))

    kind, where = update_cmd.running_cli_location(coga_os)
    assert kind == "pipx", (
        "symlink resolution would land in homebrew Cellar; detection must "
        "stay on the unresolved venv path so pipx_metadata.json is found"
    )
    assert where == pipx_venv.absolute()


# --- external dependency check --------------------------------------------------
#
# `coga init` fails loud when a required-at-init external CLI (only `git`) is
# not on PATH; `gh` and `op` are enforced at their points of need instead.
# Captured before the autouse `_stub_init_dep_check` fixture replaces
# the module attribute, so these tests exercise the real implementation.
_real_dep_check = init_cmd._check_external_dependencies


def _which_missing(missing: set[str]):
    """A `shutil.which` stand-in that reports `missing` tools as absent."""
    return lambda name: None if name in missing else f"/usr/bin/{name}"


def test_dep_check_passes_when_all_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("coga.commands.init.shutil.which", _which_missing(set()))
    _real_dep_check()  # must not raise


def test_dep_check_ignores_missing_op(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """`op` is not required at init (it's enforced at launch when a ticket
    actually needs an `op://` secret), so a missing `op` must not crash init."""
    monkeypatch.setattr("coga.commands.init.shutil.which", _which_missing({"op"}))
    _real_dep_check()  # must not raise


def test_dep_check_ignores_missing_agent_clis(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """Agent CLIs (`claude`/`codex`) are not required at init — they're
    enforced at the point of need (launch/ticket/build, with an install
    hint), so a missing one must not crash init."""
    monkeypatch.setattr(
        "coga.commands.init.shutil.which", _which_missing({"claude", "codex"})
    )
    _real_dep_check()  # must not raise


def test_dep_check_ignores_missing_gh(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """`gh` is not required at init (managed skill installs degrade to a
    warn-with-hint skip, and the open-pr step / autoclose sweep fail loud at
    their point of need), so a missing `gh` must not crash init."""
    monkeypatch.setattr("coga.commands.init.shutil.which", _which_missing({"gh"}))
    _real_dep_check()  # must not raise


def test_dep_check_crashes_on_missing_git(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr("coga.commands.init.shutil.which", _which_missing({"git"}))
    with pytest.raises(SystemExit) as exc:
        _real_dep_check()
    assert exc.value.code == 2
    assert "git" in capsys.readouterr().err


def test_dep_check_omits_optional_tools_from_crash(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(
        "coga.commands.init.shutil.which", _which_missing({"git", "gh", "op"})
    )
    with pytest.raises(SystemExit):
        _real_dep_check()
    err = capsys.readouterr().err
    # Only the required-at-init tool is reported; point-of-need tools are
    # omitted even when they are also missing.
    assert "git" in err
    assert "gh" not in err
    assert "op" not in err


def test_init_bails_before_scaffolding_when_required_dep_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing required dep (git) stops `coga init` before it writes anything."""
    # Restore the real check (autouse no-ops it), then make `git` absent.
    monkeypatch.setattr(init_cmd, "_check_external_dependencies", _real_dep_check)
    monkeypatch.setattr("coga.commands.init.shutil.which", _which_missing({"git"}))

    target = tmp_path / "fresh"
    result = CliRunner().invoke(app, ["init", str(target), "--user", "tester"])

    assert result.exit_code == 2
    assert "git" in result.output
    assert not (target / "coga").exists()  # bailed before scaffolding
