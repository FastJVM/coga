from __future__ import annotations

import importlib.util
import os
import shlex
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest
import typer
from typer.testing import CliRunner

from coga.config import load_config
from coga.launch import LaunchResult
from coga.tasks import resolve_task
from coga.ticket import Ticket
from coga.validate import Issue, TaskValidationError

from conftest import seed_direct_body_workflow


RETIRE_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "src/coga/resources/templates/coga/bootstrap/retire/ticket.py"
)


def _load_retire_script():
    """Import the packaged `bootstrap/retire/ticket.py` as a module.

    Its `__main__` guard keeps loading side-effect free; tests drive its Typer
    `app` directly, which bypasses the alias and launch framing.
    """
    spec = importlib.util.spec_from_file_location("coga_bootstrap_retire", RETIRE_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


retire_cmd = _load_retire_script()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip(), encoding="utf-8", newline="\n")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    coga_os = tmp_path / "coga"
    coga_os.mkdir()
    _write(
        coga_os / "coga.toml",
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
        coga_os / "coga.local.toml",
        """
        user = "marc"
        [notification.slack]
        enabled = false
        """,
    )
    # Retire creates its task with the `direct/body` workflow; the minimal
    # test repo needs that shipped workflow + skill present (real repos get it
    # from `coga init`) or `create_task` fails to load the workflow.
    seed_direct_body_workflow(coga_os)
    return coga_os


def _seed_finished_task(
    repo: Path, slug: str = "fix-retry-logic", status: str = "canceled"
) -> Path:
    task_dir = repo / "tasks" / slug
    task_dir.mkdir(parents=True)
    _write(
        task_dir / "ticket.md",
        f"""
        ---
        title: Fix retry logic
        status: {status}
        owner: marc
        ---

        ## Description

        Done.
        """,
    )
    (task_dir / "blackboard.md").write_text("# Fix retry logic\n", encoding="utf-8", newline="\n")
    (task_dir / "log.md").write_text("", encoding="utf-8", newline="\n")
    return task_dir


def test_retire_uses_repo_retire_template_override(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    _seed_finished_task(repo, "fix-retry-logic")
    _write(repo / "resources" / "retire.md", "Repo retire pass for `{slug}`.\n")

    result = CliRunner().invoke(retire_cmd.app, ["fix-retry-logic", "--no-launch"])

    assert result.exit_code == 0, result.output
    body = Ticket.read(repo / "tasks" / "retire-fix-retry-logic.md").body
    assert "Repo retire pass for `fix-retry-logic`." in body
    assert "Retire the canceled ticket" not in body


@pytest.mark.parametrize(
    "placeholder", ["{json: true}", "{slug.missing}", "{slug[foo]}", "{"],
)
def test_retire_override_with_stray_brace_names_the_file(
    repo: Path, monkeypatch: pytest.MonkeyPatch, placeholder: str,
) -> None:
    monkeypatch.chdir(repo)
    _seed_finished_task(repo, "fix-retry-logic")
    override = repo / "resources" / "retire.md"
    _write(override, "Retire {slug} using " + placeholder + ".\n")

    result = CliRunner().invoke(retire_cmd.app, ["fix-retry-logic", "--no-launch"])

    assert result.exit_code == 2
    assert str(override) in result.output
    assert "Traceback" not in result.output
    assert not (repo / "tasks" / "retire-fix-retry-logic.md").exists()


def test_retire_defaults_to_the_default_agent_key(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    toml = repo / "coga.toml"
    toml.write_text(
        'default_agent = "codex"\n'
        + toml.read_text(encoding="utf-8")
        + '\n[agents.codex]\ncli = "codex"\nfile = "AGENTS.md"\n',
        encoding="utf-8", newline="\n",
    )
    monkeypatch.chdir(repo)
    _seed_finished_task(repo, "fix-retry-logic")

    result = CliRunner().invoke(retire_cmd.app, ["fix-retry-logic", "--no-launch"])

    assert result.exit_code == 0, result.output
    assert "Retire: using main agent codex (agent type codex)" in result.output
    ticket = Ticket.read(repo / "tasks" / "retire-fix-retry-logic.md")
    assert ticket.agent == "codex"


def test_retire_reports_created_task_validation_failure(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    _seed_finished_task(repo, "fix-retry-logic")

    def reject_created_task(  # type: ignore[no-untyped-def]
        cfg, ref, *, action: str
    ) -> None:
        raise TaskValidationError(
            [
                Issue(
                    kind="broken-ref",
                    task=ref.id_slug,
                    message="generated retire ticket is malformed",
                    severity="error",
                )
            ],
            action=action,
        )

    monkeypatch.setattr("coga.validate.assert_task_valid", reject_created_task)

    result = CliRunner().invoke(retire_cmd.app, ["fix-retry-logic", "--no-launch"])

    assert result.exit_code == 2
    combined = result.output + (result.stderr or "")
    assert "task validation failed after create" in combined
    assert "generated retire ticket is malformed" in combined
    assert "Retire: created task" not in combined
    assert (repo / "tasks" / "retire-fix-retry-logic.md").is_file()


def test_retire_refuses_non_done_target(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    task_dir = repo / "tasks" / "in-flight"
    task_dir.mkdir(parents=True)
    _write(
        task_dir / "ticket.md",
        """
        ---
        title: Still going
        status: active
        owner: marc
        ---

        ## Description

        Active.
        """,
    )
    (task_dir / "blackboard.md").write_text("", encoding="utf-8", newline="\n")
    (task_dir / "log.md").write_text("", encoding="utf-8", newline="\n")

    result = CliRunner().invoke(retire_cmd.app, ["in-flight", "--no-launch"])

    assert result.exit_code == 2
    assert "Retire only operates on done or canceled tickets" in result.output
    assert "is 'active'" in result.output
    # Refused — no retire create task created.
    assert not (repo / "tasks" / "retire-in-flight").exists()


def test_retire_deletes_a_done_ticket_without_a_retro_task(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A done ticket's learning landed with its PR, so retire just deletes it."""
    monkeypatch.chdir(repo)
    task_dir = _seed_finished_task(repo, "fix-retry-logic", status="done")
    launched: list[str] = []
    monkeypatch.setattr(
        "coga.launch.launch", lambda slug, **_kw: launched.append(slug)
    )

    result = CliRunner().invoke(retire_cmd.app, ["fix-retry-logic"])

    assert result.exit_code == 0, result.output
    assert f"Retire: fix-retry-logic: deleted {task_dir}" in result.output
    assert not task_dir.exists()
    assert not (repo / "tasks" / "retire-fix-retry-logic.md").exists()
    assert "Retire: creating task" not in result.output
    assert launched == []


def test_retire_refuses_unknown_slug(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    _seed_finished_task(repo, "real-task")

    result = CliRunner().invoke(retire_cmd.app, ["no-such-task", "--no-launch"])

    assert result.exit_code == 2
    assert "no-such-task" in result.output


def test_retire_launches_after_create(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    _seed_finished_task(repo, "fix-retry-logic")
    calls: list[dict[str, object]] = []

    def fake_launch(
        task: str,
        agent_override: str | None,
        prompt_report: bool,
        idle_timeout: float | None = None,
        max_session: float | None = None,
        return_timeout: bool = False,
    ) -> LaunchResult:
        ticket = Ticket.read(repo / "tasks" / f"{task}.md")
        assert ticket.status == "active"
        calls.append(
            {
                "task": task,
                "agent_override": agent_override,
                "prompt_report": prompt_report,
                "idle_timeout": idle_timeout,
                "max_session": max_session,
                "return_timeout": return_timeout,
            }
        )
        typer.echo("fake launch called")
        return LaunchResult()

    monkeypatch.setattr("coga.launch.launch", fake_launch)

    result = CliRunner().invoke(retire_cmd.app, ["fix-retry-logic"])

    assert result.exit_code == 0, result.output
    assert "Retire: created task retire-fix-retry-logic" in result.output
    assert "(active)" in result.output
    assert "Retire: launching retire-fix-retry-logic" in result.output
    assert "fake launch called" in result.output
    # The audit log is the repo-global `coga/log.md` now; filter it to the
    # retire task's ref instead of reading a per-task log.md (which is gone).
    from coga.config import load_config
    from coga.logfile import task_log_lines

    cfg = load_config(repo)
    log = "\n".join(task_log_lines(cfg, "retire-fix-retry-logic"))
    assert "created (status=active)" in log
    assert calls == [
        {
            "task": "retire-fix-retry-logic",
            "agent_override": None,
            "prompt_report": False,
            "idle_timeout": None,
            "max_session": None,
            "return_timeout": False,
        }
    ]


def _run_coga(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the real CLI, so `retire` goes through its alias and bootstrap launch."""
    env = os.environ.copy()
    source = str(Path(__file__).resolve().parents[1] / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = source if not existing else source + os.pathsep + existing
    return subprocess.run(
        [sys.executable, "-m", "coga.cli", *args],
        cwd=repo,
        env=env,
        check=False,
        capture_output=True,
        text=True, encoding="utf-8",
    )


def test_retire_alias_deletes_a_done_ticket(repo: Path) -> None:
    task_dir = _seed_finished_task(repo, "fix-retry-logic", status="done")

    result = _run_coga(repo, "retire", "fix-retry-logic")

    assert result.returncode == 0, result.stderr
    assert "→ coga launch bootstrap/retire -- fix-retry-logic" in result.stderr
    assert "Retire: target task fix-retry-logic" in result.stdout
    assert not task_dir.exists()


def test_retire_alias_retires_a_done_ticket_without_configured_agents(
    repo: Path,
) -> None:
    (repo / "coga.toml").write_text('version = 1\ndefault_status = "draft"\n', encoding="utf-8", newline="\n")
    task_dir = _seed_finished_task(repo, "fix-retry-logic", status="done")

    result = _run_coga(repo, "retire", "fix-retry-logic")

    assert result.returncode == 0, result.stderr
    assert not task_dir.exists()


def test_retire_alias_forwards_no_launch_for_a_canceled_ticket(repo: Path) -> None:
    _seed_finished_task(repo, "fix-retry-logic")

    result = _run_coga(repo, "retire", "fix-retry-logic", "--no-launch")

    assert result.returncode == 0, result.stderr
    assert "Retire: launch skipped (--no-launch)" in result.stdout
    assert (repo / "tasks" / "retire-fix-retry-logic.md").exists()


def test_retire_alias_refuses_an_unknown_slug(repo: Path) -> None:
    result = _run_coga(repo, "retire", "no-such-task", "--no-launch")

    assert result.returncode == 2
    assert "no-such-task" in result.stderr


def test_retire_alias_help_reaches_the_script(repo: Path) -> None:
    result = _run_coga(repo, "retire", "--help")

    assert result.returncode == 0, result.stderr
    assert "Usage: coga retire" in result.stdout
    assert "--no-launch" in result.stdout


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, encoding="utf-8"
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return proc


def _retire_status(repo: Path, slug: str) -> str:
    return Ticket.read(repo / "tasks" / f"retire-{slug}.md").frontmatter["status"]


def _merged_worktree_ticket(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: str = "canceled",
) -> tuple[str, Path]:
    """A finished ticket whose merged branch is still checked out in a linked worktree.

    Returns `(slug, feature_worktree)`; the checkout is what retire's cleanup
    is expected to dispose of.
    """
    monkeypatch.chdir(repo)
    monkeypatch.setattr(
        "coga.branchcleanup.prs_for_head", lambda _branch, _state: []
    )
    _git(repo, "init", "-b", "main", ".")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Tester")
    (repo / "seed.txt").write_text("seed", encoding="utf-8", newline="\n")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-m", "seed")
    feature = tmp_path / "feature"
    _git(repo, "worktree", "add", str(feature), "-b", "fix-retry-branch")
    (feature / "work.txt").write_text("work", encoding="utf-8", newline="\n")
    _git(feature, "add", "work.txt")
    _git(feature, "commit", "-m", "work")
    _git(repo, "merge", "--ff-only", "fix-retry-branch")

    slug = "fix-retry-logic"
    task_dir = repo / "tasks" / slug
    task_dir.mkdir(parents=True)
    _write(
        task_dir / "ticket.md",
        f"""
        ---
        title: Fix retry logic
        status: {status}
        owner: marc
        ---

        ## Description

        Done.

        <!-- coga:blackboard -->

        ## Dev
        branch: fix-retry-branch
        worktree: {feature}
        pr: https://github.com/owner/repo/pull/9
        """,
    )
    (task_dir / "log.md").write_text("", encoding="utf-8", newline="\n")
    return slug, feature




def _seed_retire_worklist(repo: Path, *entries: rw.RetireFollowUp) -> Path:
    """The autoclose sweep's durable worklist, naming `entries` as owed retires."""
    template = repo / "recurring" / "autoclose-merged"
    template.mkdir(parents=True)
    (template / "ticket.md").write_text("template\n", encoding="utf-8", newline="\n")
    path = template / rw.RETIRE_WORKLIST_FILENAME
    path.write_text(rw.render_worklist(rw.RETIRE_WORKLIST_HEADER, entries), encoding="utf-8", newline="\n")
    return path










def test_retire_leaves_dirty_worktree_in_place(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    _git(repo, "init", "-b", "main", ".")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Tester")
    (repo / "seed.txt").write_text("seed", encoding="utf-8", newline="\n")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-m", "seed")
    feature = tmp_path / "feature"
    _git(repo, "worktree", "add", str(feature), "-b", "fix-retry-branch")
    (feature / "uncommitted.txt").write_text("work in progress", encoding="utf-8", newline="\n")

    slug = "fix-retry-logic"
    task_dir = repo / "tasks" / slug
    task_dir.mkdir(parents=True)
    _write(
        task_dir / "ticket.md",
        f"""
        ---
        title: Fix retry logic
        status: canceled
        owner: marc
        ---

        ## Description

        Done.

        <!-- coga:blackboard -->

        ## Dev
        branch: fix-retry-branch
        worktree: {feature}
        """,
    )
    (task_dir / "log.md").write_text("", encoding="utf-8", newline="\n")

    result = CliRunner().invoke(retire_cmd.app, [slug, "--no-launch"])

    assert result.exit_code == 0, result.output
    assert _retire_status(repo, slug) == "active"
    assert (feature / "uncommitted.txt").read_text() == "work in progress"
    assert _git(feature, "branch", "--show-current").stdout.strip() == "fix-retry-branch"



def test_retire_resolves_unique_prefix(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    _seed_finished_task(repo, "fix-retry-logic")

    result = CliRunner().invoke(retire_cmd.app, ["fix-retr", "--no-launch"])

    assert result.exit_code == 0, result.output
    assert "Retire: target task fix-retry-logic" in result.output
    assert (repo / "tasks" / "retire-fix-retry-logic.md").is_file()
