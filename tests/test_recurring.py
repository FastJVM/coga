from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from coga import git as coga_git
from coga import recurring_runner as recurring_cmd
from coga.cli import app
from coga.config import load_config
from coga.logfile import task_log_lines
from coga.paths import tasks_dir
from coga.recurring import (
    list_templates,
    read_last_serviced_period,
    create_named,
    list_templates,
    scan_due,
)
from coga.taskfile import read_blackboard, replace_blackboard, upsert_blackboard
from coga.tasks import list_tasks
from coga.ticket import Ticket
from coga.validate import Issue, TaskValidationError


_TEMPLATES_COGA_OS = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "coga"
    / "resources"
    / "templates"
    / "coga"
)

SHIPPED_DREAM_DIR = _TEMPLATES_COGA_OS / "recurring" / "dream"
SHIPPED_DIRECT_BODY_SKILL_DIR = _TEMPLATES_COGA_OS / "skills" / "direct" / "body"
SHIPPED_DIRECT_BODY_WORKFLOW = _TEMPLATES_COGA_OS / "workflows" / "direct" / "body.md"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _write_recurring(company: Path, name: str, text: str) -> None:
    """Write a recurring task as a ticket-format directory."""
    _write(company / "recurring" / name / "ticket.md", text)


def _seed_template_blackboard(company: Path, name: str, region: str) -> None:
    """Seed a recurring template's persistent working state.

    In the single-file format a template's cross-run state — its `state_keys`
    values and the `last_serviced_period` high-water mark — lives in the
    blackboard region of `recurring/<name>/ticket.md`, not a separate
    `blackboard.md`. `upsert_blackboard` adds the fence if the hand-authored
    template ticket doesn't have one yet.

    The fence must stay on its own line, so the region text is normalized to
    start with a blank line after the fence (matching what `read_blackboard`
    returns and the high-water writer produces).
    """
    region_text = "\n\n" + region.lstrip("\n")
    upsert_blackboard(company / "recurring" / name / "ticket.md", region_text)


def _read_template_blackboard(company: Path, name: str) -> str:
    """Read a recurring template's blackboard region from its `ticket.md`."""
    return read_blackboard(
        company / "recurring" / name / "ticket.md", blackboard_required=False
    )


def _blackboard_of_text(ticket_text: str) -> str:
    """Return the blackboard region (text after the fence) of a ticket string.

    The on-disk `read_blackboard` takes a path; the git tests need the same
    region out of a `git show`-ed ticket blob, so they can compare a period
    task's blackboard state that now lives inside its `ticket.md`.
    """
    from coga.taskfile import _fence_matches

    matches = _fence_matches(ticket_text)
    if not matches:
        return ""
    return ticket_text[matches[0].end():]


def _template_ticket_with_blackboard(company: Path, name: str, region: str) -> str:
    """Return the template `ticket.md` text with its blackboard region replaced.

    Used by the cross-branch race tests that previously pushed a competing
    `blackboard.md`: under the single-file format the load-bearing template
    state is the blackboard region of `ticket.md`, so a competing commit must
    write the whole ticket with that region swapped in.
    """
    from coga.taskfile import BLACKBOARD_FENCE, split_body
    from coga.ticket import Ticket

    path = company / "recurring" / name / "ticket.md"
    ticket = Ticket.read(path)
    above, _ = split_body(ticket.body, blackboard_required=False)
    body = f"{above.rstrip(chr(10))}\n\n{BLACKBOARD_FENCE}\n{region}"
    ticket.body = body
    return ticket.render()


def _seed_global_log(git_repo) -> None:
    """Seed the repo-global `coga/log.md` and its union-merge attribute.

    The `git_repo` conftest fixture seeds `coga/` but no global log or
    `.gitattributes`. Period history (`created recurring/<name> for <period>`)
    now lands in this single repo-global log, which is committed locally and
    pushed on the same branch (not via the cross-branch task overlay), and is
    marked `merge=union` so concurrent appends across branches merge cleanly.
    The caller stages/commits — this only writes the files.
    """
    coga_os = git_repo.coga_os
    (coga_os / "log.md").write_text("")
    (coga_os / ".gitattributes").write_text("/log.md merge=union\n")
    git_repo.git("add", "coga/log.md", "coga/.gitattributes")


def _freeze_recurring_now(monkeypatch, when: datetime) -> None:
    """Pin `coga.recurring`'s wall clock to `when`.

    The deterministic recurring tests inject `now=` straight into `scan_due`
    / `create_named`, but the ones that exercise the CLI (`coga recurring`,
    `coga recurring launch`) can't — the command derives the current period
    from `datetime.now()`. Without this the period key tracks the real ISO
    week, so a test asserting a specific `2026-Wnn` only passes during that
    calendar week. Subclassing keeps every other `datetime` use intact and
    only overrides `.now()`.
    """

    class _FixedNow(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ARG003 - match datetime.now signature
            return when

    monkeypatch.setattr("coga.recurring.datetime", _FixedNow)


def _seed_direct_body_workflow(company: Path) -> None:
    """Seed the `direct/body` workflow + skill the creator freezes onto
    workflow-less recurring templates (e.g. Dream).

    Recurring tasks create straight to `active`, and every task past `draft`
    carries a workflow, so a template that declares none now runs through
    `direct/body`. Real repos get the file from `coga init`; the minimal test
    repos must copy it from the shipped templates or `create_task` fails to
    load the workflow.
    """
    skill_dst = company / "skills" / "direct" / "body"
    skill_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SHIPPED_DIRECT_BODY_SKILL_DIR, skill_dst, dirs_exist_ok=True)
    wf_dst = company / "workflows" / "direct" / "body.md"
    wf_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(SHIPPED_DIRECT_BODY_WORKFLOW, wf_dst)


_SCRIPT_WORKFLOW = "script-run/run"
_SCRIPT_SKILL = "script-run/run"


def _seed_script_workflow(company: Path) -> None:
    """Seed a real one-step SCRIPT workflow + skill.

    A recurring template that points its `workflow:` at this runs as a script:
    the single step's skill carries a `script:` entry, which is exactly what
    `is_script_launch` detects. Script runs produce live console output, so they
    are safe to create and launch unattended. Tests that need a non-interactive
    template to run without a TTY use `_write_recurring_script` to point at it.
    """
    skill_dir = company / "skills" / _SCRIPT_SKILL
    skill_dir.mkdir(parents=True, exist_ok=True)
    _write(
        skill_dir / "SKILL.md",
        f"""
        ---
        name: {_SCRIPT_SKILL}
        description: stub script skill
        script: run.sh
        ---

        # Script run
        """,
    )
    (skill_dir / "run.sh").write_text("#!/bin/sh\nexit 0\n")
    _write(
        company / "workflows" / f"{_SCRIPT_WORKFLOW}.md",
        f"""
        ---
        name: {_SCRIPT_WORKFLOW}
        description: One-step script workflow for tests.
        steps:
          - name: run
            skills:
              - {_SCRIPT_SKILL}
            assignee: agent
        ---

        ## run

        Script step. Runs `{_SCRIPT_SKILL}`.
        """,
    )


def _write_recurring_script(
    company: Path,
    name: str,
    *,
    schedule: str,
    title: str,
    extra: str = "",
) -> None:
    """Write a recurring SCRIPT template: the seeded script workflow's step 1
    is script-backed, so the template deduces to a script run and bypasses the
    Agent TTY gate. `extra` appends additional frontmatter lines (e.g.
    `state_keys`); each line is re-indented to the 8-space block so `dedent`
    strips uniformly."""
    if extra.strip():
        indented = "\n".join(
            "        " + line if line else line
            for line in extra.strip("\n").splitlines()
        )
        extra_block = "\n" + indented
    else:
        extra_block = ""
    _write_recurring(
        company,
        name,
        f"""
        ---
        schedule: "{schedule}"
        title: "{title}"
        workflow: {_SCRIPT_WORKFLOW}
        assignee: claude
        owner: marc{extra_block}
        ---

        ## Description

        Run {name}.
        """,
    )


def _seed_period_task_context(company: Path) -> None:
    """Seed the prerequisites the creator needs for a period task:
    the auto-attached `coga/period-task` context and the `direct/body`
    workflow (frozen onto workflow-less templates).

    The creator appends `coga/period-task` to every period task's
    `contexts:`, so the test repo needs a resolvable context file or
    `create_task` rejects the unknown ref.
    """
    _write(
        company / "contexts" / "coga" / "period-task" / "SKILL.md",
        """
        ---
        name: coga/period-task
        description: stub
        ---

        # Period task
        """,
    )
    _seed_direct_body_workflow(company)


def _allow_interactive_recurring(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "coga.recurring_runner._interactive_stdio_has_tty", lambda: True
    )


def _patch_recurring_command_launch(
    monkeypatch: pytest.MonkeyPatch,
    repo: Path,
    child_launch,
) -> None:
    """Run the bootstrap scan target in-process, but delegate child launches.

    The real command now launches `bootstrap/recurring-scan`, whose script
    would otherwise run in a subprocess and lose test monkeypatches for time,
    TTY state, Slack, and child launch behavior.
    """

    def fake_launch(task: str, **kwargs):  # type: ignore[no-untyped-def]
        if task == "bootstrap/recurring-scan":
            return recurring_cmd.run_recurring_scan(
                load_config(repo),
                force=os.environ.get("COGA_RECURRING_FORCE") == "1",
                interactive=os.environ.get("COGA_RECURRING_INTERACTIVE") == "1",
                agent_override=os.environ.get("COGA_RECURRING_AGENT") or None,
            )
        return child_launch(task, **kwargs)

    monkeypatch.setattr("coga.commands.launch.launch", fake_launch)


def _finish_period_task(coga_os: Path, slug: str) -> None:
    ticket_path = coga_os / "tasks" / slug / "ticket.md"
    ticket = Ticket.read(ticket_path)
    ticket.frontmatter["status"] = "done"
    ticket.write(ticket_path)
    coga_git.sync_task_state(
        load_config(coga_os), ticket_path.parent, message=f"Ticket: {slug} — done"
    )


@pytest.fixture
def repo(tmp_path: Path):
    company = tmp_path / "coga"
    _write(
        company / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')
    _seed_period_task_context(company)
    _write_recurring(
        company,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly deliverability check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the full deliverability diagnostic suite.
        """,
    )
    return company


# --- coga recurring list: the read-only schedule view ------------------------


def test_bare_recurring_head_launches_bootstrap_scan_with_env(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, dict, str | None, str | None, str | None]] = []

    def fake_launch(task: str, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(
            (
                task,
                kwargs,
                os.environ.get("COGA_RECURRING_FORCE"),
                os.environ.get("COGA_RECURRING_INTERACTIVE"),
                os.environ.get("COGA_RECURRING_AGENT"),
            )
        )

    monkeypatch.chdir(repo)
    monkeypatch.setattr("coga.commands.launch.launch", fake_launch)

    result = CliRunner().invoke(
        app, ["recurring", "--force", "--interactive", "--agent", "claude"]
    )

    assert result.exit_code == 0, result.output
    assert calls == [
        (
            "bootstrap/recurring-scan",
            {
                "agent_override": None,
                "prompt_report": False,
                "idle_timeout": None,
                "max_session": None,
                "return_timeout": False,
            },
            "1",
            "1",
            "claude",
        )
    ]
    assert os.environ.get("COGA_RECURRING_FORCE") is None
    assert os.environ.get("COGA_RECURRING_INTERACTIVE") is None
    assert os.environ.get("COGA_RECURRING_AGENT") is None


def test_recurring_all_runs_each_discovered_repo_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "workspaces"
    first = root / "alpha" / "coga"
    second = root / "teams" / "beta" / "coga"
    ignored = root / "node_modules" / "fixture" / "coga"
    excluded = root / "_scratch" / "throwaway" / "coga"
    nested_fixture = first.parent / "example" / "coga"
    for coga_os in (first, second, ignored, excluded, nested_fixture):
        _write(coga_os / "coga.toml", "version = 1\n")
    for coga_os in (first, second):
        _write(coga_os / "coga.local.toml", 'user = "marc"\n')

    calls: list[tuple[Path, bool, bool, str | None]] = []

    def fake_run(
        coga_os: Path,
        *,
        force: bool,
        interactive: bool,
        agent_override: str | None,
    ) -> int:
        calls.append((coga_os, force, interactive, agent_override))
        return 0

    monkeypatch.setattr(recurring_cmd, "_run_repo_recurring", fake_run)

    result = CliRunner().invoke(
        app,
        [
            "recurring",
            "--all",
            str(root),
            "--force",
            "--interactive",
            "--agent",
            "codex",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls == [
        (first, True, True, "codex"),
        (second, True, True, "codex"),
    ]
    assert "Found 2 Coga repo(s)" in result.output
    assert "Swept 2 of 2 Coga repo(s)." in result.output


def test_recurring_all_skips_unconfigured_repos_compactly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "workspaces"
    missing_user = root / "missing-user" / "coga"
    stale_config = root / "stale-config" / "coga"
    alias_collision = root / "alias-collision" / "coga"
    unknown_alias_target = root / "unknown-alias-target" / "coga"
    configured = root / "configured" / "coga"
    _write(missing_user / "coga.toml", "version = 1\n")
    _write(
        stale_config / "coga.toml",
        """
        version = 1
        [megalaunch]
        max_tasks = 10
        """,
    )
    _write(
        alias_collision / "coga.toml",
        """
        version = 1
        [aliases]
        launch = "status"
        """,
    )
    _write(
        unknown_alias_target / "coga.toml",
        """
        version = 1
        [aliases]
        custom = "not-a-command"
        """,
    )
    for coga_os in (alias_collision, unknown_alias_target):
        _write(coga_os / "coga.local.toml", 'user = "marc"\n')
    _write(configured / "coga.toml", "version = 1\n")
    _write(configured / "coga.local.toml", 'user = "marc"\n')
    seen: list[Path] = []

    monkeypatch.setattr(
        recurring_cmd,
        "_run_repo_recurring",
        lambda coga_os, **kwargs: seen.append(coga_os) or 0,
    )

    result = CliRunner().invoke(app, ["recurring", "--all", str(root)])

    assert result.exit_code == 0, result.output
    assert seen == [configured]
    assert "Swept 1 of 5 Coga repo(s)." in result.output
    assert "Skipped 4 unconfigured repos." in result.output
    assert "recurring exited" not in result.output


def test_recurring_all_services_one_checkout_per_remote(
    git_repo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Two checkouts of one remote produce one sweep and one period run."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _seed_template_blackboard(coga_os, "weekly-check", "state\n")
    _seed_global_log(git_repo)
    git_repo.git("add", "coga/contexts", "coga/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    scan_root = tmp_path / "workspaces"
    checkouts: list[Path] = []
    for name in ("alpha", "beta"):
        checkout = scan_root / name
        git_repo.git("clone", str(git_repo.origin), str(checkout))
        git_repo.git("checkout", "-B", "main", "origin/main", cwd=checkout)
        git_repo.git("config", "user.email", "test@example.com", cwd=checkout)
        git_repo.git("config", "user.name", "Coga Test", cwd=checkout)
        git_repo.git("config", "commit.gpgsign", "false", cwd=checkout)
        (checkout / "coga" / "coga.local.toml").write_text('user = "marc"\n')
        if name == "alpha":
            git_repo.git("checkout", "-b", "feature", cwd=checkout)
        checkouts.append(checkout)

    sweeps: list[Path] = []
    launches: list[tuple[Path, str]] = []
    active_checkout: list[Path] = []

    def fake_launch(task: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        coga_root = active_checkout[-1]
        launches.append((coga_root, task))
        _finish_period_task(coga_root, task)

    def run_in_process(
        found: Path,
        *,
        force: bool,
        interactive: bool,
        agent_override: str | None,
    ) -> int:
        sweeps.append(found)
        active_checkout.append(found)
        try:
            return recurring_cmd.run_recurring_scan(
                load_config(found),
                force=force,
                interactive=interactive,
                agent_override=agent_override,
                require_fresh_control=True,
            )
        finally:
            active_checkout.pop()

    _allow_interactive_recurring(monkeypatch)
    _freeze_recurring_now(monkeypatch, datetime(2026, 6, 8, 10, 0))
    monkeypatch.setattr("coga.commands.launch.launch", fake_launch)
    monkeypatch.setattr(recurring_cmd, "_run_repo_recurring", run_in_process)

    assert recurring_cmd.run_recurring_all_repos(scan_root) == 0

    assert sweeps == [checkouts[1] / "coga"]
    assert launches == [(checkouts[1] / "coga", "recurring/weekly-check")]
    assert git_repo.origin_tracks("coga/tasks/recurring/weekly-check/ticket.md")
    for checkout in checkouts:
        git_repo.git("fetch", "origin", "main", cwd=checkout)
        ahead, _behind = git_repo.git(
            "rev-list", "--left-right", "--count", "HEAD...origin/main", cwd=checkout
        ).split()
        assert ahead == "0"

    captured = capsys.readouterr()
    assert "alpha — same git remote as beta; skipped duplicate checkout" in captured.err


def test_recurring_all_keeps_distinct_workspaces_in_one_remote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sibling Coga workspaces in one monorepo are not duplicate checkouts."""
    root = tmp_path / "monorepo"
    first = root / "service-a" / "coga"
    second = root / "service-b" / "coga"
    for coga_os in (first, second):
        _write(coga_os / "coga.toml", "version = 1\n")

    monkeypatch.setattr(recurring_cmd, "_git_toplevel", lambda _path: root)
    monkeypatch.setattr(recurring_cmd, "_current_branch", lambda _root: "main")

    def fake_subprocess_run(command, **kwargs):  # type: ignore[no-untyped-def]
        assert command[-3:] == ["remote", "get-url", "origin"]
        return SimpleNamespace(returncode=0, stdout="https://example.com/team/repo\n")

    monkeypatch.setattr(recurring_cmd.subprocess, "run", fake_subprocess_run)

    assert recurring_cmd._duplicate_remote_checkouts([first, second]) == {}


def test_recurring_all_prefers_configured_duplicate_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing local user cannot shadow a runnable clone of the workspace."""
    root = tmp_path / "workspaces"
    first = root / "alpha" / "coga"
    second = root / "beta" / "coga"
    for coga_os in (first, second):
        _write(coga_os / "coga.toml", "version = 1\n")
    _write(second / "coga.local.toml", 'user = "marc"\n')

    monkeypatch.setattr(
        recurring_cmd, "_git_toplevel", lambda coga_os: coga_os.parent
    )
    monkeypatch.setattr(recurring_cmd, "_current_branch", lambda _root: "main")

    def fake_subprocess_run(command, **kwargs):  # type: ignore[no-untyped-def]
        assert command[-3:] == ["remote", "get-url", "origin"]
        return SimpleNamespace(returncode=0, stdout="https://example.com/team/repo\n")

    monkeypatch.setattr(recurring_cmd.subprocess, "run", fake_subprocess_run)

    assert recurring_cmd._duplicate_remote_checkouts([first, second]) == {
        first: second
    }


def test_recurring_all_isolates_malformed_config_during_remote_grouping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "workspaces"
    first = root / "alpha" / "coga"
    second = root / "beta" / "coga"
    _write(first / "coga.toml", "version = [\n")
    _write(second / "coga.toml", "version = 1\n")
    _write(second / "coga.local.toml", 'user = "marc"\n')
    seen: list[Path] = []

    def fake_run(coga_os: Path, **kwargs) -> int:  # type: ignore[no-untyped-def]
        seen.append(coga_os)
        return 2 if coga_os == first else 0

    monkeypatch.setattr(recurring_cmd, "_run_repo_recurring", fake_run)

    assert recurring_cmd.run_recurring_all_repos(root) == 1
    assert seen == [first, second]


def test_recurring_all_continues_after_repo_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "workspaces"
    first = root / "alpha" / "coga"
    second = root / "beta" / "coga"
    for coga_os in (first, second):
        _write(coga_os / "coga.toml", "version = 1\n")
        _write(coga_os / "coga.local.toml", 'user = "marc"\n')

    seen: list[Path] = []

    def fake_run(coga_os: Path, **kwargs) -> int:  # type: ignore[no-untyped-def]
        seen.append(coga_os)
        return 7 if coga_os == first else 0

    monkeypatch.setattr(recurring_cmd, "_run_repo_recurring", fake_run)

    result = CliRunner().invoke(app, ["recurring", "--all", str(root)])

    assert result.exit_code == 1
    assert seen == [first, second]
    assert "Swept 1 of 2 Coga repo(s)." in result.output
    assert "alpha — recurring exited 7" in result.output


def test_recurring_all_accepts_coga_workspace_as_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    coga_os = tmp_path / "project" / "coga"
    _write(coga_os / "coga.toml", "version = 1\n")
    _write(coga_os / "coga.local.toml", 'user = "marc"\n')
    seen: list[Path] = []
    monkeypatch.setattr(
        recurring_cmd,
        "_run_repo_recurring",
        lambda found, **kwargs: seen.append(found) or 0,
    )

    result = CliRunner().invoke(app, ["recurring", "--all", str(coga_os)])

    assert result.exit_code == 0, result.output
    assert seen == [coga_os]


def test_recurring_all_fails_loud_when_no_repos_exist(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["recurring", "--all", str(tmp_path)])

    assert result.exit_code == 1
    assert "No Coga repos found" in result.output


def test_recurring_sweep_flags_are_rejected_for_subcommands(repo: Path) -> None:
    result = CliRunner().invoke(app, ["recurring", "--force", "list"])

    assert result.exit_code == 2
    assert "apply to recurring sweeps" in result.output


def test_repo_recurring_dispatch_uses_current_python_and_clears_scan_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    coga_os = tmp_path / "project" / "coga"
    _write(coga_os / "coga.toml", "version = 1\n")
    monkeypatch.setenv("COGA_RECURRING_FORCE", "stale")
    captured: dict[str, object] = {}

    def fake_subprocess_run(command, **kwargs):  # type: ignore[no-untyped-def]
        captured["command"] = command
        captured.update(kwargs)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(recurring_cmd.subprocess, "run", fake_subprocess_run)

    code = recurring_cmd._run_repo_recurring(
        coga_os,
        force=True,
        interactive=True,
        agent_override="codex",
    )

    assert code == 0
    assert captured["command"] == [
        recurring_cmd.sys.executable,
        "-m",
        "coga.cli",
        "recurring",
        "--force",
        "--interactive",
        "--agent",
        "codex",
    ]
    assert captured["cwd"] == coga_os.parent
    assert captured["check"] is False
    assert "COGA_RECURRING_FORCE" not in captured["env"]
    assert captured["env"]["COGA_RECURRING_REQUIRE_FRESH_CONTROL"] == "1"


def test_recurring_list_is_read_only_and_shows_schedule(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    monkeypatch.setenv("COLUMNS", "200")  # avoid Rich truncating the cells
    result = CliRunner().invoke(app, ["recurring", "list"])
    assert result.exit_code == 0, result.output
    assert "weekly-check" in result.output
    assert "0 9 * * 1" in result.output  # the schedule cron
    # Listing creates nothing — a view never mutates (principle 6).
    assert list_tasks(load_config(repo)) == []


def test_recurring_list_shows_picked_tasks(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(repo)
    fixed_now = datetime(2026, 4, 22, 10, 0, 0)  # a Wednesday after Monday 9am
    scan_due(cfg, now=fixed_now)  # instantiate this period's task
    monkeypatch.chdir(repo)
    monkeypatch.setenv("COLUMNS", "200")
    result = CliRunner().invoke(app, ["recurring", "list"])
    assert result.exit_code == 0, result.output
    assert "Picked tasks" in result.output
    assert "recurring/weekly-check" in result.output


def test_recurring_list_reports_prior_period_done_task_as_due(repo: Path) -> None:
    """A stale stable-path task must not masquerade as this period's run."""
    cfg = load_config(repo)
    week_17 = datetime(2026, 4, 22, 10, 0, 0)
    first = scan_due(cfg, now=week_17)
    ticket = Ticket.read(first.tasks[0].ref.ticket_path)
    ticket.frontmatter["status"] = "done"
    ticket.frontmatter.pop("step", None)
    ticket.write(first.tasks[0].ref.ticket_path)

    current = list_templates(cfg, now=week_17)[0]
    assert current.instance == first.tasks[0].ref
    assert current.instance_status == "done"
    assert current.stale_done is False
    assert current.due is False

    next_period = list_templates(
        cfg, now=datetime(2026, 4, 29, 10, 0, 0)
    )[0]
    assert next_period.instance == first.tasks[0].ref
    assert next_period.instance_status == "done"
    assert next_period.stale_done is True
    assert next_period.due is True
    # The read-only view does not perform the replacement itself.
    assert Ticket.read(first.tasks[0].ref.ticket_path).status == "done"
    assert read_last_serviced_period(
        repo / "recurring" / "weekly-check" / "ticket.md"
    ) == "2026-W17"


def test_recurring_list_reports_reaped_serviced_period_as_ran(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A serviced period whose task dir Dream reaped is not due.

    The sweep skips it as "ran this period" (the template blackboard's
    high-water mark covers the firing); `list` must agree instead of
    showing "due — not created"."""
    cfg = load_config(repo)
    week_17 = datetime(2026, 4, 22, 10, 0, 0)
    scan = scan_due(cfg, now=week_17)
    shutil.rmtree(scan.tasks[0].ref.path)  # Dream reaped the finished run

    current = list_templates(cfg, now=week_17)[0]
    assert current.instance is None
    assert current.serviced is True
    assert current.due is False

    # The next period is genuinely due again.
    next_period = list_templates(cfg, now=datetime(2026, 4, 29, 10, 0, 0))[0]
    assert next_period.serviced is False
    assert next_period.due is True

    monkeypatch.chdir(repo)
    monkeypatch.setenv("COLUMNS", "200")
    _freeze_recurring_now(monkeypatch, week_17)
    result = CliRunner().invoke(app, ["recurring", "list"])
    assert result.exit_code == 0, result.output
    assert "ran this period — task reaped" in result.output
    assert "due — not created" not in result.output


# --- scan_due: the bare `coga recurring` library layer -----------------------


def test_scan_due_creates_task(repo: Path) -> None:
    cfg = load_config(repo)
    fixed_now = datetime(2026, 4, 22, 10, 0, 0)  # a Wednesday after Monday 9am
    scan = scan_due(cfg, now=fixed_now)
    assert scan.errors == []
    assert len(scan.tasks) == 1
    task = scan.tasks[0]
    assert task.created is True
    assert task.launchable is True  # creates straight to `active`
    assert task in scan.due

    ticket = Ticket.read(task.ref.path / "ticket.md")
    assert ticket.title == "Weekly deliverability check"
    assert "mode" not in ticket.frontmatter
    assert ticket.owner == "marc"
    assert task.ref.directory == "recurring"
    assert task.ref.slug == "weekly-check"
    assert task.ref.id_slug == "recurring/weekly-check"
    assert task.ref.path == repo / "tasks" / "recurring" / "weekly-check"
    assert read_last_serviced_period(
        repo / "recurring" / "weekly-check" / "ticket.md"
    ) == "2026-W17"
    body = (task.ref.path / "ticket.md").read_text()
    assert "Run the full deliverability diagnostic suite" in body


def test_create_auto_attaches_period_task_context(repo: Path) -> None:
    """Every period task gets `coga/period-task` appended to its contexts.

    The recurring template above declares no contexts; after creating, the
    period task should carry exactly `["coga/period-task"]`. This is what
    teaches the launched run that persistent state lives in the parent
    recurring task's blackboard, not the per-period one.
    """
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    ticket = Ticket.read(scan.tasks[0].ref.path / "ticket.md")
    assert ticket.contexts == ["coga/period-task"]


def test_create_does_not_duplicate_explicit_period_task_context(
    repo: Path,
) -> None:
    """A recurring task that already lists `coga/period-task` doesn't get
    it appended again — the append is idempotent."""
    _write_recurring(
        repo,
        "explicit-period",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Already lists period-task"
        assignee: claude
        owner: marc
        contexts:
          - coga/period-task
        ---

        ## Description

        Body.
        """,
    )
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    task = next(t for t in scan.tasks if t.template == "explicit-period")
    ticket = Ticket.read(task.ref.path / "ticket.md")
    assert ticket.contexts == ["coga/period-task"]


def test_create_preserves_non_description_template_sections(repo: Path) -> None:
    """Template sections beyond `## Description` survive into the period task.

    Regression: the creator used to keep only the `## Description` slice, so
    a template's `## Script config` (which sets a script step's mode/sync) was
    dropped and scheduled runs silently fell back to the default mode. The full
    template body must be carried verbatim, with a `## Context` appended.
    """
    _write_recurring(
        repo,
        "script-config-template",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Has script config"
        assignee: claude
        owner: marc
        state_keys:
        - cursor
        ---

        ## Description

        Verify daily that every row has an alert.

        ## Script config

        ```yaml
        mode: watchdog
        ```

        ## Output

        Writes one JSON summary to stdout.
        """,
    )
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    task = next(t for t in scan.tasks if t.template == "script-config-template")
    body = (task.ref.path / "ticket.md").read_text()
    assert "## Script config" in body
    assert "mode: watchdog" in body
    assert "## Output" in body
    # The canonical `## Context` section is still appended for body uniformity.
    assert "## Context" in body


def test_create_preserves_recurring_template_secrets(repo: Path) -> None:
    _write_recurring(
        repo,
        "locked-down",
        """
        ---
        title: "Locked down"
        schedule: "0 9 * * 1"
        secrets: []
        ---

        ## Description

        No secrets for this recurring run.
        """,
    )

    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 27, 9, 0), allow_interactive=True)
    task = next(t for t in scan.tasks if t.template == "locked-down")
    ticket = Ticket.read(task.ref.path / "ticket.md")
    assert ticket.secrets == []


def test_scan_due_idempotent(repo: Path) -> None:
    cfg = load_config(repo)
    now = datetime(2026, 4, 22, 10, 0, 0)
    first = scan_due(cfg, now=now)
    second = scan_due(cfg, now=now)
    assert first.tasks[0].created is True
    # Same period: the task already exists, so it is found, not recreated.
    assert second.tasks[0].created is False
    assert len(list_tasks(cfg)) == 1


def test_scan_due_different_period_creates_new(repo: Path) -> None:
    cfg = load_config(repo)
    first = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))  # week 17
    ticket = Ticket.read(first.tasks[0].ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(first.tasks[0].ref.path / "ticket.md")
    shutil.rmtree(first.tasks[0].ref.path)

    scan = scan_due(cfg, now=datetime(2026, 4, 29, 10, 0, 0))  # week 18
    assert scan.tasks[0].created is True
    assert scan.tasks[0].ref.id_slug == "recurring/weekly-check"
    assert read_last_serviced_period(
        repo / "recurring" / "weekly-check" / "ticket.md"
    ) == "2026-W18"
    assert len(list_tasks(cfg)) == 1


def test_scan_due_replaces_prior_period_done_task(repo: Path) -> None:
    """A stale done task is deleted before a fresh current-period task."""
    _write_recurring(
        repo,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly deliverability check"
        assignee: claude
        owner: marc
        state_keys:
        - cursor
        ---

        ## Description

        Run the full deliverability diagnostic suite.
        """,
    )
    _seed_template_blackboard(repo, "weekly-check", "cursor: old\n")
    cfg = load_config(repo)
    first = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    ref = first.tasks[0].ref
    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter["status"] = "done"
    ticket.write(ref.ticket_path)
    replace_blackboard(ref.ticket_path, "\nold run residue\n")
    _seed_template_blackboard(
        repo,
        "weekly-check",
        "cursor: new\n\nlast_serviced_period: 2026-W17\n",
    )

    scan = scan_due(cfg, now=datetime(2026, 4, 29, 10, 0, 0))

    assert scan.errors == []
    assert len(scan.tasks) == 1
    replacement = scan.tasks[0]
    assert replacement.ref == ref
    assert replacement.created is True
    assert replacement.replaced_done is True
    assert replacement.launchable is True
    assert replacement in scan.due
    ticket = Ticket.read(ref.ticket_path)
    assert ticket.status == "active"
    assert ticket.step == "1 (execute)"
    assert "old run residue" not in read_blackboard(ref.ticket_path)
    assert '"cursor": "new"' in (ref.path / ".state-snapshot.json").read_text()
    assert read_last_serviced_period(
        repo / "recurring" / "weekly-check" / "ticket.md"
    ) == "2026-W18"
    log = "\n".join(task_log_lines(cfg, "recurring/weekly-check"))
    assert "deleted completed prior-period task before 2026-W18" in log
    assert "created recurring/weekly-check for 2026-W18" in log
    assert len(list_tasks(cfg)) == 1


def test_scan_due_keeps_current_period_done_task_finished(repo: Path) -> None:
    cfg = load_config(repo)
    now = datetime(2026, 4, 22, 10, 0, 0)
    first = scan_due(cfg, now=now)
    ticket = Ticket.read(first.tasks[0].ref.ticket_path)
    ticket.frontmatter["status"] = "done"
    ticket.frontmatter.pop("step", None)
    ticket.write(first.tasks[0].ref.ticket_path)

    scan = scan_due(cfg, now=now)

    assert scan.tasks[0].status == "done"
    assert scan.tasks[0].replaced_done is False
    assert scan.due == []


def test_scan_due_keeps_prior_period_paused_task_parked(repo: Path) -> None:
    cfg = load_config(repo)
    first = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    ticket = Ticket.read(first.tasks[0].ref.ticket_path)
    ticket.frontmatter["status"] = "paused"
    ticket.write(first.tasks[0].ref.ticket_path)

    scan = scan_due(cfg, now=datetime(2026, 4, 29, 10, 0, 0))

    assert scan.tasks[0].status == "paused"
    assert scan.tasks[0].replaced_done is False
    assert scan.due == []
    assert read_last_serviced_period(
        repo / "recurring" / "weekly-check" / "ticket.md"
    ) == "2026-W17"


def test_recurring_scan_launches_replacement_task(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The runner syncs and launches the fresh replacement task."""
    cfg = load_config(repo)
    first = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    ticket = Ticket.read(first.tasks[0].ref.ticket_path)
    ticket.frontmatter["status"] = "done"
    ticket.frontmatter.pop("step", None)
    ticket.write(first.tasks[0].ref.ticket_path)
    launched: list[str] = []

    def fake_launch(slug: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        launched.append(slug)
        finished = Ticket.read(first.tasks[0].ref.ticket_path)
        finished.frontmatter["status"] = "done"
        finished.frontmatter.pop("step", None)
        finished.write(first.tasks[0].ref.ticket_path)

    _allow_interactive_recurring(monkeypatch)
    _freeze_recurring_now(monkeypatch, datetime(2026, 4, 29, 10, 0, 0))
    monkeypatch.setattr("coga.commands.launch.launch", fake_launch)

    assert recurring_cmd.run_recurring_scan(cfg) == 0

    assert launched == ["recurring/weekly-check"]
    assert "Replaced completed recurring/weekly-check" in capsys.readouterr().out
    assert read_last_serviced_period(
        repo / "recurring" / "weekly-check" / "ticket.md"
    ) == "2026-W18"


def test_recurring_scan_launches_even_when_create_sync_crashes(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A non-GitError sync crash must not strand created tasks unlaunched.

    The pre-launch control-branch sync sits between task creation and the
    launch loop; if it aborts the sweep, the period tasks are left `active`
    at step 1 with nothing in the log — created but never run.
    """
    cfg = load_config(repo)
    launched: list[str] = []

    def fake_launch(slug: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        launched.append(slug)
        ticket_path = repo / "tasks" / "recurring" / "weekly-check" / "ticket.md"
        finished = Ticket.read(ticket_path)
        finished.frontmatter["status"] = "done"
        finished.frontmatter.pop("step", None)
        finished.write(ticket_path)

    def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise subprocess.CalledProcessError(128, ["git", "push"])

    _allow_interactive_recurring(monkeypatch)
    _freeze_recurring_now(monkeypatch, datetime(2026, 4, 22, 10, 0, 0))
    monkeypatch.setattr("coga.commands.launch.launch", fake_launch)
    monkeypatch.setattr(recurring_cmd, "_sync_recurring_create_paths", boom)

    assert recurring_cmd.run_recurring_scan(cfg) == 0

    assert launched == ["recurring/weekly-check"]
    captured = capsys.readouterr()
    assert "Created recurring/weekly-check" in captured.out
    assert "[git] sync failed" in captured.err


def test_sync_recurring_create_survives_non_git_error(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unexpected sync failures degrade like GitError: report, keep launchable."""
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    ref = scan.tasks[0].ref
    template_ticket = repo / "recurring" / "weekly-check" / "ticket.md"
    before = template_ticket.read_text()

    def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise subprocess.CalledProcessError(128, ["git", "push"])

    monkeypatch.setattr(recurring_cmd, "_sync_recurring_create_paths", boom)

    created = recurring_cmd._sync_recurring_create(cfg, "weekly-check", ref)

    assert created is True
    assert "[git] sync failed" in capsys.readouterr().err
    assert template_ticket.read_text() == before  # restored, not corrupted


def test_scan_due_resumes_stuck_prior_run_instead_of_new_period(
    repo: Path,
) -> None:
    """A stuck prior-period `in_progress` run is resumed, deferring the new period.

    One live task per template: identity is the `recurring/` directory plus
    the template leaf slug, so a stale orphan is found and resumed (`created=False`)
    rather than a fresh current-period task created alongside it.
    """
    cfg = load_config(repo)
    first = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))  # week 17
    ref = first.tasks[0].ref
    ticket = Ticket.read(ref.path / "ticket.md")
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(ref.path / "ticket.md")

    scan = scan_due(cfg, now=datetime(2026, 4, 29, 10, 0, 0))  # week 18

    assert scan.errors == []
    assert len(scan.tasks) == 1
    resumed = scan.tasks[0]
    # The stale orphan is resumed, not superseded by another task dir.
    assert resumed.created is False
    assert resumed.launchable is True
    assert resumed.resuming is True
    assert resumed.ref.id_slug == ref.id_slug
    assert resumed.ref.id_slug == "recurring/weekly-check"
    # The resumed prior-period run still owns week 17. Week 18 is not marked
    # serviced until the stale run is gone and a new run is created.
    assert read_last_serviced_period(
        repo / "recurring" / "weekly-check" / "ticket.md"
    ) == "2026-W17"
    # Only the stuck run exists — no duplicate create.
    assert {r.id_slug for r in list_tasks(cfg)} == {"recurring/weekly-check"}

    ticket.frontmatter["status"] = "done"
    ticket.write(ref.path / "ticket.md")
    shutil.rmtree(ref.path)
    next_scan = scan_due(cfg, now=datetime(2026, 4, 29, 10, 0, 0))
    assert next_scan.tasks[0].created is True
    assert read_last_serviced_period(
        repo / "recurring" / "weekly-check" / "ticket.md"
    ) == "2026-W18"


def test_scan_due_does_not_recreate_after_period_task_deleted(
    repo: Path,
) -> None:
    """A completed-this-period task that has been deleted stays completed.

    A later Dream retro pass deletes done recurring period tickets; a human
    `coga delete` is the other case. The recurring template's blackboard
    carries the `last_serviced_period` high-water mark, so a successful run
    isn't silently re-launched by the next `coga recurring`.
    """
    cfg = load_config(repo)
    now = datetime(2026, 4, 22, 10, 0, 0)  # a Wednesday after Monday 9am

    first = scan_due(cfg, now=now)
    assert first.tasks[0].created is True
    ref = first.tasks[0].ref

    # The load-bearing period state lands in the template ticket's blackboard
    # region; the repo-global log keeps the append-only period history, tagged
    # `recurring/<name>`.
    log = "\n".join(task_log_lines(cfg, "recurring/weekly-check"))
    bb_path = repo / "recurring" / "weekly-check" / "ticket.md"
    assert "created recurring/weekly-check for 2026-W17" in log
    assert read_last_serviced_period(bb_path) == "2026-W17"

    # Simulate the run completing and later being deleted by Dream or a human.
    shutil.rmtree(ref.path)

    second = scan_due(cfg, now=now)
    assert second.errors == []
    assert len(second.tasks) == 1
    completed = second.tasks[0]
    assert completed.created is False
    assert completed.launchable is False
    assert completed.ref is None
    assert second.due == []
    # The directory stays gone — no re-create.
    assert list_tasks(cfg) == []


def test_due_orders_dream_last(repo: Path) -> None:
    """A bare sweep launches the cleanup template (Dream) after every other
    due template, so Dream's retro pass reaps this sweep's freshly-`done`
    period tickets instead of trailing them by a full sweep.

    Alphabetically `dream` sorts between `digest` and `weekly-summary`; the
    layered `due` key (`is_cleanup` leading) overrides that so it lands last.
    """
    # Three due weekly templates whose names bracket `dream` alphabetically.
    for name in ("digest", "dream", "weekly-summary"):
        _write_recurring(
            repo,
            name,
            f"""
            ---
            schedule: "0 9 * * 1"
            title: "{name}"
            assignee: claude
            owner: marc
            ---

            ## Description

            Run {name}.
            """,
        )

    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))  # Wed after Mon 9am

    order = [t.template for t in scan.due]
    assert order[-1] == "dream"
    assert set(order) == {"digest", "dream", "weekly-summary", "weekly-check"}


def test_due_resuming_orphan_runs_before_fresh_dream(repo: Path) -> None:
    """Dream-last leads the sort key, but resume-first still holds *among the
    non-cleanup templates*: a stuck `in_progress` orphan is picked up before a
    fresh Dream launch."""
    for name in ("digest", "dream"):
        _write_recurring(
            repo,
            name,
            f"""
            ---
            schedule: "0 9 * * 1"
            title: "{name}"
            assignee: claude
            owner: marc
            ---

            ## Description

            Run {name}.
            """,
        )

    cfg = load_config(repo)
    first = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))  # week 17
    # Strand the digest period task as a dead-sweep orphan.
    digest_ref = next(t.ref for t in first.tasks if t.template == "digest")
    ticket = Ticket.read(digest_ref.path / "ticket.md")
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(digest_ref.path / "ticket.md")

    scan = scan_due(cfg, now=datetime(2026, 4, 29, 10, 0, 0))  # week 18
    order = [t.template for t in scan.due]
    # Resumed digest orphan first; Dream still last.
    assert order[0] == "digest"
    assert order[-1] == "dream"


def test_scan_due_recognizes_blackboard_high_water(repo: Path) -> None:
    """A period recorded in `last_serviced_period` is honored."""
    now = datetime(2026, 4, 22, 10, 0, 0)  # week 17
    _seed_template_blackboard(
        repo, "weekly-check", "### State\n\nlast_serviced_period: 2026-W17\n"
    )

    cfg = load_config(repo)
    scan = scan_due(cfg, now=now)
    assert scan.errors == []
    assert len(scan.tasks) == 1
    assert scan.tasks[0].created is False  # recognized as already handled
    assert scan.due == []
    assert list_tasks(cfg) == []  # not re-created


def test_scan_due_skips_bad_template(repo: Path, capsys) -> None:
    _write(repo / "recurring" / "bad" / "ticket.md", "no frontmatter here\n")
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    assert len(scan.tasks) == 1  # good one still created
    assert len(scan.errors) == 1
    assert scan.errors[0][0] == "bad"
    assert "skipping bad" in capsys.readouterr().err


def test_scan_due_explains_removed_megalaunch_skill(repo: Path) -> None:
    _write(
        repo / "workflows" / "megalaunch.md",
        """
        ---
        name: megalaunch
        description: Legacy recurring megalaunch workflow.
        steps:
          - name: run
            skills:
              - coga/megalaunch/run
        ---
        """,
    )
    _write_recurring(
        repo,
        "megalaunch",
        """
        ---
        schedule: "0 9 * * *"
        title: "Megalaunch"
        workflow: megalaunch
        assignee: claude
        owner: marc
        ---

        ## Description

        Legacy recurring megalaunch.
        """,
    )

    scan = scan_due(
        load_config(repo), now=datetime(2026, 4, 22, 10, 0, 0)
    )

    error = next(message for name, message in scan.errors if name == "megalaunch")
    assert "megalaunch is now on-demand only" in error
    assert "`coga/recurring/megalaunch/`" in error
    assert "`coga/workflows/megalaunch/`" in error


def test_scan_due_skips_malformed_schedule(repo: Path, capsys) -> None:
    _write_recurring(
        repo,
        "bad-cron",
        """
        ---
        schedule: "not a cron"
        title: "Bad cron"
        assignee: claude
        owner: marc
        ---

        ## Description

        Bad schedule.
        """,
    )
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    assert len(scan.tasks) == 1  # the good template still creates
    assert scan.tasks[0].template == "weekly-check"
    assert len(scan.errors) == 1
    assert scan.errors[0][0] == "bad-cron"
    assert "`schedule` is not a valid cron expression" in scan.errors[0][1]
    assert "skipping bad-cron" in capsys.readouterr().err


def test_scan_due_accepts_year_scoped_schedule_for_current_year(repo: Path) -> None:
    _write_recurring(
        repo,
        "year-scoped",
        """
        ---
        schedule: "0 0 1 1 * * 2026"
        title: "Year-scoped"
        assignee: claude
        owner: marc
        ---

        ## Description

        Year-scoped schedule.
        """,
    )
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 6, 1, 10, 0, 0))
    assert scan.errors == []
    assert [task.template for task in scan.tasks] == ["weekly-check", "year-scoped"]


def test_scan_due_skips_template_missing_ticket_md(repo: Path, capsys) -> None:
    (repo / "recurring" / "missing-ticket").mkdir(parents=True)
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    assert len(scan.tasks) == 1  # the good template still creates
    assert len(scan.errors) == 1
    assert scan.errors[0] == ("missing-ticket", "missing ticket.md")
    assert "skipping missing-ticket" in capsys.readouterr().err


def test_scan_due_flags_legacy_md_file(repo: Path, capsys) -> None:
    """A leftover single-file `<name>.md` is flagged, not silently ignored."""
    _write(
        repo / "recurring" / "legacy.md",
        '---\nschedule: "0 9 * * 1"\n---\n',
    )
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    assert len(scan.tasks) == 1  # the real directory still creates
    assert scan.errors[0][0] == "legacy.md"
    assert "legacy single-file" in scan.errors[0][1]
    assert "skipping legacy.md" in capsys.readouterr().err


def test_scan_due_ignores_leftover_mode_key(repo: Path, capsys) -> None:
    """The removed `mode:` field is inert: a stale template still scans.

    Whether a run is a script or an agent session is deduced from the
    template's `script:` / workflow step 1, so a leftover `mode:` key — any
    value — neither dispatches nor fails."""
    _write_recurring(
        repo,
        "daily-auto",
        """
        ---
        schedule: "0 9 * * *"
        title: "Daily auto"
        mode: auto
        assignee: claude
        owner: marc
        ---

        ## Description

        Auto.
        """,
    )
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    assert {task.template for task in scan.tasks} == {"weekly-check", "daily-auto"}
    assert scan.errors == []


def test_scan_due_skips_interactive_template_without_tty(
    repo: Path, capsys
) -> None:
    """Unattended scans skip interactive templates before creating.

    The error lands in
    `DueScan.errors`, so `coga recurring` can post its scan-error summary and
    still continue to other due templates. A script template bypasses the TTY gate
    (it produces live output), so it still creates while the interactive one is
    skipped.
    """
    _seed_script_workflow(repo)
    _write_recurring_script(
        repo, "z-script-check", schedule="0 9 * * *", title="Script check"
    )
    cfg = load_config(repo)
    scan = scan_due(
        cfg, now=datetime(2026, 4, 22, 10, 0, 0), allow_interactive=False
    )
    assert len(scan.tasks) == 1
    assert scan.tasks[0].template == "z-script-check"
    assert len(scan.errors) == 1
    assert scan.errors[0][0] == "weekly-check"
    assert "an agent run requires a TTY" in scan.errors[0][1]
    assert "skipping weekly-check" in capsys.readouterr().err


def test_scan_due_reports_created_task_validation_failure(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A malformed recurring scaffold is retained and reported per template."""

    def reject_created_task(  # type: ignore[no-untyped-def]
        cfg, ref, *, action: str
    ) -> None:
        raise TaskValidationError(
            [
                Issue(
                    kind="broken-ref",
                    task=ref.id_slug,
                    message="generated recurring ticket is malformed",
                    severity="error",
                )
            ],
            action=action,
        )

    monkeypatch.setattr("coga.validate.assert_task_valid", reject_created_task)
    cfg = load_config(repo)

    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))

    assert scan.tasks == []
    assert scan.errors == [
        (
            "weekly-check",
            "task validation failed after create:\n"
            "[ERROR] recurring/weekly-check: broken-ref — "
            "generated recurring ticket is malformed",
        )
    ]
    assert "skipping weekly-check" in capsys.readouterr().err
    assert (repo / "tasks" / "recurring" / "weekly-check" / "ticket.md").is_file()


def test_scan_due_reports_create_value_error_per_template(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A pre-write create failure skips the template instead of crashing."""

    def reject_create(*args: object, **kwargs: object) -> None:
        raise ValueError("Unknown contexts: nonexistent/ctx")

    monkeypatch.setattr("coga.recurring.create_task", reject_create)
    cfg = load_config(repo)

    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))

    assert scan.tasks == []
    assert scan.errors == [
        ("weekly-check", "Unknown contexts: nonexistent/ctx")
    ]
    assert "skipping weekly-check" in capsys.readouterr().err


def test_scan_due_template_without_script_deduces_agent(
    repo: Path, capsys
) -> None:
    """A template with no script anywhere deduces to an agent run."""
    _write_recurring(
        repo,
        "no-mode",
        """
        ---
        schedule: "0 9 * * *"
        title: "No mode"
        assignee: claude
        owner: marc
        ---

        ## Description

        Legacy template.
        """,
    )
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    assert {task.template for task in scan.tasks} == {"weekly-check", "no-mode"}
    assert scan.errors == []


def test_template_deduction_prefers_template_script(repo: Path) -> None:
    """Pre-freeze deduction rule 1: a template's own `script:` makes it a
    script run — no workflow resolution needed — so an unattended scan keeps
    it instead of TTY-gating it."""
    _write_recurring(
        repo,
        "own-script",
        """
        ---
        schedule: "0 9 * * *"
        title: "Own script"
        script: inline
        assignee: claude
        owner: marc
        ---

        ## Description

        Own script.

        ## Script

        ```sh
        exit 0
        ```
        """,
    )
    cfg = load_config(repo)
    scan = scan_due(
        cfg, now=datetime(2026, 4, 22, 10, 0, 0), allow_interactive=False
    )
    assert "own-script" in {task.template for task in scan.tasks}
    assert all(name != "own-script" for name, _ in scan.errors)


def test_template_deduction_isolates_malformed_first_step_skill(
    repo: Path,
) -> None:
    """One malformed skill is a per-template scan error, not a sweep abort."""
    _write(
        repo / "skills" / "broken" / "run" / "SKILL.md",
        "not skill frontmatter\n",
    )
    _write(
        repo / "workflows" / "broken.md",
        """
        ---
        name: broken
        description: malformed first-step skill.
        steps:
          - name: run
            skills:
              - broken/run
        ---
        """,
    )
    _write_recurring(
        repo,
        "a-broken",
        """
        ---
        schedule: "0 9 * * *"
        title: "Broken"
        workflow: broken
        assignee: claude
        owner: marc
        ---

        ## Description

        Broken.
        """,
    )
    _seed_script_workflow(repo)
    _write_recurring_script(
        repo, "z-script-check", schedule="0 9 * * *", title="Script check"
    )

    cfg = load_config(repo)
    scan = scan_due(
        cfg, now=datetime(2026, 4, 22, 10, 0, 0), allow_interactive=False
    )

    assert "z-script-check" in {task.template for task in scan.tasks}
    broken_error = next(message for name, message in scan.errors if name == "a-broken")
    assert "step 1 skill 'broken/run' could not be loaded" in broken_error


def test_template_deduction_multi_skill_step_is_agent(repo: Path, capsys) -> None:
    """A workflow step 1 with more than one skill is not a script step — the
    same exactly-one-skill rule the live dispatch uses — so the template
    deduces to agent and the unattended scan TTY-gates it."""
    _seed_script_workflow(repo)
    _write(
        repo / "workflows" / "two-skills.md",
        f"""
        ---
        name: two-skills
        description: step 1 has two skills, so it cannot be a script step.
        steps:
          - name: run
            skills:
              - {_SCRIPT_SKILL}
              - {_SCRIPT_SKILL}
            assignee: agent
        ---
        """,
    )
    _write_recurring(
        repo,
        "two-skill-check",
        """
        ---
        schedule: "0 9 * * *"
        title: "Two-skill check"
        workflow: two-skills
        assignee: claude
        owner: marc
        ---

        ## Description

        Two skills.
        """,
    )
    cfg = load_config(repo)
    scan = scan_due(
        cfg, now=datetime(2026, 4, 22, 10, 0, 0), allow_interactive=False
    )
    errored = {name for name, _ in scan.errors}
    assert "two-skill-check" in errored


def test_template_deduction_unresolvable_workflow_is_agent(
    repo: Path, capsys
) -> None:
    """An unresolvable `workflow:` deduces to agent (the sweep TTY-gates it)
    rather than crashing the scan — create/launch fail loud on the missing
    workflow later, with better remedies."""
    _write_recurring(
        repo,
        "ghost-workflow",
        """
        ---
        schedule: "0 9 * * *"
        title: "Ghost workflow"
        workflow: does/not-exist
        assignee: claude
        owner: marc
        ---

        ## Description

        Ghost.
        """,
    )
    cfg = load_config(repo)
    scan = scan_due(
        cfg, now=datetime(2026, 4, 22, 10, 0, 0), allow_interactive=False
    )
    errored = {name for name, _ in scan.errors}
    assert "ghost-workflow" in errored
    detail = dict(scan.errors)["ghost-workflow"]
    assert "an agent run requires a TTY" in detail


def test_scan_due_skips_underscore_template(repo: Path, capsys) -> None:
    # `_template/` is a create, not a live recurring task — must be ignored
    # silently (no stderr complaint) even though its placeholder fields wouldn't
    # validate.
    _write_recurring(
        repo,
        "_template",
        """
        ---
        schedule: "0 9 * * 1"
        title: placeholder
        ---
        """,
    )
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    assert len(scan.tasks) == 1  # only the real one
    assert scan.errors == []
    assert "_template" not in capsys.readouterr().err


def test_scan_due_excludes_handled_task(repo: Path) -> None:
    """A task already past `active` is not relaunched — it drops out of `.due`."""
    cfg = load_config(repo)
    now = datetime(2026, 4, 22, 10, 0, 0)
    first = scan_due(cfg, now=now)
    task = first.tasks[0]

    # Simulate the task having been picked up / finished.
    ticket = Ticket.read(task.ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(task.ref.path / "ticket.md")

    second = scan_due(cfg, now=now)
    assert second.tasks[0].status == "done"
    assert second.tasks[0].launchable is False
    assert second.due == []


def test_scan_due_resumes_orphaned_in_progress_task(repo: Path) -> None:
    """An `in_progress` current-period task is a dead sweep's orphan — resume it.

    A sweep whose supervisor died mid-run (laptop sleep) leaves its in-flight
    period task frozen `in_progress`. There is no daemon and no concurrent
    sweep, so the next bare `coga recurring` re-includes it in `.due` and
    `coga launch` resumes it from its current step — rather than skipping it
    forever (the old behavior, which stranded the orphan).
    """
    cfg = load_config(repo)
    now = datetime(2026, 4, 22, 10, 0, 0)
    first = scan_due(cfg, now=now)
    task = first.tasks[0]

    # Simulate the supervisor dying mid-run: the task is frozen `in_progress`.
    ticket = Ticket.read(task.ref.path / "ticket.md")
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(task.ref.path / "ticket.md")

    second = scan_due(cfg, now=now)
    resumed = second.tasks[0]
    assert resumed.status == "in_progress"
    assert resumed.created is False  # get-or-create returned the existing dir
    assert resumed.launchable is True
    assert resumed.resuming is True
    assert resumed in second.due


def test_scan_due_skips_paused_task(repo: Path) -> None:
    """A `paused` period task stays skipped — a human deliberately parked it."""
    cfg = load_config(repo)
    now = datetime(2026, 4, 22, 10, 0, 0)
    first = scan_due(cfg, now=now)
    task = first.tasks[0]

    ticket = Ticket.read(task.ref.path / "ticket.md")
    ticket.frontmatter["status"] = "paused"
    ticket.write(task.ref.path / "ticket.md")

    second = scan_due(cfg, now=now)
    assert second.tasks[0].status == "paused"
    assert second.tasks[0].launchable is False
    assert second.tasks[0].resuming is False
    assert second.due == []


def test_scan_due_stale_done_replacement_respects_tty_gate(
    repo: Path, capsys
) -> None:
    """Replacing a stale done run puts an agent run in front of the sweep, so
    a TTY-less scan refuses it exactly like a fresh create — the stale run
    stays `done`, untouched."""
    cfg = load_config(repo)
    first = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))  # week 17
    ref = first.tasks[0].ref
    ticket = Ticket.read(ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(ref.path / "ticket.md")

    scan = scan_due(
        cfg, now=datetime(2026, 4, 29, 10, 0, 0), allow_interactive=False
    )
    assert scan.tasks == []
    assert len(scan.errors) == 1
    assert "an agent run requires a TTY" in scan.errors[0][1]
    assert Ticket.read(ref.path / "ticket.md").status == "done"
    assert read_last_serviced_period(
        repo / "recurring" / "weekly-check" / "ticket.md"
    ) == "2026-W17"


def test_create_named_replaces_stale_done_run(repo: Path) -> None:
    """`coga recurring launch <name>` (and the `dream` alias) replace a
    stale done run too — both entry points share `create_template`."""
    cfg = load_config(repo)
    first = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))  # week 17
    ref = first.tasks[0].ref
    ticket = Ticket.read(ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(ref.path / "ticket.md")

    outcome = create_named(cfg, "weekly-check", now=datetime(2026, 4, 29, 10, 0, 0))
    assert outcome.created is True
    assert outcome.replaced_done is True
    assert outcome.ref.id_slug == ref.id_slug
    assert Ticket.read(outcome.ref.path / "ticket.md").status == "active"
    assert read_last_serviced_period(
        repo / "recurring" / "weekly-check" / "ticket.md"
    ) == "2026-W18"


# --- coga recurring launch / the `dream` alias path --------------------------


@pytest.fixture
def dream_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repo carrying the real shipped `recurring/dream/` recurring task.

    `coga recurring launch` and a bare `coga recurring` are the two entry
    points into the same create path; these tests prove they converge.
    """
    company = tmp_path / "coga"
    _write(
        company / "coga.toml",
        """
        version = 1
        default_status = "draft"

        [slack]
        enabled = false

        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')
    _seed_period_task_context(company)
    (company / "tasks").mkdir(parents=True)
    (company / "recurring").mkdir(parents=True)
    shutil.copytree(SHIPPED_DREAM_DIR, company / "recurring" / "dream")
    monkeypatch.chdir(company)
    return company


def test_recurring_launch_creates_dream_task(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("coga.commands.launch.launch", lambda *a, **k: None)
    result = CliRunner().invoke(app, ["recurring", "launch", "dream"])

    assert result.exit_code == 0, result.output
    assert "Created recurring/dream" in result.output

    cfg = load_config(dream_repo)
    refs = list_tasks(cfg)
    assert len(refs) == 1
    assert refs[0].directory == "recurring"
    assert refs[0].slug == "dream"
    assert refs[0].id_slug == "recurring/dream"
    ticket = Ticket.read(refs[0].path / "ticket.md")
    assert ticket.title == "Dream"
    assert "mode" not in ticket.frontmatter
    # Dream's template declares no workflow, so it creates with the
    # `direct/body` workflow: it runs its body's ordered phases directly,
    # but is still a workflow-carrying, bumpable, valid active task.
    assert isinstance(ticket.workflow, dict)
    assert ticket.workflow["name"] == "direct/body"
    # The recurring template's `## Description` body composes into the ticket.
    assert "Run the Dream cleanup pass for this Coga repo." in ticket.body
    # The task path carries recurring identity; the period lives in the
    # recurring template blackboard, not the slug.
    assert refs[0].id_slug != "dream"
    assert read_last_serviced_period(
        dream_repo / "recurring" / "dream" / "ticket.md"
    ) is not None


def test_recurring_launch_syncs_period_task_and_high_water(
    git_repo, monkeypatch
) -> None:
    """The git control branch gets the task dir and period high-water together.

    Dream later deletes done recurring period tickets. That deletion is
    idempotent only if another checkout can still see the advanced
    `last_serviced_period` after the task dir is gone.
    """
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _seed_template_blackboard(coga_os, "weekly-check", "cursor: old\n")
    _seed_global_log(git_repo)
    git_repo.git("add", "coga/contexts", "coga/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    _freeze_recurring_now(monkeypatch, datetime(2026, 6, 8, 10, 0))  # Mon, 2026-W24
    monkeypatch.setattr("coga.commands.launch.launch", lambda *a, **k: None)
    result = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])

    assert result.exit_code == 0, result.output
    cfg = load_config(coga_os)
    ref = list_tasks(cfg)[0]
    # Period history now lands in the repo-global log; the high-water mark lives
    # in the template ticket's blackboard region.
    log_rel = "coga/log.md"
    template_rel = "coga/recurring/weekly-check/ticket.md"
    ticket_rel = f"coga/tasks/{ref.id_slug}/ticket.md"
    assert git_repo.origin_tracks(ticket_rel)
    assert git_repo.origin_tracks(log_rel)
    assert git_repo.origin_tracks(template_rel)
    template = git_repo.git("show", f"main:{template_rel}", cwd=git_repo.origin)
    assert "last_serviced_period: 2026-W24" in template
    ledger = git_repo.git("show", f"main:{log_rel}", cwd=git_repo.origin)
    assert f"created {ref.id_slug}" in ledger


def test_recurring_scan_catches_checkout_up_to_origin_before_scanning(
    git_repo, monkeypatch, capsys
) -> None:
    """A sweep starting behind origin fast-forwards the checkout first.

    With no templates due, nothing creates or lands — the only way the
    competing commit can reach the working tree is the pre-scan catch-up.
    """
    git_repo.push_competing_commit("notes.md", "remote note\n")
    assert not (git_repo.root / "notes.md").exists()

    cfg = load_config(git_repo.coga_os)
    assert recurring_cmd.run_recurring_scan(cfg) == 0

    assert (git_repo.root / "notes.md").is_file()
    assert "not fast-forwarded" not in capsys.readouterr().err


def test_recurring_all_scan_refuses_unconfirmed_control_freshness(
    git_repo, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """An `--all` child mutates no period state after a failed catch-up."""
    cfg = load_config(git_repo.coga_os)

    def fail_fetch(*args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        raise coga_git.GitError("simulated rebase conflict")

    monkeypatch.setattr(recurring_cmd, "_fetch_control_branch", fail_fetch)
    monkeypatch.setattr(
        recurring_cmd,
        "scan_due",
        lambda *args, **kwargs: pytest.fail("stale checkout must not be scanned"),
    )

    assert recurring_cmd.run_recurring_scan(
        cfg, require_fresh_control=True
    ) == 1
    assert list_tasks(cfg) == []
    captured = capsys.readouterr()
    assert "Recurring scan skipped" in captured.err
    assert "simulated rebase conflict" in captured.err


def test_recurring_all_scan_refuses_git_disabled_checkout(
    git_repo, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    git_repo.coga_os.joinpath("coga.local.toml").write_text(
        'user = "marc"\n[git]\nenabled = false\n'
    )
    cfg = load_config(git_repo.coga_os)
    monkeypatch.setattr(
        recurring_cmd,
        "scan_due",
        lambda *args, **kwargs: pytest.fail("git-disabled checkout must not scan"),
    )

    assert recurring_cmd.run_recurring_scan(
        cfg, require_fresh_control=True
    ) == 1
    assert "[git].enabled = false" in capsys.readouterr().err


def test_recurring_all_scan_refuses_detached_checkout(
    git_repo, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    git_repo.git("checkout", "--detach")
    cfg = load_config(git_repo.coga_os)
    monkeypatch.setattr(
        recurring_cmd,
        "scan_due",
        lambda *args, **kwargs: pytest.fail("detached checkout must not scan"),
    )

    assert recurring_cmd.run_recurring_scan(
        cfg, require_fresh_control=True
    ) == 1
    assert "detached HEAD" in capsys.readouterr().err


def test_recurring_scan_replaces_stale_done_task_on_control(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prior-period deletion and fresh creation land together on control."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Current template body.
        """,
    )
    _seed_template_blackboard(coga_os, "weekly-check", "state\n")
    _seed_global_log(git_repo)
    git_repo.git("add", "coga/contexts", "coga/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    cfg = load_config(coga_os)
    first = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0)).tasks[0]
    recurring_cmd._sync_recurring_create(cfg, "weekly-check", first.ref)
    ticket = Ticket.read(first.ref.ticket_path)
    ticket.frontmatter["status"] = "done"
    ticket.frontmatter.pop("step", None)
    ticket.write(first.ref.ticket_path)
    replace_blackboard(first.ref.ticket_path, "\nold run residue\n")
    coga_git.sync_task_state(
        cfg,
        first.ref.path,
        message="Ticket: recurring/weekly-check — done",
    )

    launched: list[str] = []

    def fake_launch(slug: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        launched.append(slug)
        landed = git_repo.git(
            "show",
            "main:coga/tasks/recurring/weekly-check/ticket.md",
            cwd=git_repo.origin,
        )
        assert "status: active" in landed
        assert "Current template body." in landed
        assert "old run residue" not in landed
        finished = Ticket.read(first.ref.ticket_path)
        finished.frontmatter["status"] = "done"
        finished.frontmatter.pop("step", None)
        finished.write(first.ref.ticket_path)

    _allow_interactive_recurring(monkeypatch)
    _freeze_recurring_now(monkeypatch, datetime(2026, 4, 29, 10, 0, 0))
    monkeypatch.setattr("coga.commands.launch.launch", fake_launch)

    assert recurring_cmd.run_recurring_scan(cfg) == 0
    assert launched == ["recurring/weekly-check"]
    control_template = git_repo.git(
        "show",
        "main:coga/recurring/weekly-check/ticket.md",
        cwd=git_repo.origin,
    )
    assert "last_serviced_period: 2026-W18" in control_template


def test_recurring_launch_lands_create_without_ff_noise(
    git_repo, monkeypatch
) -> None:
    """A create on the checked-out control branch emits no ff-merge dump.

    The landing pushes origin ahead while the checkout is still dirty with the
    create paths; the checkout is reconciled by the post-landing rebase, so no
    doomed `merge --ff-only` attempt (and no spurious stderr note) runs.
    """
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _seed_global_log(git_repo)
    git_repo.git("add", "coga/contexts", "coga/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")
    git_repo.push_competing_commit("notes.md", "remote note\n")

    _freeze_recurring_now(monkeypatch, datetime(2026, 6, 8, 10, 0))  # Mon, 2026-W24
    monkeypatch.setattr("coga.commands.launch.launch", lambda *a, **k: None)
    result = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])

    assert result.exit_code == 0, result.output
    assert "not fast-forwarded" not in result.output
    cfg = load_config(coga_os)
    ref = list_tasks(cfg)[0]
    assert git_repo.origin_tracks(f"coga/tasks/{ref.id_slug}/ticket.md")
    # The pre-create catch-up (or post-landing rebase) leaves the checkout at
    # origin's tip, competing commit included.
    assert (git_repo.root / "notes.md").is_file()


def test_recurring_launch_preserves_remote_ledger_entries_from_stale_branch(
    git_repo, monkeypatch
) -> None:
    """A stale checkout appends its create line without replacing main's log."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _seed_template_blackboard(coga_os, "weekly-check", "state\n")
    log = coga_os / "log.md"
    seed_line = (
        "2026-06-01 09:00 [recurring/weekly-check] [system] created "
        "recurring/weekly-check for 2026-W23\n"
    )
    log.write_text(seed_line)
    (coga_os / ".gitattributes").write_text("/log.md merge=union\n")
    git_repo.git("add", "coga/log.md", "coga/.gitattributes")
    git_repo.git("add", "coga/contexts", "coga/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    git_repo.checkout_branch("feature/stale")
    remote_line = (
        "2026-06-08 09:00 [recurring/weekly-check] [system] created "
        "recurring/weekly-check for 2026-W22\n"
    )
    git_repo.push_competing_commit(
        "coga/log.md",
        log.read_text() + remote_line,
    )

    monkeypatch.setattr("coga.commands.launch.launch", lambda *a, **k: None)
    result = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])

    assert result.exit_code == 0, result.output
    cfg = load_config(coga_os)
    ref = list_tasks(cfg)[0]
    # The repo-global log is union-merged across branches: the concurrent
    # remote append and this run's create line both survive on control.
    ledger = git_repo.git("show", "main:coga/log.md", cwd=git_repo.origin)
    assert remote_line in ledger
    assert f"created {ref.id_slug}" in ledger
    assert git_repo.origin_tracks(f"coga/tasks/{ref.id_slug}/ticket.md")


def test_recurring_launch_does_not_publish_feature_only_template_log(
    git_repo, monkeypatch
) -> None:
    """A feature-only recurring template does not become a malformed main dir."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    git_repo.git("add", "coga/contexts")
    git_repo.git("commit", "-m", "seed recurring context")
    git_repo.git("push", "origin", "main")

    git_repo.checkout_branch("feature/new-recurring")
    _write_recurring(
        coga_os,
        "new-weekly",
        """
        ---
        schedule: "0 9 * * 1"
        title: "New weekly"
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the new weekly check.
        """,
    )
    _seed_template_blackboard(coga_os, "new-weekly", "state\n")
    git_repo.git("add", "coga/recurring/new-weekly")
    git_repo.git("commit", "-m", "add new recurring template")

    monkeypatch.setattr("coga.commands.launch.launch", lambda *a, **k: None)
    result = CliRunner().invoke(app, ["recurring", "launch", "new-weekly"])

    assert result.exit_code == 0, result.output
    cfg = load_config(coga_os)
    ref = list_tasks(cfg)[0]
    assert git_repo.origin_tracks(f"coga/tasks/{ref.id_slug}/ticket.md")
    # The feature-only template ticket must not be published to control.
    assert not git_repo.origin_tracks("coga/recurring/new-weekly/ticket.md")
    # The create history lands in the repo-global log, committed locally on the
    # feature branch (it reaches control the union-safe way at PR merge).
    local_ledger = git_repo.git("show", "HEAD:coga/log.md")
    assert f"created {ref.id_slug}" in local_ledger
    assert git_repo.git("status", "--porcelain") == ""


def test_recurring_launch_preserves_remote_ledger_entries_on_stale_main(
    git_repo, monkeypatch
) -> None:
    """A local control branch behind origin rebases cleanly and preserves logs."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _seed_template_blackboard(coga_os, "weekly-check", "state\n")
    log = coga_os / "log.md"
    seed_line = (
        "2026-06-01 09:00 [recurring/weekly-check] [system] created "
        "recurring/weekly-check for 2026-W23\n"
    )
    log.write_text(seed_line)
    (coga_os / ".gitattributes").write_text("/log.md merge=union\n")
    git_repo.git("add", "coga/log.md", "coga/.gitattributes")
    git_repo.git("add", "coga/contexts", "coga/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    remote_line = (
        "2026-06-08 09:00 [recurring/weekly-check] [system] created "
        "recurring/weekly-check for 2026-W22\n"
    )
    git_repo.push_competing_commit(
        "coga/log.md",
        log.read_text() + remote_line,
    )

    monkeypatch.setattr("coga.commands.launch.launch", lambda *a, **k: None)
    result = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])

    assert result.exit_code == 0, result.output
    cfg = load_config(coga_os)
    ref = list_tasks(cfg)[0]
    ledger = git_repo.git("show", "main:coga/log.md", cwd=git_repo.origin)
    assert remote_line in ledger
    assert f"created {ref.id_slug}" in ledger
    assert git_repo.origin_tracks(f"coga/tasks/{ref.id_slug}/ticket.md")
    assert git_repo.git("status", "--porcelain") == ""


def test_recurring_launch_does_not_resurrect_remote_deleted_period_from_stale_main(
    git_repo, monkeypatch
) -> None:
    """A stale control checkout honors a remotely handled-and-deleted period."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _seed_template_blackboard(coga_os, "weekly-check", "state\n")
    _seed_global_log(git_repo)
    git_repo.git("add", "coga/contexts", "coga/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")
    stale_head = git_repo.git("rev-parse", "HEAD").strip()

    launch_calls: list[tuple[object, ...]] = []
    _patch_recurring_command_launch(
        monkeypatch, coga_os, lambda *a, **k: launch_calls.append(a)
    )
    first = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])
    assert first.exit_code == 0, first.output
    cfg = load_config(coga_os)
    ref = list_tasks(cfg)[0]
    launch_calls.clear()

    ticket = Ticket.read(ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(ref.path / "ticket.md")
    git_repo.git("add", f"coga/tasks/{ref.id_slug}")
    git_repo.git("commit", "-m", "complete recurring period")
    git_repo.git("rm", "-r", f"coga/tasks/{ref.id_slug}")
    git_repo.git("commit", "-m", "delete completed recurring period")
    git_repo.git("push", "origin", "main")
    git_repo.git("reset", "--hard", stale_head)
    monkeypatch.setattr(
        "coga.recurring_runner._interactive_stdio_has_tty", lambda: True
    )
    monkeypatch.setattr("coga.recurring_runner.notify", lambda *a, **k: None)
    _patch_recurring_command_launch(
        monkeypatch, coga_os, lambda *a, **k: launch_calls.append(a)
    )

    second = CliRunner().invoke(app, ["recurring"])

    assert second.exit_code == 0, second.output
    assert launch_calls == []
    assert not git_repo.origin_tracks(f"coga/tasks/{ref.id_slug}/ticket.md")
    assert not ref.path.exists()
    ledger = git_repo.git(
        "show",
        "main:coga/log.md",
        cwd=git_repo.origin,
    )
    assert f"created {ref.id_slug}" in ledger
    assert git_repo.git("status", "--porcelain") == ""


def test_recurring_launch_explicit_rerun_bypasses_handled_period_ledger(
    git_repo, monkeypatch
) -> None:
    """Manual `recurring launch` is an explicit same-period rerun override."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _seed_template_blackboard(coga_os, "weekly-check", "state\n")
    _seed_global_log(git_repo)
    git_repo.git("add", "coga/contexts", "coga/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    launch_calls: list[tuple[object, ...]] = []
    _patch_recurring_command_launch(
        monkeypatch, coga_os, lambda *a, **k: launch_calls.append(a)
    )
    first = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])
    assert first.exit_code == 0, first.output
    cfg = load_config(coga_os)
    ref = list_tasks(cfg)[0]
    launch_calls.clear()

    ticket = Ticket.read(ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(ref.path / "ticket.md")
    git_repo.git("add", f"coga/tasks/{ref.id_slug}")
    git_repo.git("commit", "-m", "complete recurring period")
    git_repo.git("rm", "-r", f"coga/tasks/{ref.id_slug}")
    git_repo.git("commit", "-m", "delete completed recurring period")
    git_repo.git("push", "origin", "main")
    (coga_os / "tasks").mkdir(exist_ok=True)

    second = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])

    assert second.exit_code == 0, second.output
    assert launch_calls == [(ref.id_slug,)]
    assert (coga_os / "tasks" / ref.id_slug / "ticket.md").is_file()
    assert git_repo.origin_tracks(f"coga/tasks/{ref.id_slug}/ticket.md")


def test_recurring_create_sync_restores_control_ledger_for_handled_period(
    git_repo,
) -> None:
    """A stale control checkout discards its attempted duplicate period state."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _seed_template_blackboard(coga_os, "weekly-check", "state\n")
    log = coga_os / "log.md"
    _seed_global_log(git_repo)
    git_repo.git("add", "coga/contexts", "coga/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")
    stale_head = git_repo.git("rev-parse", "HEAD").strip()

    cfg = load_config(coga_os)
    remote = create_named(cfg, "weekly-check", now=datetime(2026, 6, 8, 10, 0))
    recurring_cmd._sync_recurring_create(cfg, "weekly-check", remote.ref)
    ticket = Ticket.read(remote.ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(remote.ref.path / "ticket.md")
    git_repo.git("add", f"coga/tasks/{remote.ref.id_slug}")
    git_repo.git("commit", "-m", "complete recurring period")
    git_repo.git("rm", "-r", f"coga/tasks/{remote.ref.id_slug}")
    git_repo.git("commit", "-m", "delete completed recurring period")
    git_repo.git("push", "origin", "main")
    git_repo.git("reset", "--hard", stale_head)

    cfg = load_config(coga_os)
    stale = create_named(cfg, "weekly-check", now=datetime(2026, 6, 8, 10, 5))
    recurring_cmd._sync_recurring_create(cfg, "weekly-check", stale.ref)

    # The stale checkout's duplicate task is discarded; the create line it
    # recorded survives in the union-merged repo-global log.
    assert f"created {stale.ref.id_slug}" in "\n".join(
        task_log_lines(cfg, "recurring/weekly-check")
    )
    assert not stale.ref.path.exists()
    assert git_repo.git("status", "--porcelain") == ""


def test_recurring_create_sync_failure_after_removing_stale_task_is_soft(
    git_repo, monkeypatch, capsys
) -> None:
    """A handled-period restore can remove the task before a later git error."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _seed_template_blackboard(coga_os, "weekly-check", "state\n")
    _seed_global_log(git_repo)
    git_repo.git("add", "coga/contexts", "coga/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")
    stale_head = git_repo.git("rev-parse", "HEAD").strip()

    cfg = load_config(coga_os)
    remote = create_named(cfg, "weekly-check", now=datetime(2026, 6, 8, 10, 0))
    recurring_cmd._sync_recurring_create(cfg, "weekly-check", remote.ref)
    ticket = Ticket.read(remote.ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(remote.ref.path / "ticket.md")
    git_repo.git("add", f"coga/tasks/{remote.ref.id_slug}")
    git_repo.git("commit", "-m", "complete recurring period")
    git_repo.git("rm", "-r", f"coga/tasks/{remote.ref.id_slug}")
    git_repo.git("commit", "-m", "delete completed recurring period")
    git_repo.git("push", "origin", "main")
    git_repo.checkout_branch("feature/stale",)
    git_repo.git("reset", "--hard", stale_head)

    cfg = load_config(coga_os)
    stale = create_named(cfg, "weekly-check", now=datetime(2026, 6, 8, 10, 5))

    def fail_commit(*args, **kwargs):
        raise recurring_cmd.git.GitError("simulated index lock")

    monkeypatch.setattr("coga.recurring_runner.git._commit_paths", fail_commit)

    recurring_cmd._sync_recurring_create(cfg, "weekly-check", stale.ref)

    assert "sync failed: simulated index lock" in capsys.readouterr().err
    assert not stale.ref.path.exists()


def test_recurring_sweep_skips_task_removed_by_create_sync(
    git_repo, monkeypatch
) -> None:
    """The bare sweep does not launch a stale task removed during broadcast sync."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _seed_template_blackboard(coga_os, "weekly-check", "state\n")
    _seed_global_log(git_repo)
    git_repo.git("add", "coga/contexts", "coga/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")
    stale_head = git_repo.git("rev-parse", "HEAD").strip()

    cfg = load_config(coga_os)
    remote = create_named(cfg, "weekly-check", now=datetime(2026, 6, 8, 10, 0))
    recurring_cmd._sync_recurring_create(cfg, "weekly-check", remote.ref)
    ticket = Ticket.read(remote.ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(remote.ref.path / "ticket.md")
    git_repo.git("add", f"coga/tasks/{remote.ref.id_slug}")
    git_repo.git("commit", "-m", "complete recurring period")
    git_repo.git("rm", "-r", f"coga/tasks/{remote.ref.id_slug}")
    git_repo.git("commit", "-m", "delete completed recurring period")
    git_repo.git("push", "origin", "main")
    git_repo.git("reset", "--hard", stale_head)

    launch_calls: list[tuple[object, ...]] = []
    _freeze_recurring_now(monkeypatch, datetime(2026, 6, 8, 10, 0))  # Mon, 2026-W24
    monkeypatch.setattr(
        "coga.recurring_runner._interactive_stdio_has_tty", lambda: True
    )
    _patch_recurring_command_launch(
        monkeypatch, coga_os, lambda *a, **k: launch_calls.append(a)
    )
    monkeypatch.setattr("coga.recurring_runner.notify", lambda *a, **k: None)

    result = CliRunner().invoke(app, ["recurring"])

    assert result.exit_code == 0, result.output
    assert launch_calls == []
    assert "No recurring tasks due." in result.output
    assert not (coga_os / "tasks" / remote.ref.id_slug).exists()
    assert git_repo.git("status", "--porcelain") == ""


def test_recurring_launch_does_not_revert_remote_done_period_from_stale_main(
    git_repo, monkeypatch
) -> None:
    """A stale control checkout does not replace a remote done task with active."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _seed_template_blackboard(coga_os, "weekly-check", "state\n")
    _seed_global_log(git_repo)
    git_repo.git("add", "coga/contexts", "coga/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")
    stale_head = git_repo.git("rev-parse", "HEAD").strip()

    launch_calls: list[tuple[object, ...]] = []
    notify_calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        "coga.commands.launch.launch", lambda *a, **k: launch_calls.append(a)
    )
    monkeypatch.setattr(
        "coga.recurring_runner.notify", lambda *a, **k: notify_calls.append(a)
    )
    first = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])
    assert first.exit_code == 0, first.output
    cfg = load_config(coga_os)
    ref = list_tasks(cfg)[0]
    launch_calls.clear()
    notify_calls.clear()

    ticket = Ticket.read(ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(ref.path / "ticket.md")
    # The period task's working state lives in its own ticket.md blackboard
    # region now (no separate blackboard.md).
    replace_blackboard(ref.path / "ticket.md", "\nremote done state\n")
    git_repo.git("add", f"coga/tasks/{ref.id_slug}")
    git_repo.git("commit", "-m", "complete recurring period")
    git_repo.git("push", "origin", "main")
    git_repo.git("reset", "--hard", stale_head)

    second = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])

    assert second.exit_code == 0, second.output
    assert f"Created {ref.id_slug}" not in second.output
    assert launch_calls == []
    assert notify_calls == []
    ticket_rel = f"coga/tasks/{ref.id_slug}/ticket.md"
    remote_ticket = git_repo.git("show", f"main:{ticket_rel}", cwd=git_repo.origin)
    assert "status: done" in remote_ticket
    assert "status: active" not in remote_ticket
    assert Ticket.read(ref.path / "ticket.md").status == "done"
    assert read_blackboard(ref.path / "ticket.md") == "\nremote done state\n"
    assert git_repo.git("status", "--porcelain") == ""


def test_recurring_launch_preserves_unpushed_control_branch_commits(
    git_repo, monkeypatch
) -> None:
    """Checked-out main keeps local work and takes unrelated remote changes."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _seed_template_blackboard(coga_os, "weekly-check", "state\n")
    log = coga_os / "log.md"
    seed_line = (
        "2026-06-01 09:00 [recurring/weekly-check] [system] created "
        "recurring/weekly-check for 2026-W23\n"
    )
    log.write_text(seed_line)
    (coga_os / ".gitattributes").write_text("/log.md merge=union\n")
    git_repo.git("add", "coga/log.md", "coga/.gitattributes")
    git_repo.git("add", "coga/contexts", "coga/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    local_file = git_repo.root / "LOCAL.txt"
    local_file.write_text("local\n")
    git_repo.git("add", "LOCAL.txt")
    git_repo.git("commit", "-m", "local unpushed")
    git_repo.push_competing_commit("UNRELATED.txt", "remote\n")
    remote_line = (
        "2026-06-08 09:00 [recurring/weekly-check] [system] created "
        "recurring/weekly-check for 2026-W22\n"
    )
    git_repo.push_competing_commit(
        "coga/log.md",
        log.read_text() + remote_line,
    )

    monkeypatch.setattr("coga.commands.launch.launch", lambda *a, **k: None)
    result = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])

    assert result.exit_code == 0, result.output
    cfg = load_config(coga_os)
    ref = list_tasks(cfg)[0]
    assert git_repo.origin_tracks("LOCAL.txt")
    assert git_repo.origin_tracks("UNRELATED.txt")
    assert git_repo.origin_tracks(f"coga/tasks/{ref.id_slug}/ticket.md")
    assert local_file.read_text() == "local\n"
    assert (git_repo.root / "UNRELATED.txt").read_text() == "remote\n"
    ledger = git_repo.git(
        "show",
        "main:coga/log.md",
        cwd=git_repo.origin,
    )
    assert remote_line in ledger
    assert f"created {ref.id_slug}" in ledger
    assert git_repo.git("status", "--porcelain") == ""


def test_recurring_launch_preserves_midflight_remote_ledger_race(
    git_repo, monkeypatch
) -> None:
    """A log line pushed after local commit but before control landing survives."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _seed_template_blackboard(coga_os, "weekly-check", "state\n")
    log = coga_os / "log.md"
    seed_line = (
        "2026-06-01 09:00 [recurring/weekly-check] [system] created "
        "recurring/weekly-check for 2026-W23\n"
    )
    log.write_text(seed_line)
    (coga_os / ".gitattributes").write_text("/log.md merge=union\n")
    git_repo.git("add", "coga/log.md", "coga/.gitattributes")
    git_repo.git("add", "coga/contexts", "coga/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    git_repo.checkout_branch("feature/race")
    base_log = log.read_text()
    race_line = (
        "2026-06-08 09:00 [recurring/weekly-check] [system] created "
        "recurring/weekly-check for 2026-W22\n"
    )
    real_commit_paths = recurring_cmd.git._commit_paths

    def racing_commit(root, rels, message):
        committed = real_commit_paths(root, rels, message)
        git_repo.push_competing_commit(
            "coga/log.md",
            base_log + race_line,
        )
        return committed

    monkeypatch.setattr("coga.recurring_runner.git._commit_paths", racing_commit)
    monkeypatch.setattr("coga.commands.launch.launch", lambda *a, **k: None)
    result = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])

    assert result.exit_code == 0, result.output
    cfg = load_config(coga_os)
    ref = list_tasks(cfg)[0]
    ledger_rel = "coga/log.md"
    ledger = git_repo.git("show", f"main:{ledger_rel}", cwd=git_repo.origin)
    assert race_line in ledger
    assert f"created {ref.id_slug}" in ledger
    assert git_repo.origin_tracks(f"coga/tasks/{ref.id_slug}/ticket.md")
    local_ledger = git_repo.git("show", f"HEAD:{ledger_rel}")
    assert race_line not in local_ledger
    assert f"created {ref.id_slug}" in local_ledger
    assert git_repo.git("status", "--porcelain") == ""


def test_recurring_launch_does_not_resurrect_midflight_handled_period(
    git_repo, monkeypatch
) -> None:
    """A same-slug handled-period race wins over the local active create."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _seed_template_blackboard(coga_os, "weekly-check", "state\n")
    _seed_global_log(git_repo)
    git_repo.git("add", "coga/contexts", "coga/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")
    git_repo.checkout_branch("feature/handled-race")

    cfg = load_config(coga_os)
    outcome = create_named(cfg, "weekly-check", now=datetime(2026, 6, 8, 10, 5))
    handled_region = (
        "\nstate\n\nremote_cursor: kept\n\nlast_serviced_period: 2026-W24\n"
    )
    handled_ticket = _template_ticket_with_blackboard(
        coga_os, "weekly-check", handled_region
    )
    real_commit_paths = recurring_cmd.git._commit_paths
    raced = False

    def racing_commit(root, rels, message):
        nonlocal raced
        committed = real_commit_paths(root, rels, message)
        if not raced:
            git_repo.push_competing_commit(
                "coga/recurring/weekly-check/ticket.md",
                handled_ticket,
            )
            raced = True
        return committed

    monkeypatch.setattr("coga.recurring_runner.git._commit_paths", racing_commit)

    recurring_cmd._sync_recurring_create(cfg, "weekly-check", outcome.ref)

    # The handled control state (its cursor and W24 high-water) lives in the
    # template ticket's blackboard region; the stale checkout adopts it.
    ticket_rel = "coga/recurring/weekly-check/ticket.md"
    control_ticket = git_repo.git("show", f"main:{ticket_rel}", cwd=git_repo.origin)
    assert "remote_cursor: kept" in control_ticket
    assert "last_serviced_period: 2026-W24" in control_ticket
    local_template = coga_os / "recurring" / "weekly-check" / "ticket.md"
    assert "remote_cursor: kept" in read_blackboard(local_template)
    assert read_last_serviced_period(local_template) == "2026-W24"
    assert not git_repo.origin_tracks(f"coga/tasks/{outcome.ref.id_slug}/ticket.md")
    assert not outcome.ref.path.exists()
    assert git_repo.git("status", "--porcelain") == ""


def test_recurring_launch_removes_checked_out_control_task_when_race_handled(
    git_repo, monkeypatch, capsys
) -> None:
    """A checked-out control branch drops a new task if the remote handled it."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _seed_template_blackboard(coga_os, "weekly-check", "state\n")
    _seed_global_log(git_repo)
    git_repo.git("add", "coga/contexts", "coga/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    cfg = load_config(coga_os)
    outcome = create_named(cfg, "weekly-check", now=datetime(2026, 6, 8, 10, 5))
    handled_region = "\nstate\n\nlast_serviced_period: 2026-W24\n"
    handled_ticket = _template_ticket_with_blackboard(
        coga_os, "weekly-check", handled_region
    )
    real_fetch = recurring_cmd._fetch_control_branch
    fetch_calls = 0

    def racing_fetch(cfg_arg, root):
        nonlocal fetch_calls
        fetch_calls += 1
        real_fetch(cfg_arg, root)
        if fetch_calls == 2:
            git_repo.push_competing_commit(
                "coga/recurring/weekly-check/ticket.md",
                handled_ticket,
            )

    monkeypatch.setattr(recurring_cmd, "_fetch_control_branch", racing_fetch)

    recurring_cmd._sync_recurring_create(cfg, "weekly-check", outcome.ref)

    assert "sync failed" not in capsys.readouterr().err
    assert not outcome.ref.path.exists()
    assert not git_repo.origin_tracks(f"coga/tasks/{outcome.ref.id_slug}/ticket.md")
    ticket_rel = "coga/recurring/weekly-check/ticket.md"
    assert "last_serviced_period: 2026-W24" in git_repo.git(
        "show", f"main:{ticket_rel}", cwd=git_repo.origin
    )
    local_template = coga_os / "recurring" / "weekly-check" / "ticket.md"
    assert read_last_serviced_period(local_template) == "2026-W24"
    assert git_repo.git("status", "--porcelain") == ""


def test_recurring_create_sync_missing_git_is_soft(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    cfg = load_config(dream_repo)
    outcome = create_named(cfg, "dream", now=datetime(2026, 5, 20, 10, 0, 0))

    def missing_git(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(recurring_cmd.subprocess, "run", missing_git)
    recurring_cmd._sync_recurring_create(cfg, "dream", outcome.ref)

    assert "sync skipped" in capsys.readouterr().err


def test_recurring_launch_preserves_local_commit_when_control_fetch_fails(
    git_repo, monkeypatch
) -> None:
    """An unreachable control branch still leaves the create committed locally."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _seed_template_blackboard(coga_os, "weekly-check", "state\n")
    _seed_global_log(git_repo)
    git_repo.git("add", "coga/contexts", "coga/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")
    git_repo.git(
        "remote",
        "set-url",
        "origin",
        str(git_repo.origin.parent / "missing.git"),
    )

    monkeypatch.setattr("coga.commands.launch.launch", lambda *a, **k: None)
    result = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])

    assert result.exit_code == 0, result.output
    cfg = load_config(coga_os)
    ref = list_tasks(cfg)[0]
    log_rel = "coga/log.md"
    ticket_rel = f"coga/tasks/{ref.id_slug}/ticket.md"
    assert git_repo.git("log", "--format=%s", "-1").strip() == (
        f"Ticket: {ref.id_slug} — recurring create"
    )
    assert f"created {ref.id_slug}" in git_repo.git("show", f"HEAD:{log_rel}")
    assert "title: Weekly check" in git_repo.git("show", f"HEAD:{ticket_rel}")


def test_recurring_launch_defaults_assignee_to_default_agent(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A recurring task (Dream) with no template `assignee:` defaults to the
    repo's default agent, not the human owner — otherwise `coga launch` cannot
    resolve the assignee to an agent type. (The `direct/body` step's
    `assignee: agent` resolves to that same default agent.)"""
    monkeypatch.setattr("coga.commands.launch.launch", lambda *a, **k: None)
    CliRunner().invoke(app, ["recurring", "launch", "dream"])

    cfg = load_config(dream_repo)
    refs = list_tasks(cfg)
    ticket = Ticket.read(refs[0].path / "ticket.md")
    assert ticket.workflow["name"] == "direct/body"
    assert ticket.assignee == "claude"


def test_recurring_launch_is_idempotent(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("coga.commands.launch.launch", lambda *a, **k: None)
    runner = CliRunner()
    first = runner.invoke(app, ["recurring", "launch", "dream"])
    second = runner.invoke(app, ["recurring", "launch", "dream"])

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert "Created recurring/dream" in first.output
    assert "already created for this period" in second.output
    # Idempotent: one task directory, not two.
    assert len(list_tasks(load_config(dream_repo))) == 1


def test_recurring_launch_and_scan_converge(dream_repo: Path) -> None:
    """A manual `launch dream` and a bare `coga recurring` produce one dir."""
    cfg = load_config(dream_repo)
    now = datetime(2026, 5, 20, 10, 0, 0)  # a Wednesday

    manual = create_named(cfg, "dream", now=now)
    assert manual.created is True

    # The bare-recurring scan, same period, sees the task already exists.
    scan = scan_due(cfg, now=now)
    assert [t.created for t in scan.tasks] == [False]
    assert scan.errors == []
    assert len(list_tasks(cfg)) == 1


# --- coga recurring --force (forced full run) ----------------------------------


def test_scan_due_force_reruns_already_done_period(repo: Path) -> None:
    """`--force` (`force=True`) surfaces the real `recurring/<name>` task for
    launch even after it ran and moved to `done` — no `-dbg-` scratch run, and
    the real task is reused, not duplicated."""
    cfg = load_config(repo)
    now = datetime(2026, 4, 22, 10, 0, 0)

    # The real current-period task exists and has moved past `active`, so the
    # normal sweep would skip it.
    period = scan_due(cfg, now=now)
    period_slug = period.tasks[0].ref.id_slug
    ticket_path = period.tasks[0].ref.path / "ticket.md"
    t = Ticket.read(ticket_path)
    t.frontmatter["status"] = "done"
    ticket_path.write_text(t.render())
    assert scan_due(cfg, now=now).due == []  # nothing launchable normally

    forced = scan_due(cfg, now=now, force=True)
    assert forced.errors == []
    assert len(forced.tasks) == 1
    run = forced.tasks[0]
    # The real period task is reused — same slug, no `-dbg-` scratch.
    assert run.ref.id_slug == period_slug
    assert "-dbg-" not in run.ref.id_slug
    # `forced` includes the `done` task (coga launch re-activates it); the
    # status-filtered `due` list still skips it.
    assert run.status == "done"
    assert forced.forced == [run]
    assert forced.due == []
    # No second task dir created — the real run is reused, not cloned.
    assert len(list_tasks(cfg)) == 1


def test_scan_due_force_defers_existing_done_period_until_launch(
    repo: Path,
) -> None:
    """Scan only discovers finished tasks; launch records the forced rerun."""
    _write_recurring(
        repo,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly deliverability check"
        assignee: claude
        owner: marc
        state_keys:
        - cursor
        ---

        ## Description

        Run the full deliverability diagnostic suite.
        """,
    )
    _seed_template_blackboard(repo, "weekly-check", "cursor: old\n")
    cfg = load_config(repo)

    first = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    ref = first.tasks[0].ref
    ticket_path = ref.path / "ticket.md"
    t = Ticket.read(ticket_path)
    t.frontmatter["status"] = "done"
    ticket_path.write_text(t.render())
    # Reset the template blackboard region to just the cursor — this clobbers
    # the W17 high-water the first create wrote, exactly as a fresh
    # blackboard.md rewrite did under the old layout.
    _seed_template_blackboard(repo, "weekly-check", "cursor: new\n")

    forced = scan_due(cfg, now=datetime(2026, 4, 29, 10, 0, 0), force=True)

    assert forced.forced[0].ref == ref
    assert (
        read_last_serviced_period(repo / "recurring" / "weekly-check" / "ticket.md")
        is None
    )
    assert '"cursor": "old"' in (ref.path / ".state-snapshot.json").read_text()
    log = "\n".join(task_log_lines(cfg, "recurring/weekly-check"))
    assert "reused recurring/weekly-check for 2026-W18" not in log
    assert "created recurring/weekly-check for 2026-W18" not in log


def test_scan_due_force_does_not_advance_live_prior_period_task(
    repo: Path,
) -> None:
    """A force scan relaunches live work without marking a newer period done."""
    _write_recurring(
        repo,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly deliverability check"
        assignee: claude
        owner: marc
        state_keys:
        - cursor
        ---

        ## Description

        Run the full deliverability diagnostic suite.
        """,
    )
    _seed_template_blackboard(repo, "weekly-check", "cursor: old\n")
    cfg = load_config(repo)

    first = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    ref = first.tasks[0].ref
    _seed_template_blackboard(
        repo, "weekly-check", "cursor: new\n\nlast_serviced_period: 2026-W17\n"
    )

    forced = scan_due(cfg, now=datetime(2026, 4, 29, 10, 0, 0), force=True)

    assert forced.forced[0].ref == ref
    assert forced.forced[0].status == "active"
    assert read_last_serviced_period(
        repo / "recurring" / "weekly-check" / "ticket.md"
    ) == "2026-W17"
    log = "\n".join(task_log_lines(cfg, "recurring/weekly-check"))
    assert "reused recurring/weekly-check for 2026-W18" not in log
    assert '"cursor": "old"' in (ref.path / ".state-snapshot.json").read_text()


def test_scan_due_force_recreates_serviced_deleted_period(repo: Path) -> None:
    """`--force` bypasses the `last_serviced_period` high-water: a period that
    already ran and had its task dir deleted is re-created as a real run."""
    cfg = load_config(repo)
    now = datetime(2026, 4, 22, 10, 0, 0)

    # First real run, then delete the task dir (as Dream's retro pass would).
    first = scan_due(cfg, now=now)
    shutil.rmtree(first.tasks[0].ref.path)

    # Normal sweep skips it — already serviced and the dir is gone.
    skipped = scan_due(cfg, now=now)
    assert skipped.tasks[0].ref is None
    assert skipped.due == []

    # Force re-creates the real period task instead.
    forced = scan_due(cfg, now=now, force=True)
    assert len(forced.forced) == 1
    run = forced.forced[0]
    assert run.ref is not None
    assert "-dbg-" not in run.ref.id_slug
    assert run.status == "active"
    log = "\n".join(task_log_lines(cfg, "recurring/weekly-check"))
    assert log.count("created recurring/weekly-check for 2026-W17") == 1


def test_recurring_force_syncs_forced_recreated_period_on_control_branch(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--force` must not let the control high-water discard a forced recreate."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _seed_script_workflow(coga_os)
    _write_recurring_script(
        coga_os,
        "weekly-check",
        schedule="0 9 * * 1",
        title="Weekly check",
        extra="state_keys:\n- cursor",
    )
    _seed_template_blackboard(coga_os, "weekly-check", "cursor: old\n")
    _seed_global_log(git_repo)
    git_repo.git(
        "add",
        "coga/contexts",
        "coga/skills",
        "coga/workflows",
        "coga/recurring/weekly-check",
    )
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    cfg = load_config(coga_os)
    first = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    ref = first.tasks[0].ref
    recurring_cmd._sync_recurring_create(cfg, "weekly-check", ref)
    ticket = Ticket.read(ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(ref.path / "ticket.md")
    git_repo.git("add", f"coga/tasks/{ref.id_slug}")
    git_repo.git("commit", "-m", "complete recurring period")
    git_repo.git("rm", "-r", f"coga/tasks/{ref.id_slug}")
    git_repo.git("commit", "-m", "delete completed recurring period")
    git_repo.git("push", "origin", "main")

    launched: list[str] = []

    def fake_launch(slug: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        launched.append(slug)
        path = coga_os / "tasks" / slug / "ticket.md"
        ticket = Ticket.read(path)
        ticket.frontmatter["status"] = "done"
        ticket.write(path)

    _patch_recurring_command_launch(monkeypatch, coga_os, fake_launch)
    _freeze_recurring_now(monkeypatch, datetime(2026, 4, 22, 10, 0, 0))
    monkeypatch.chdir(coga_os)

    result = CliRunner().invoke(app, ["recurring", "--force"])

    assert result.exit_code == 0, result.output
    assert launched == [ref.id_slug]
    assert (coga_os / "tasks" / ref.id_slug / "ticket.md").is_file()
    assert git_repo.origin_tracks(f"coga/tasks/{ref.id_slug}/ticket.md")


def test_recurring_force_preserves_existing_control_task_from_stale_checkout(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A forced stale local create must not overwrite a newer control task."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _seed_script_workflow(coga_os)
    _write_recurring_script(
        coga_os,
        "weekly-check",
        schedule="0 9 * * 1",
        title="Weekly check",
        extra="state_keys:\n- cursor",
    )
    _seed_template_blackboard(coga_os, "weekly-check", "cursor: old\n")
    _seed_global_log(git_repo)
    git_repo.git(
        "add",
        "coga/contexts",
        "coga/skills",
        "coga/workflows",
        "coga/recurring/weekly-check",
    )
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")
    stale_head = git_repo.git("rev-parse", "HEAD").strip()

    cfg = load_config(coga_os)
    remote = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0)).tasks[0]
    recurring_cmd._sync_recurring_create(cfg, "weekly-check", remote.ref)
    ticket = Ticket.read(remote.ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(remote.ref.path / "ticket.md")
    replace_blackboard(remote.ref.path / "ticket.md", "\nremote done state\n")
    git_repo.git("add", f"coga/tasks/{remote.ref.id_slug}")
    git_repo.git("commit", "-m", "complete recurring period")
    git_repo.git("push", "origin", "main")
    git_repo.git("reset", "--hard", stale_head)

    launched: list[str] = []

    def fake_launch(slug: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        launched.append(slug)
        _finish_period_task(coga_os, slug)

    _patch_recurring_command_launch(monkeypatch, coga_os, fake_launch)
    _freeze_recurring_now(monkeypatch, datetime(2026, 4, 29, 10, 0, 0))
    monkeypatch.chdir(coga_os)

    result = CliRunner().invoke(app, ["recurring", "--force"])

    assert result.exit_code == 0, result.output
    assert launched == [remote.ref.id_slug]
    # The period task's state lives in its ticket.md blackboard region now.
    assert read_blackboard(remote.ref.path / "ticket.md") == "\nremote done state\n"
    assert Ticket.read(remote.ref.path / "ticket.md").status == "done"
    remote_ticket = git_repo.git(
        "show",
        f"main:coga/tasks/{remote.ref.id_slug}/ticket.md",
        cwd=git_repo.origin,
    )
    assert _blackboard_of_text(remote_ticket) == "\nremote done state\n"
    control_template = git_repo.git(
        "show",
        "main:coga/recurring/weekly-check/ticket.md",
        cwd=git_repo.origin,
    )
    assert "last_serviced_period: 2026-W18" in control_template


def test_recurring_force_restores_clean_stale_existing_task_from_control(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A clean local task dir may be stale; force mode should use control."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        assignee: claude
        owner: marc
        state_keys:
        - cursor
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _seed_template_blackboard(coga_os, "weekly-check", "cursor: old\n")
    _seed_global_log(git_repo)
    git_repo.git("add", "coga/contexts", "coga/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    cfg = load_config(coga_os)
    stale = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0)).tasks[0]
    recurring_cmd._sync_recurring_create(cfg, "weekly-check", stale.ref)
    stale_head = git_repo.git("rev-parse", "HEAD").strip()

    ticket = Ticket.read(stale.ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(stale.ref.path / "ticket.md")
    replace_blackboard(stale.ref.path / "ticket.md", "\nremote newer state\n")
    git_repo.git("add", f"coga/tasks/{stale.ref.id_slug}")
    git_repo.git("commit", "-m", "complete recurring period remotely")
    git_repo.git("push", "origin", "main")
    git_repo.git("reset", "--hard", stale_head)
    _seed_template_blackboard(
        coga_os, "weekly-check", "cursor: new\n\nlast_serviced_period: 2026-W17\n"
    )

    launched: list[str] = []

    def fake_launch(slug: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        launched.append(slug)
        _finish_period_task(coga_os, slug)

    _patch_recurring_command_launch(monkeypatch, coga_os, fake_launch)
    _freeze_recurring_now(monkeypatch, datetime(2026, 4, 29, 10, 0, 0))
    monkeypatch.chdir(coga_os)

    result = CliRunner().invoke(app, ["recurring", "--force"])

    assert result.exit_code == 0, result.output
    assert launched == [stale.ref.id_slug]
    assert read_blackboard(stale.ref.path / "ticket.md") == "\nremote newer state\n"
    assert "status: done" in (stale.ref.path / "ticket.md").read_text()
    remote_ticket = git_repo.git(
        "show",
        f"main:coga/tasks/{stale.ref.id_slug}/ticket.md",
        cwd=git_repo.origin,
    )
    assert _blackboard_of_text(remote_ticket) == "\nremote newer state\n"
    control_template = git_repo.git(
        "show",
        "main:coga/recurring/weekly-check/ticket.md",
        cwd=git_repo.origin,
    )
    assert "last_serviced_period: 2026-W18" in control_template
    assert '"cursor": "new"' in (stale.ref.path / ".state-snapshot.json").read_text()


def test_recurring_force_preserves_existing_local_task_state_during_force_sync(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Force-syncing an existing local task must not replace unsynced state."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _seed_template_blackboard(coga_os, "weekly-check", "state\n")
    _seed_global_log(git_repo)
    git_repo.git("add", "coga/contexts", "coga/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    cfg = load_config(coga_os)
    first = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0)).tasks[0]
    recurring_cmd._sync_recurring_create(cfg, "weekly-check", first.ref)
    # The period task's unsynced working state lives in its ticket.md blackboard.
    replace_blackboard(first.ref.path / "ticket.md", "\nlocal unsynced state\n")

    launched: list[str] = []

    def fake_launch(slug: str, **kwargs) -> None:
        launched.append(slug)
        assert read_blackboard(first.ref.path / "ticket.md") == (
            "\nlocal unsynced state\n"
        )
        ticket = Ticket.read(first.ref.path / "ticket.md")
        ticket.frontmatter["status"] = "done"
        ticket.write(first.ref.path / "ticket.md")

    _patch_recurring_command_launch(monkeypatch, coga_os, fake_launch)
    _freeze_recurring_now(monkeypatch, datetime(2026, 4, 29, 10, 0, 0))
    monkeypatch.chdir(coga_os)

    result = CliRunner().invoke(app, ["recurring", "--force"])

    assert result.exit_code == 0, result.output
    assert launched == [first.ref.id_slug]
    assert read_blackboard(first.ref.path / "ticket.md") == "\nlocal unsynced state\n"


def test_recurring_force_snapshot_does_not_block_control_restore(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A generated state snapshot is not a local edit worth preserving."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        assignee: claude
        owner: marc
        state_keys:
        - cursor
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _seed_template_blackboard(coga_os, "weekly-check", "cursor: old\n")
    _seed_global_log(git_repo)
    git_repo.git("add", "coga/contexts", "coga/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    cfg = load_config(coga_os)
    first = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0)).tasks[0]
    recurring_cmd._sync_recurring_create(cfg, "weekly-check", first.ref)
    ticket = Ticket.read(first.ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(first.ref.path / "ticket.md")
    replace_blackboard(first.ref.path / "ticket.md", "\nlocal stale done state\n")
    git_repo.git("add", f"coga/tasks/{first.ref.id_slug}")
    git_repo.git("commit", "-m", "local done period")
    git_repo.git("push", "origin", "main")
    stale_done_head = git_repo.git("rev-parse", "HEAD").strip()

    replace_blackboard(first.ref.path / "ticket.md", "\nremote newer done state\n")
    git_repo.git("add", f"coga/tasks/{first.ref.id_slug}")
    git_repo.git("commit", "-m", "remote newer done state")
    git_repo.git("push", "origin", "main")
    git_repo.git("reset", "--hard", stale_done_head)
    _seed_template_blackboard(
        coga_os, "weekly-check", "cursor: new\n\nlast_serviced_period: 2026-W17\n"
    )

    launched: list[str] = []

    def fake_launch(slug: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        launched.append(slug)
        _finish_period_task(coga_os, slug)

    _patch_recurring_command_launch(monkeypatch, coga_os, fake_launch)
    _freeze_recurring_now(monkeypatch, datetime(2026, 4, 29, 10, 0, 0))
    monkeypatch.chdir(coga_os)

    result = CliRunner().invoke(app, ["recurring", "--force"])

    assert result.exit_code == 0, result.output
    assert launched == [first.ref.id_slug]
    assert read_blackboard(first.ref.path / "ticket.md") == "\nremote newer done state\n"
    remote_ticket = git_repo.git(
        "show",
        f"main:coga/tasks/{first.ref.id_slug}/ticket.md",
        cwd=git_repo.origin,
    )
    assert _blackboard_of_text(remote_ticket) == "\nremote newer done state\n"
    assert '"cursor": "new"' in (first.ref.path / ".state-snapshot.json").read_text()


def test_recurring_force_does_not_mark_new_period_for_control_live_task(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale checkout must resume control's live task without W18 high-water."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _seed_script_workflow(coga_os)
    _write_recurring_script(
        coga_os, "weekly-check", schedule="0 9 * * 1", title="Weekly check"
    )
    _seed_template_blackboard(coga_os, "weekly-check", "state\n")
    _seed_global_log(git_repo)
    git_repo.git(
        "add",
        "coga/contexts",
        "coga/skills",
        "coga/workflows",
        "coga/recurring/weekly-check",
    )
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")
    stale_head = git_repo.git("rev-parse", "HEAD").strip()

    cfg = load_config(coga_os)
    remote = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0)).tasks[0]
    recurring_cmd._sync_recurring_create(cfg, "weekly-check", remote.ref)
    ticket = Ticket.read(remote.ref.path / "ticket.md")
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(remote.ref.path / "ticket.md")
    replace_blackboard(remote.ref.path / "ticket.md", "\nremote live state\n")
    git_repo.git("add", f"coga/tasks/{remote.ref.id_slug}")
    git_repo.git("commit", "-m", "remote live period")
    git_repo.git("push", "origin", "main")
    git_repo.git("reset", "--hard", stale_head)

    launched: list[str] = []

    def fake_launch(slug: str, **kwargs) -> None:
        launched.append(slug)
        assert read_blackboard(remote.ref.path / "ticket.md") == "\nremote live state\n"

    _patch_recurring_command_launch(monkeypatch, coga_os, fake_launch)
    _freeze_recurring_now(monkeypatch, datetime(2026, 4, 29, 10, 0, 0))
    monkeypatch.chdir(coga_os)

    result = CliRunner().invoke(app, ["recurring", "--force"])

    assert result.exit_code == 1, result.output
    assert launched == [remote.ref.id_slug]
    control_template = git_repo.git(
        "show",
        "main:coga/recurring/weekly-check/ticket.md",
        cwd=git_repo.origin,
    )
    assert "last_serviced_period: 2026-W17" in control_template
    assert "last_serviced_period: 2026-W18" not in control_template


def test_recurring_force_reconciles_existing_tasks_before_launch_order(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A control-branch orphan must resume before stale local fresh work."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _seed_script_workflow(coga_os)
    for name in ("aaa-first", "zzz-live"):
        _write_recurring_script(
            coga_os, name, schedule="0 9 * * 1", title=name
        )
        _seed_template_blackboard(coga_os, name, "state\n")
    _seed_global_log(git_repo)
    git_repo.git(
        "add",
        "coga/contexts",
        "coga/skills",
        "coga/workflows",
        "coga/recurring",
    )
    git_repo.git("commit", "-m", "seed recurring templates")
    git_repo.git("push", "origin", "main")

    cfg = load_config(coga_os)
    first_scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    for task in first_scan.tasks:
        assert task.ref is not None
        recurring_cmd._sync_recurring_create(cfg, task.template, task.ref)
    live = next(task for task in first_scan.tasks if task.template == "zzz-live")
    assert live.ref is not None

    ticket = Ticket.read(live.ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(live.ref.path / "ticket.md")
    git_repo.git("add", f"coga/tasks/{live.ref.id_slug}")
    git_repo.git("commit", "-m", "local done live task")
    git_repo.git("push", "origin", "main")
    stale_done_head = git_repo.git("rev-parse", "HEAD").strip()

    ticket = Ticket.read(live.ref.path / "ticket.md")
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(live.ref.path / "ticket.md")
    replace_blackboard(live.ref.path / "ticket.md", "\nremote live state\n")
    git_repo.git("add", f"coga/tasks/{live.ref.id_slug}")
    git_repo.git("commit", "-m", "remote live task")
    git_repo.git("push", "origin", "main")
    git_repo.git("reset", "--hard", stale_done_head)

    launched: list[str] = []

    def fake_launch(slug: str, **kwargs) -> None:
        launched.append(slug)

    _patch_recurring_command_launch(monkeypatch, coga_os, fake_launch)
    _freeze_recurring_now(monkeypatch, datetime(2026, 4, 29, 10, 0, 0))
    monkeypatch.chdir(coga_os)

    result = CliRunner().invoke(app, ["recurring", "--force"])

    assert result.exit_code == 1, result.output
    assert launched == [live.ref.id_slug]
    assert read_blackboard(live.ref.path / "ticket.md") == "\nremote live state\n"
    assert "recurring launch returned with status='in_progress'" in result.output


def test_recurring_force_does_not_service_unreached_existing_task(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A forced done task is serviced only once the launch loop reaches it."""
    _seed_script_workflow(repo)
    _write_recurring_script(
        repo, "aaa-first", schedule="0 9 * * 1", title="First check"
    )
    _write_recurring_script(
        repo, "zzz-second", schedule="0 9 * * 1", title="Second check"
    )
    cfg = load_config(repo)
    second = create_named(cfg, "zzz-second", now=datetime(2026, 4, 22, 10, 0, 0))
    ticket = Ticket.read(second.ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.frontmatter.pop("step", None)
    ticket.write(second.ref.path / "ticket.md")

    launched: list[str] = []

    def stop_after_first(slug: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        launched.append(slug)
        raise RuntimeError("stop sweep before second template")

    _patch_recurring_command_launch(monkeypatch, repo, stop_after_first)
    _freeze_recurring_now(monkeypatch, datetime(2026, 4, 29, 10, 0, 0))
    monkeypatch.chdir(repo)

    result = CliRunner().invoke(app, ["recurring", "--force"])

    assert result.exit_code == 1
    assert launched == ["recurring/aaa-first"]
    assert read_last_serviced_period(
        repo / "recurring" / "zzz-second" / "ticket.md"
    ) == "2026-W17"
    assert Ticket.read(second.ref.path / "ticket.md").status == "done"


def test_recurring_force_syncs_forced_existing_period_state(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A forced relaunch of an existing task still syncs parent period state."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _seed_template_blackboard(coga_os, "weekly-check", "state\n")
    _seed_global_log(git_repo)
    git_repo.git("add", "coga/contexts", "coga/recurring/weekly-check")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    cfg = load_config(coga_os)
    first = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    ref = first.tasks[0].ref
    recurring_cmd._sync_recurring_create(cfg, "weekly-check", ref)
    ticket = Ticket.read(ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(ref.path / "ticket.md")
    git_repo.git("add", f"coga/tasks/{ref.id_slug}")
    git_repo.git("commit", "-m", "complete recurring period")
    git_repo.git("push", "origin", "main")

    launched: list[str] = []

    def fake_launch(slug: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        launched.append(slug)
        _finish_period_task(coga_os, slug)

    _patch_recurring_command_launch(monkeypatch, coga_os, fake_launch)
    _freeze_recurring_now(monkeypatch, datetime(2026, 4, 29, 10, 0, 0))
    monkeypatch.chdir(coga_os)

    result = CliRunner().invoke(app, ["recurring", "--force"])

    assert result.exit_code == 0, result.output
    assert launched == [ref.id_slug]
    assert "skip (done)" not in result.output
    assert "→ launch" in result.output
    control_template = git_repo.git(
        "show",
        "main:coga/recurring/weekly-check/ticket.md",
        cwd=git_repo.origin,
    )
    assert "last_serviced_period: 2026-W18" in control_template


def test_recurring_force_launches_every_template(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launched: list[str] = []
    _allow_interactive_recurring(monkeypatch)
    _patch_recurring_command_launch(
        monkeypatch, repo, lambda slug, **k: launched.append(slug)
    )
    monkeypatch.chdir(repo)
    result = CliRunner().invoke(app, ["recurring", "--force"])

    assert result.exit_code == 0, result.output
    assert len(launched) == 1
    slug = launched[0]
    # The REAL period task is launched — not a `-dbg-` scratch run, and no
    # fold-back-to-template-log / scratch-removal step runs.
    assert slug == "recurring/weekly-check"
    assert "-dbg-" not in slug
    assert "scratch dir removed" not in result.output
    assert (repo / "tasks" / "recurring" / "weekly-check" / "ticket.md").is_file()
    assert not any("-dbg-" in p.name for p in (repo / "tasks").iterdir())


def test_recurring_force_skips_interactive_template_without_tty(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launched: list[str] = []
    monkeypatch.setattr(
        "coga.recurring_runner._interactive_stdio_has_tty", lambda: False
    )
    _patch_recurring_command_launch(
        monkeypatch, repo, lambda slug, **k: launched.append(slug)
    )
    monkeypatch.chdir(repo)

    result = CliRunner().invoke(app, ["recurring", "--force"])

    assert result.exit_code == 0, result.output
    assert launched == []
    assert "No recurring templates to launch." in result.output
    combined = result.output + (result.stderr or "")
    assert "skipping weekly-check" in combined
    assert "an agent run requires a TTY" in combined
    assert list_tasks(load_config(repo)) == []


def test_recurring_launch_unknown_template_fails(dream_repo: Path) -> None:
    result = CliRunner().invoke(app, ["recurring", "launch", "nope"])
    assert result.exit_code == 2
    assert "no recurring task `recurring/nope/`" in result.output


def test_recurring_launch_invokes_launch(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`coga recurring launch` hands the created `active` task to launch."""
    calls: list[str] = []

    def fake_launch(
        task: str,
        agent_override: str | None,
        prompt_report: bool,
        idle_timeout: float | None = None,
        max_session: float | None = None,
        return_timeout: bool = False,
    ) -> None:
        assert return_timeout is False
        assert idle_timeout == 900.0
        assert max_session is None
        ticket = Ticket.read(dream_repo / "tasks" / task / "ticket.md")
        assert ticket.status == "active"
        calls.append(task)

    monkeypatch.setattr("coga.commands.launch.launch", fake_launch)

    result = CliRunner().invoke(app, ["recurring", "launch", "dream"])

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert calls == ["recurring/dream"]


@pytest.mark.parametrize(
    "args",
    [
        ["recurring", "launch", "dream", "--agent", "codex"],
        ["recurring", "--agent", "codex", "launch", "dream"],
    ],
)
def test_recurring_launch_passes_ephemeral_agent_override(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch, args: list[str]
) -> None:
    """A named recurring launch can use another configured agent temporarily."""
    coga_toml = dream_repo / "coga.toml"
    coga_toml.write_text(
        coga_toml.read_text()
        + '\n[agents.codex]\ncli = "codex"\nfile = "AGENTS.md"\n'
    )
    seen: list[str | None] = []
    monkeypatch.setattr(
        "coga.commands.launch.launch",
        lambda task, **kwargs: seen.append(kwargs.get("agent_override")),
    )

    result = CliRunner().invoke(app, args)

    assert result.exit_code == 0, result.output
    assert seen == ["codex"]
    ticket = Ticket.read(dream_repo / "tasks" / "recurring" / "dream" / "ticket.md")
    assert ticket.assignee == "claude"


def test_recurring_launch_agent_override_leaves_script_task_as_script(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--agent` scopes agent launches without breaking script templates."""
    _seed_script_workflow(repo)
    _write_recurring_script(
        repo, "script-check", schedule="* * * * *", title="Script check"
    )
    monkeypatch.chdir(repo)
    seen: list[str | None] = []
    monkeypatch.setattr(
        "coga.commands.launch.launch",
        lambda task, **kwargs: seen.append(kwargs.get("agent_override")),
    )

    result = CliRunner().invoke(
        app, ["recurring", "launch", "script-check", "--agent", "claude"]
    )

    assert result.exit_code == 0, result.output
    assert seen == [None]


def test_recurring_rejects_unknown_agent_even_when_nothing_is_due(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert recurring_cmd.run_recurring_scan(
        load_config(repo), agent_override="goat"
    ) == 2
    assert "Agent type 'goat' is not defined" in capsys.readouterr().err


def test_recurring_launch_threads_configured_timeout_limits(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """On-demand recurring launches pass concrete launch-limit values."""
    coga_toml = dream_repo / "coga.toml"
    coga_toml.write_text(
        coga_toml.read_text() + "\n[launch]\nidle_timeout = 120\nmax_session = 3600\n"
    )
    seen: list[tuple[float | None, float | None, bool]] = []

    def fake_launch(task: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        seen.append(
            (
                kwargs.get("idle_timeout"),
                kwargs.get("max_session"),
                kwargs.get("return_timeout"),
            )
        )

    monkeypatch.setattr("coga.commands.launch.launch", fake_launch)

    result = CliRunner().invoke(app, ["recurring", "launch", "dream"])

    assert result.exit_code == 0, result.output
    assert seen == [(120.0, 3600.0, False)]


def test_recurring_launch_resumes_in_progress_orphan(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`coga recurring launch <name>` resumes an orphaned `in_progress` task.

    The on-demand path (the `coga dream` alias) follows the same rule as the
    bare sweep: an `in_progress` period task left by a dead supervisor is
    relaunched (resumed), not refused.
    """
    calls: list[str] = []
    monkeypatch.setattr(
        "coga.commands.launch.launch", lambda task, **k: calls.append(task)
    )

    # First call creates the period task (`active`); freeze it `in_progress`
    # to mimic a sweep that died mid-run.
    CliRunner().invoke(app, ["recurring", "launch", "dream"])
    cfg = load_config(dream_repo)
    ref = list_tasks(cfg)[0]
    ticket = Ticket.read(ref.path / "ticket.md")
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(ref.path / "ticket.md")
    calls.clear()

    result = CliRunner().invoke(app, ["recurring", "launch", "dream"])

    assert result.exit_code == 0, result.output
    assert "Resuming" in result.output
    assert calls == [ref.id_slug]  # relaunched, not refused


def test_recurring_launch_refuses_done_task(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A `done` period task is left alone — re-running finished work is wrong."""
    calls: list[str] = []
    monkeypatch.setattr(
        "coga.commands.launch.launch", lambda task, **k: calls.append(task)
    )

    CliRunner().invoke(app, ["recurring", "launch", "dream"])
    cfg = load_config(dream_repo)
    ref = list_tasks(cfg)[0]
    ticket = Ticket.read(ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(ref.path / "ticket.md")
    calls.clear()

    result = CliRunner().invoke(app, ["recurring", "launch", "dream"])

    assert result.exit_code == 0, result.output
    assert "is done; not launching" in result.output
    assert calls == []


def test_recurring_launch_interactive_leaves_limits_unarmed(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--interactive` is a human-stepped run and leaves limits unarmed."""
    seen: list[tuple[float | None, float | None]] = []
    monkeypatch.setattr(
        "coga.commands.launch.launch",
        lambda task, **k: seen.append(
            (k.get("idle_timeout"), k.get("max_session"))
        ),
    )

    result = CliRunner().invoke(
        app, ["recurring", "launch", "dream", "--interactive"]
    )

    assert result.exit_code == 0, result.output
    assert seen == [(None, None)]


def test_bare_recurring_scans_and_launches_due(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bare `coga recurring` creates the due task and launches it."""
    calls: list[str] = []
    _allow_interactive_recurring(monkeypatch)

    def fake_launch(task: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        calls.append(task)
        ticket = Ticket.read(dream_repo / "tasks" / task / "ticket.md")
        ticket.frontmatter["status"] = "done"
        ticket.write(dream_repo / "tasks" / task / "ticket.md")

    _patch_recurring_command_launch(monkeypatch, dream_repo, fake_launch)

    result = CliRunner().invoke(app, ["recurring"])

    assert result.exit_code == 0, result.output
    assert "Recurring scan" in result.output
    assert len(calls) == 1
    assert calls == ["recurring/dream"]


def test_bare_recurring_passes_agent_override_to_agent_tasks(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The sweep threads `--agent` through the bootstrap script boundary."""
    coga_toml = dream_repo / "coga.toml"
    coga_toml.write_text(
        coga_toml.read_text()
        + '\n[agents.codex]\ncli = "codex"\nfile = "AGENTS.md"\n'
    )
    _allow_interactive_recurring(monkeypatch)
    seen: list[str | None] = []

    def fake_launch(task: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        seen.append(kwargs.get("agent_override"))
        ticket = Ticket.read(dream_repo / "tasks" / task / "ticket.md")
        ticket.frontmatter["status"] = "done"
        ticket.write(dream_repo / "tasks" / task / "ticket.md")

    _patch_recurring_command_launch(monkeypatch, dream_repo, fake_launch)

    result = CliRunner().invoke(app, ["recurring", "--agent", "codex"])

    assert result.exit_code == 0, result.output
    assert seen == ["codex"]


def test_bare_recurring_skips_interactive_without_tty_and_continues(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unattended recurring skips interactive work and launches later due tasks."""
    _seed_script_workflow(repo)
    _write_recurring_script(
        repo, "z-script-check", schedule="* * * * *", title="Script check"
    )
    monkeypatch.chdir(repo)
    monkeypatch.setattr(
        "coga.recurring_runner._interactive_stdio_has_tty", lambda: False
    )
    calls: list[str] = []
    slack_msgs: list[str] = []

    def fake_launch(task: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        calls.append(task)
        ticket = Ticket.read(repo / "tasks" / task / "ticket.md")
        ticket.frontmatter["status"] = "done"
        ticket.write(repo / "tasks" / task / "ticket.md")

    def capture_slack(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        slack_msgs.append(json["text"])

        class R:
            status_code = 200
            text = "ok"

        return R()

    _patch_recurring_command_launch(monkeypatch, repo, fake_launch)
    monkeypatch.setattr("coga.notification.slack.requests.post", capture_slack)

    result = CliRunner().invoke(app, ["recurring"])

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert calls == ["recurring/z-script-check"]
    combined = result.output + (result.stderr or "")
    assert "skipping weekly-check" in combined
    assert "an agent run requires a TTY" in combined
    assert any(
        "skipped 1 template" in msg and "weekly-check" in msg
        for msg in slack_msgs
    )


def test_bare_recurring_skips_malformed_schedule_and_continues(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bad cron is a per-template skip, not a sweep-killer."""
    _write_recurring(
        repo,
        "bad-cron",
        """
        ---
        schedule: "not a cron"
        title: "Bad cron"
        assignee: claude
        owner: marc
        ---

        ## Description

        Bad schedule.
        """,
    )
    _write_recurring(
        repo,
        "z-script-check",
        """
        ---
        schedule: "0 9 * * *"
        title: "Script check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Script.
        """,
    )
    monkeypatch.chdir(repo)
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://example.invalid/webhook")
    _freeze_recurring_now(monkeypatch, datetime(2026, 4, 22, 10, 0, 0))
    _allow_interactive_recurring(monkeypatch)
    calls: list[str] = []
    slack_msgs: list[str] = []

    def fake_launch(task: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        calls.append(task)
        ticket = Ticket.read(repo / "tasks" / task / "ticket.md")
        ticket.frontmatter["status"] = "done"
        ticket.write(repo / "tasks" / task / "ticket.md")

    def capture_slack(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        slack_msgs.append(json["text"])

        class R:
            status_code = 200
            text = "ok"

        return R()

    _patch_recurring_command_launch(monkeypatch, repo, fake_launch)
    monkeypatch.setattr("coga.notification.slack.requests.post", capture_slack)

    result = CliRunner().invoke(app, ["recurring"])

    assert result.exit_code == 0, result.output
    assert calls == ["recurring/weekly-check", "recurring/z-script-check"]
    combined = result.output + (result.stderr or "")
    assert "skipping bad-cron" in combined
    assert "`schedule` is not a valid cron expression" in combined
    assert any(
        "skipped 1 template" in msg and "bad-cron" in msg for msg in slack_msgs
    )


def test_bare_recurring_continues_past_unfinished_interactive_task(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Interactive templates do not gate the sweep on `status: done`.

    The human is driving — exiting the agent without marking done is a
    "park this run and move on" signal, not a stuck task. The sweep pauses
    that task, prints a note, and proceeds to the next due task.
    """
    _write_recurring(
        repo,
        "z-weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Second weekly check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the second diagnostic suite.
        """,
    )
    monkeypatch.chdir(repo)
    calls: list[str] = []
    _allow_interactive_recurring(monkeypatch)

    def fake_launch(task: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        calls.append(task)
        ticket = Ticket.read(repo / "tasks" / task / "ticket.md")
        ticket.frontmatter["status"] = "in_progress"
        ticket.write(repo / "tasks" / task / "ticket.md")

    _patch_recurring_command_launch(monkeypatch, repo, fake_launch)

    result = CliRunner().invoke(app, ["recurring"])

    assert result.exit_code == 0, result.output
    assert len(calls) == 2
    assert calls == ["recurring/weekly-check", "recurring/z-weekly-check"]
    assert "paused and continuing to next due task (interactive)" in result.output

    cfg = load_config(repo)
    refs = list_tasks(cfg)
    assert {Ticket.read(ref.path / "ticket.md").status for ref in refs} == {"paused"}

    calls.clear()
    second = CliRunner().invoke(app, ["recurring"])
    assert second.exit_code == 0, second.output
    assert calls == []
    assert "No recurring tasks due." in second.output


def test_bare_recurring_records_liveness_timeout_not_human_pause(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A launch that ends in a liveness timeout is recorded as a watchdog
    timeout — not the human-pause masquerade.

    `launch` returns "timeout" when the supervisor tore a wedged REPL down. The
    sweep must pause the task (so the next scan doesn't relaunch the orphan) but
    log/broadcast it as a timeout with a system actor, and continue the sweep.
    """
    monkeypatch.chdir(repo)
    calls: list[str] = []
    _allow_interactive_recurring(monkeypatch)

    def fake_launch(task: str, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(task)
        ticket = Ticket.read(repo / "tasks" / task / "ticket.md")
        ticket.frontmatter["status"] = "in_progress"
        ticket.write(repo / "tasks" / task / "ticket.md")
        return "timeout"

    _patch_recurring_command_launch(monkeypatch, repo, fake_launch)

    result = CliRunner().invoke(app, ["recurring"])

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "timed out" in result.output
    assert "paused as a watchdog timeout" in result.output

    cfg = load_config(repo)
    ref = list_tasks(cfg)[0]
    assert Ticket.read(ref.path / "ticket.md").status == "paused"
    # The durable trace names the watchdog on the pause line, not a human — the
    # whole point of the fix is that this is distinguishable from a deliberate
    # human pause (which would log `[human:<user>] paused ...`).
    pause_lines = [
        line for line in task_log_lines(cfg, ref.id_slug) if "→ paused" in line
    ]
    assert pause_lines, "expected a pause entry in the global log"
    assert all("[system:watchdog]" in line for line in pause_lines)
    assert any("timed out before signalling done" in line for line in pause_lines)
    assert all(f"[human:{cfg.current_user}]" not in line for line in pause_lines)


def test_bare_recurring_stops_before_next_due_task_if_script_unfinished(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-interactive (script/auto) templates still gate the sweep on done.

    Unattended runs can't be redirected by a human at the terminal, so a
    launched-but-unfinished task is a stuck task and stops the sweep.
    """
    company = tmp_path / "coga"
    _write(
        company / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')
    _seed_period_task_context(company)
    _seed_script_workflow(company)
    _write_recurring_script(
        company, "nightly-check", schedule="0 9 * * *", title="Nightly diagnostic"
    )
    _write_recurring_script(
        company,
        "z-nightly-check",
        schedule="0 9 * * *",
        title="Second nightly check",
    )
    monkeypatch.chdir(company)
    calls: list[str] = []

    def fake_launch(task: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        calls.append(task)
        ticket = Ticket.read(company / "tasks" / task / "ticket.md")
        ticket.frontmatter["status"] = "in_progress"
        ticket.write(company / "tasks" / task / "ticket.md")

    _patch_recurring_command_launch(monkeypatch, company, fake_launch)

    result = CliRunner().invoke(app, ["recurring"])

    assert result.exit_code == 1, result.output
    assert len(calls) == 1
    assert calls == ["recurring/nightly-check"]
    combined = result.output + (result.stderr or "")
    assert "stopping before the next due task" in combined


def test_bare_recurring_interactive_leaves_limits_unarmed(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`coga recurring --interactive` leaves liveness limits unarmed."""
    seen: list[tuple[float | None, float | None]] = []
    _allow_interactive_recurring(monkeypatch)

    def fake_launch(task: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        seen.append((kwargs.get("idle_timeout"), kwargs.get("max_session")))
        ticket = Ticket.read(dream_repo / "tasks" / task / "ticket.md")
        ticket.frontmatter["status"] = "done"
        ticket.write(dream_repo / "tasks" / task / "ticket.md")

    _patch_recurring_command_launch(monkeypatch, dream_repo, fake_launch)

    result = CliRunner().invoke(app, ["recurring", "--interactive"])

    assert result.exit_code == 0, result.output
    assert seen == [(None, None)]


def test_bare_recurring_uses_ticket_mode(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bare recurring does not pass a mode override to launch."""
    seen: list[bool] = []
    _allow_interactive_recurring(monkeypatch)

    def fake_launch(task: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        seen.append("mode_override" in kwargs)
        ticket = Ticket.read(dream_repo / "tasks" / task / "ticket.md")
        ticket.frontmatter["status"] = "done"
        ticket.write(dream_repo / "tasks" / task / "ticket.md")

    _patch_recurring_command_launch(monkeypatch, dream_repo, fake_launch)

    result = CliRunner().invoke(app, ["recurring"])

    assert result.exit_code == 0, result.output
    assert seen == [False]


def _capture_idle_timeout(
    repo: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str]
) -> list[float | None]:
    """Run a recurring sweep with a stubbed launch and return the
    `idle_timeout` each launch was called with."""
    seen: list[float | None] = []
    _allow_interactive_recurring(monkeypatch)

    def fake_launch(task: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        assert kwargs.get("return_timeout") is True
        seen.append(kwargs.get("idle_timeout"))
        ticket = Ticket.read(repo / "tasks" / task / "ticket.md")
        ticket.frontmatter["status"] = "done"
        ticket.write(repo / "tasks" / task / "ticket.md")

    _patch_recurring_command_launch(monkeypatch, repo, fake_launch)
    assert CliRunner().invoke(app, argv).exit_code == 0
    return seen


def test_bare_recurring_arms_idle_timeout(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The automatic sweep arms the default idle backstop on each launch."""
    assert _capture_idle_timeout(dream_repo, monkeypatch, ["recurring"]) == [900.0]


def test_bare_recurring_config_can_disarm_idle_timeout(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`[launch].idle_timeout = 0` explicitly disables the built-in default."""
    coga_toml = dream_repo / "coga.toml"
    coga_toml.write_text(coga_toml.read_text() + "\n[launch]\nidle_timeout = 0\n")

    assert _capture_idle_timeout(dream_repo, monkeypatch, ["recurring"]) == [None]


def test_bare_recurring_interactive_leaves_idle_timeout_off(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--interactive` (a human driving by hand) leaves the REPL unbounded."""
    assert _capture_idle_timeout(
        dream_repo, monkeypatch, ["recurring", "--interactive"]
    ) == [None]


def _timeout_cfg(
    *,
    idle: float | None = None,
    idle_present: bool = False,
    max_session: float | None = None,
) -> SimpleNamespace:
    """Minimal stand-in for `Config` carrying only the launch-limit fields the
    timeout resolvers read — keeps these unit tests free of a full repo."""
    return SimpleNamespace(
        launch_idle_timeout=idle,
        launch_idle_timeout_present=idle_present,
        launch_max_session=max_session,
    )


def test_recurring_idle_timeout_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`COGA_REPL_IDLE_TIMEOUT` overrides the default window; a `<= 0`,
    non-finite, or unparseable value disarms the backstop."""
    from coga.recurring_runner import (
        _RECURRING_IDLE_TIMEOUT_SECONDS,
        _recurring_idle_timeout,
    )

    cfg = _timeout_cfg()
    monkeypatch.delenv("COGA_REPL_IDLE_TIMEOUT", raising=False)
    assert _recurring_idle_timeout(cfg) == _RECURRING_IDLE_TIMEOUT_SECONDS

    monkeypatch.setenv("COGA_REPL_IDLE_TIMEOUT", "30")
    assert _recurring_idle_timeout(cfg) == 30.0

    for disarm in ("0", "-5", "inf", "nan", "later"):
        monkeypatch.setenv("COGA_REPL_IDLE_TIMEOUT", disarm)
        assert _recurring_idle_timeout(cfg) is None, disarm


def test_recurring_idle_timeout_config_precedence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Precedence is env > `[launch].idle_timeout` > the built-in default; an
    env override wins even to disarm a committed config value."""
    from coga.recurring_runner import (
        _RECURRING_IDLE_TIMEOUT_SECONDS,
        _recurring_idle_timeout,
    )

    monkeypatch.delenv("COGA_REPL_IDLE_TIMEOUT", raising=False)
    # Config value used when no env override is set.
    assert (
        _recurring_idle_timeout(_timeout_cfg(idle=120.0, idle_present=True))
        == 120.0
    )
    assert _recurring_idle_timeout(_timeout_cfg(idle=None, idle_present=True)) is None
    # No config and no env → built-in default.
    assert _recurring_idle_timeout(_timeout_cfg()) == _RECURRING_IDLE_TIMEOUT_SECONDS
    # Env beats config, including the disarm case.
    monkeypatch.setenv("COGA_REPL_IDLE_TIMEOUT", "45")
    assert (
        _recurring_idle_timeout(_timeout_cfg(idle=120.0, idle_present=True))
        == 45.0
    )
    monkeypatch.setenv("COGA_REPL_IDLE_TIMEOUT", "0")
    assert (
        _recurring_idle_timeout(_timeout_cfg(idle=120.0, idle_present=True)) is None
    )


def test_recurring_max_session_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Max-session has no built-in default — None unless config or env sets it.
    Precedence mirrors idle-timeout: env > `[launch].max_session` > None."""
    from coga.recurring_runner import _recurring_max_session

    monkeypatch.delenv("COGA_REPL_MAX_SESSION", raising=False)
    assert _recurring_max_session(_timeout_cfg()) is None
    assert _recurring_max_session(_timeout_cfg(max_session=600.0)) == 600.0

    monkeypatch.setenv("COGA_REPL_MAX_SESSION", "90")
    assert _recurring_max_session(_timeout_cfg(max_session=600.0)) == 90.0
    for disarm in ("0", "-5", "inf", "nan", "later"):
        monkeypatch.setenv("COGA_REPL_MAX_SESSION", disarm)
        assert _recurring_max_session(_timeout_cfg(max_session=600.0)) is None, disarm


def test_bare_recurring_nothing_due(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second bare run in the same period whose task is `done` is a no-op.

    (An `in_progress` task is no longer a no-op — it is resumed; see
    `test_scan_due_resumes_orphaned_in_progress_task`.)
    """
    _patch_recurring_command_launch(monkeypatch, dream_repo, lambda *a, **k: None)
    _allow_interactive_recurring(monkeypatch)
    runner = CliRunner()
    runner.invoke(app, ["recurring"])  # creates + "launches" (no-op stub)

    # Mark the created task done so it is no longer launchable.
    cfg = load_config(dream_repo)
    ref = list_tasks(cfg)[0]
    ticket = Ticket.read(ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(ref.path / "ticket.md")

    result = runner.invoke(app, ["recurring"])
    assert result.exit_code == 0, result.output
    assert "No recurring tasks due." in result.output
