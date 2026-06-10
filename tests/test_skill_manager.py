from __future__ import annotations

import io
import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.config import load_config
from relay.skill import Skill
from relay.skill_manager import (
    GH_SKILL_REQUIRED,
    SOURCE_SCHEMA,
    SkillManagerError,
    SkillResult,
    SkillUpdateSummary,
    hash_skill_tree,
    install_github_skill,
    install_local_skill,
    install_url_skill,
    read_source_metadata,
    remove_skill,
    render_update_pr_body,
    run_skill_update_pr_flow,
    status_skills,
    update_skills,
    write_source_metadata,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    relay_os = tmp_path / "relay-os"
    _write(
        relay_os / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        """,
    )
    _write(relay_os / "relay.local.toml", 'user = "marc"\n')
    monkeypatch.chdir(relay_os)
    return relay_os


def _completed(
    args: list[str],
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr=stderr)


def _gh_install_runner(commands: list[list[str]]):
    def runner(args, cwd=None):
        command = list(args)
        commands.append(command)
        if command == ["gh", "skill", "--help"]:
            return _completed(command, stdout="gh skill help")
        if command[:3] == ["gh", "skill", "install"]:
            if "--from-local" not in command:
                return _completed(command, stdout="installed")
            source = Path(command[3])
            dest = Path(command[command.index("--dir") + 1])
            skill = Skill.load(source / "SKILL.md")
            target = dest.joinpath(*skill.name.split("/"))
            shutil.copytree(source, target)
            return _completed(command, stdout="installed")
        if command[:3] == ["gh", "skill", "update"]:
            return _completed(command, stdout="updated")
        raise AssertionError(f"unexpected command: {command}")

    return runner


def _skill_zip(name: str, body: str = "Use the tool.\n") -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr(
            "bundle/SKILL.md",
            f"---\nname: {name}\n---\n{body}",
        )
        archive.writestr("bundle/scripts/run.sh", "echo ok\n")
    return out.getvalue()


def test_github_install_delegates_to_gh_skill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(_repo(tmp_path, monkeypatch))
    commands: list[list[str]] = []

    install_github_skill(
        cfg,
        "owner/repo",
        "tools/example",
        runner=_gh_install_runner(commands),
    )

    assert commands == [
        ["gh", "skill", "--help"],
        [
            "gh",
            "skill",
            "install",
            "owner/repo",
            "tools/example",
            "--dir",
            str(cfg.repo_root / "skills"),
        ],
    ]


def test_update_all_delegates_github_backed_skills_to_gh_skill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(_repo(tmp_path, monkeypatch))
    _write(
        cfg.repo_root / "skills" / "tools" / "example" / "SKILL.md",
        "---\nname: tools/example\n---\nhttps://github.com/example/skill\n",
    )
    commands: list[list[str]] = []

    summary = update_skills(
        cfg,
        all_skills=True,
        runner=_gh_install_runner(commands),
    )

    assert summary.results[0].status == "delegated"
    assert commands == [
        ["gh", "skill", "--help"],
        [
            "gh",
            "skill",
            "update",
            "--dir",
            str(cfg.repo_root / "skills"),
            "--all",
        ],
    ]


def test_install_url_downloads_local_installs_and_records_relay_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(_repo(tmp_path, monkeypatch))
    commands: list[list[str]] = []

    result = install_url_skill(
        cfg,
        "https://example.test/skill.zip",
        downloader=lambda url: _skill_zip("tools/example"),
        runner=_gh_install_runner(commands),
        now=lambda: "2026-05-13T12:00:00Z",
    )

    target = cfg.repo_root / "skills" / "tools" / "example"
    metadata = read_source_metadata(target)
    assert result.status == "installed"
    assert (target / "SKILL.md").is_file()
    assert metadata is not None
    assert metadata["source_type"] == "url"
    assert metadata["source_url"] == "https://example.test/skill.zip"
    assert metadata["installed_ref"] == "tools/example"
    assert commands[1][:4] == ["gh", "skill", "install", commands[1][3]]
    assert "--from-local" in commands[1]


def test_install_local_delegates_to_gh_skill_from_local(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(_repo(tmp_path, monkeypatch))
    source = tmp_path / "source-skill"
    _write(source / "SKILL.md", "---\nname: tools/local\n---\n")
    commands: list[list[str]] = []

    install_local_skill(cfg, source, runner=_gh_install_runner(commands))

    assert commands == [
        ["gh", "skill", "--help"],
        [
            "gh",
            "skill",
            "install",
            str(source.resolve()),
            "--from-local",
            "--dir",
            str(cfg.repo_root / "skills"),
        ],
    ]


def test_url_update_skips_locally_adapted_skill_without_fetch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(_repo(tmp_path, monkeypatch))
    skill_dir = cfg.repo_root / "skills" / "tools" / "example"
    _write(skill_dir / "SKILL.md", "---\nname: tools/example\n---\nold\n")
    digest = hash_skill_tree(skill_dir)
    write_source_metadata(
        skill_dir,
        {
            "schema": SOURCE_SCHEMA,
            "source_type": "url",
            "source_url": "https://example.test/skill.zip",
            "selector": None,
            "installed_ref": "tools/example",
            "installed_at": "2026-05-13T12:00:00Z",
            "updated_at": "2026-05-13T12:00:00Z",
            "source_digest": "old-source",
            "source_tree_digest": digest,
            "installed_tree_digest": digest,
        },
    )
    (skill_dir / "SKILL.md").write_text("---\nname: tools/example\n---\nlocal edit\n")

    def no_fetch(url: str) -> bytes:
        raise AssertionError("locally adapted skills should not be fetched")

    summary = update_skills(cfg, "tools/example", downloader=no_fetch)

    assert summary.results[0].status == "skipped-local-adaptation"
    assert "local edit" in (skill_dir / "SKILL.md").read_text()


def test_url_update_replaces_clean_skill_and_refreshes_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(_repo(tmp_path, monkeypatch))
    skill_dir = cfg.repo_root / "skills" / "tools" / "example"
    _write(skill_dir / "SKILL.md", "---\nname: tools/example\n---\nold\n")
    digest = hash_skill_tree(skill_dir)
    write_source_metadata(
        skill_dir,
        {
            "schema": SOURCE_SCHEMA,
            "source_type": "url",
            "source_url": "https://example.test/skill.zip",
            "selector": None,
            "installed_ref": "tools/example",
            "installed_at": "2026-05-13T12:00:00Z",
            "updated_at": "2026-05-13T12:00:00Z",
            "source_digest": "old-source",
            "source_tree_digest": digest,
            "installed_tree_digest": digest,
        },
    )

    summary = update_skills(
        cfg,
        "tools/example",
        downloader=lambda url: _skill_zip("tools/example", body="new\n"),
        now=lambda: "2026-05-13T12:30:00Z",
    )

    metadata = read_source_metadata(skill_dir)
    assert summary.results[0].status == "updated"
    assert "new" in (skill_dir / "SKILL.md").read_text()
    assert metadata is not None
    assert metadata["updated_at"] == "2026-05-13T12:30:00Z"
    assert metadata["installed_tree_digest"] == hash_skill_tree(skill_dir)


def test_status_check_reports_url_update_availability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(_repo(tmp_path, monkeypatch))
    skill_dir = cfg.repo_root / "skills" / "tools" / "example"
    _write(skill_dir / "SKILL.md", "---\nname: tools/example\n---\nold\n")
    digest = hash_skill_tree(skill_dir)
    write_source_metadata(
        skill_dir,
        {
            "schema": SOURCE_SCHEMA,
            "source_type": "url",
            "source_url": "https://example.test/skill.zip",
            "selector": None,
            "installed_ref": "tools/example",
            "installed_at": "2026-05-13T12:00:00Z",
            "updated_at": "2026-05-13T12:00:00Z",
            "source_digest": "old-source",
            "source_tree_digest": digest,
            "installed_tree_digest": digest,
        },
    )

    results = status_skills(
        cfg,
        check=True,
        downloader=lambda url: _skill_zip("tools/example", body="new\n"),
    )

    assert results[0].name == "tools/example"
    assert results[0].status == "upstream-changed"


def test_status_labels_non_relay_skill_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(_repo(tmp_path, monkeypatch))
    _write(
        cfg.repo_root / "skills" / "custom" / "SKILL.md",
        "---\nname: custom\n---\nlocal-only\n",
    )
    _write(
        cfg.repo_root / "skills" / "github-tool" / "SKILL.md",
        "---\nname: github-tool\n---\nhttps://github.com/example/skill\n",
    )

    results = {result.name: result for result in status_skills(cfg)}

    assert results["custom"].source_type == "unknown"
    assert results["custom"].status == "unmanaged"
    assert results["custom"].message == "no Relay source metadata"
    assert results["github-tool"].source_type == "github"
    assert results["github-tool"].status == "delegated"
    assert results["github-tool"].message == "managed by gh skill metadata"


def test_status_reports_bundled_bootstrap_skills(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(_repo(tmp_path, monkeypatch))
    _write(
        cfg.repo_root / "bootstrap" / "skills" / "eval" / "ticket-diagnostic" / "SKILL.md",
        "---\nname: eval/ticket-diagnostic\n---\nbundled\n",
    )

    results = {result.name: result for result in status_skills(cfg)}

    assert results["eval/ticket-diagnostic"].source_type == "bundled"
    assert results["eval/ticket-diagnostic"].status == "package-backed"
    assert "relay init --update" in results["eval/ticket-diagnostic"].message


def test_status_marks_local_skill_that_overrides_bundled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(_repo(tmp_path, monkeypatch))
    _write(
        cfg.repo_root / "bootstrap" / "skills" / "tools" / "example" / "SKILL.md",
        "---\nname: tools/example\n---\nbundled\n",
    )
    _write(
        cfg.repo_root / "skills" / "tools" / "example" / "SKILL.md",
        "---\nname: tools/example\n---\nlocal\n",
    )

    results = {result.name: result for result in status_skills(cfg)}

    assert results["tools/example"].status == "local-override"
    assert "shadows bundled" in results["tools/example"].message


def test_update_all_skips_bundled_bootstrap_skills(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(_repo(tmp_path, monkeypatch))
    _write(
        cfg.repo_root / "bootstrap" / "skills" / "eval" / "ticket-diagnostic" / "SKILL.md",
        "---\nname: eval/ticket-diagnostic\n---\nbundled\n",
    )

    def runner(args, cwd=None):
        raise AssertionError(f"unexpected command: {list(args)}")

    summary = update_skills(cfg, all_skills=True, runner=runner)
    results = {result.name: result for result in summary.results}

    assert results["eval/ticket-diagnostic"].source_type == "bundled"
    assert results["eval/ticket-diagnostic"].status == "skipped-bundled"
    assert "pip install --upgrade relay-os" in results["eval/ticket-diagnostic"].message


def test_update_one_bundled_skill_reports_package_update_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(_repo(tmp_path, monkeypatch))
    _write(
        cfg.repo_root / "bootstrap" / "skills" / "eval" / "ticket-diagnostic" / "SKILL.md",
        "---\nname: eval/ticket-diagnostic\n---\nbundled\n",
    )

    summary = update_skills(cfg, "eval/ticket-diagnostic", runner=_gh_install_runner([]))

    assert summary.results[0].status == "skipped-bundled"
    assert summary.results[0].source_type == "bundled"


def test_remove_requires_exact_installed_skill_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(_repo(tmp_path, monkeypatch))
    _write(cfg.repo_root / "skills" / "foo" / "SKILL.md", "---\nname: foo\n---\n")
    _write(cfg.repo_root / "skills" / "foobar" / "SKILL.md", "---\nname: foobar\n---\n")

    removed = remove_skill(cfg, "foo")

    assert removed == cfg.repo_root / "skills" / "foo"
    assert not (cfg.repo_root / "skills" / "foo").exists()
    assert (cfg.repo_root / "skills" / "foobar" / "SKILL.md").is_file()
    with pytest.raises(SkillManagerError):
        remove_skill(cfg, "fo")


def test_missing_gh_skill_fails_loud_with_upgrade_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(_repo(tmp_path, monkeypatch))

    def old_gh(args, cwd=None):
        command = list(args)
        assert command == ["gh", "skill", "--help"]
        return _completed(command, returncode=1, stderr="unknown command: skill")

    with pytest.raises(SkillManagerError) as exc:
        install_github_skill(cfg, "owner/repo", runner=old_gh)

    assert GH_SKILL_REQUIRED in str(exc.value)
    assert "unknown command: skill" in str(exc.value)


def test_install_url_checks_gh_skill_before_downloading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(_repo(tmp_path, monkeypatch))

    def old_gh(args, cwd=None):
        return _completed(list(args), returncode=1, stderr="unknown command: skill")

    def no_download(url: str) -> bytes:
        raise AssertionError("download should not happen before gh skill check")

    with pytest.raises(SkillManagerError) as exc:
        install_url_skill(
            cfg,
            "https://example.test/skill.zip",
            runner=old_gh,
            downloader=no_download,
        )

    assert GH_SKILL_REQUIRED in str(exc.value)


def test_install_github_multi_skill_repo_translates_gh_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(_repo(tmp_path, monkeypatch))

    def multi_skill_runner(args, cwd=None):
        command = list(args)
        if command == ["gh", "skill", "--help"]:
            return _completed(command, stdout="gh skill help")
        return _completed(
            command,
            returncode=1,
            stderr=(
                "Using ref v0.1.3 (f73062ca)\n"
                "must specify a skill name when not running interactively\n"
            ),
        )

    with pytest.raises(SkillManagerError) as exc:
        install_github_skill(
            cfg,
            "https://github.com/google/agents-cli",
            runner=multi_skill_runner,
        )

    message = str(exc.value)
    assert "https://github.com/google/agents-cli" in message
    assert "relay skill install https://github.com/google/agents-cli <skill>" in message
    assert "gh api repos/google/agents-cli/contents/skills" in message
    assert "Usage:" not in message


def test_install_local_multi_skill_dir_translates_gh_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(_repo(tmp_path, monkeypatch))
    source = tmp_path / "local-skills"
    source.mkdir()

    def multi_skill_runner(args, cwd=None):
        command = list(args)
        if command == ["gh", "skill", "--help"]:
            return _completed(command, stdout="gh skill help")
        return _completed(
            command,
            returncode=1,
            stderr="must specify a skill name when not running interactively",
        )

    with pytest.raises(SkillManagerError) as exc:
        install_local_skill(cfg, source, runner=multi_skill_runner)

    message = str(exc.value)
    assert str(source) in message
    assert f"ls {source}" in message


def test_dream_pr_summary_path_runs_verification_and_opens_or_updates_pr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(_repo(tmp_path, monkeypatch))
    summary = SkillUpdateSummary(
        results=[
            SkillResult(
                name="tools/example",
                source_type="url",
                status="updated",
                message="updated from URL source",
                changed=True,
            )
        ]
    )
    commands: list[list[str]] = []

    def runner(args, cwd=None):
        command = list(args)
        commands.append(command)
        if command == ["relay", "validate", "--json"]:
            return _completed(command, stdout='{"issues":[]}\n')
        if command == ["git", "branch", "--show-current"]:
            return _completed(command, stdout="main\n")
        if command == ["git", "checkout", "-B", "relay/skill-update"]:
            return _completed(command)
        if command[:3] == ["git", "add", "--"]:
            return _completed(command)
        if command[:4] == ["git", "diff", "--cached", "--quiet"]:
            # returncode 1 == there are staged changes to commit.
            return _completed(command, returncode=1)
        if command == ["git", "commit", "-m", "Update Relay-managed skills"]:
            return _completed(command)
        if command[:4] == ["gh", "pr", "list", "--head"]:
            assert command[4] == "relay/skill-update"
            return _completed(command, stdout="")
        if command == ["git", "push", "-u", "origin", "relay/skill-update"]:
            return _completed(command, stdout="")
        if command[:4] == ["gh", "pr", "create", "--draft"]:
            body_file = Path(command[command.index("--body-file") + 1])
            assert "`tools/example`: updated" in body_file.read_text()
            return _completed(command, stdout="https://github.com/FastJVM/relay/pull/143\n")
        if command == ["git", "checkout", "main"]:
            return _completed(command)
        raise AssertionError(f"unexpected command: {command}")

    result = run_skill_update_pr_flow(
        cfg,
        summary,
        title="Update Relay-managed skills",
        verification_commands=["relay validate --json"],
        runner=runner,
    )

    assert result.pr_url == "https://github.com/FastJVM/relay/pull/143"
    assert result.verification[0].returncode == 0
    # Updates are committed onto the dedicated branch and the checkout is
    # restored to where the caller left it (`main`), never committed there.
    assert ["git", "checkout", "-B", "relay/skill-update"] in commands
    assert ["git", "commit", "-m", "Update Relay-managed skills"] in commands
    assert ["git", "push", "-u", "origin", "relay/skill-update"] in commands
    assert ["git", "checkout", "main"] in commands


def test_dream_pr_summary_skips_pr_when_nothing_changed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run where no skill changed must open no PR — opening an empty PR would
    just fail on `gh pr create` — and must touch git at all."""
    cfg = load_config(_repo(tmp_path, monkeypatch))
    summary = SkillUpdateSummary(
        results=[
            SkillResult(
                name="bootstrap/example",
                source_type="bundled",
                status="skipped-bundled",
                message="bundled skill updates come from the relay package",
                changed=False,
            )
        ]
    )

    def runner(args, cwd=None):
        raise AssertionError(f"no command expected, got: {list(args)}")

    result = run_skill_update_pr_flow(
        cfg,
        summary,
        title="Update Relay-managed skills",
        verification_commands=["relay validate --json"],
        runner=runner,
    )

    assert result.pr_url is None
    assert result.verification == []


def test_dream_pr_summary_skips_pr_when_commit_is_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A `changed=True` result that leaves no on-disk diff (e.g. an opaque
    `gh skill update` that found nothing upstream) must not error on an empty
    commit — it stages, sees no diff, opens no PR, and restores the branch."""
    cfg = load_config(_repo(tmp_path, monkeypatch))
    summary = SkillUpdateSummary(
        results=[
            SkillResult(
                name="gh-managed",
                source_type="github",
                status="delegated",
                message="delegated GitHub-backed skill updates to gh skill",
                changed=True,
            )
        ]
    )
    commands: list[list[str]] = []

    def runner(args, cwd=None):
        command = list(args)
        commands.append(command)
        if command == ["git", "branch", "--show-current"]:
            return _completed(command, stdout="main\n")
        if command == ["git", "checkout", "-B", "relay/skill-update"]:
            return _completed(command)
        if command[:3] == ["git", "add", "--"]:
            return _completed(command)
        if command[:4] == ["git", "diff", "--cached", "--quiet"]:
            # returncode 0 == nothing staged; the flow must bail out cleanly.
            return _completed(command, returncode=0)
        if command == ["git", "checkout", "main"]:
            return _completed(command)
        raise AssertionError(f"unexpected command: {command}")

    result = run_skill_update_pr_flow(
        cfg,
        summary,
        title="Update Relay-managed skills",
        verification_commands=["relay validate --json"],
        runner=runner,
    )

    assert result.pr_url is None
    assert result.verification == []
    # No commit, no PR — but the dedicated branch was created and the checkout
    # restored to where the caller left it.
    assert ["git", "commit", "-m", "Update Relay-managed skills"] not in commands
    assert ["git", "checkout", "main"] in commands


def test_update_cli_emits_json_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(_repo(tmp_path, monkeypatch))
    _write(cfg.repo_root / "skills" / "tools" / "example" / "SKILL.md", "---\nname: tools/example\n---\n")

    def fake_update_skills(cfg_arg, skill=None, *, all_skills=False):
        assert skill == "tools/example"
        return SkillUpdateSummary(
            results=[
                SkillResult(
                    name="tools/example",
                    source_type="github",
                    status="delegated",
                    message="delegated tools/example update to gh skill",
                )
            ]
        )

    monkeypatch.setattr("relay.commands.skill.update_skills", fake_update_skills)
    result = CliRunner().invoke(app, ["skill", "update", "tools/example", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["counts"] == {"delegated": 1}


def test_pr_body_lists_skipped_local_adaptations() -> None:
    body = render_update_pr_body(
        SkillUpdateSummary(
            results=[
                SkillResult(
                    name="tools/example",
                    source_type="url",
                    status="skipped-local-adaptation",
                    message="local files differ from recorded installed digest; not overwriting",
                )
            ]
        )
    )

    assert "`tools/example`: skipped-local-adaptation" in body
    assert "not overwriting" in body
