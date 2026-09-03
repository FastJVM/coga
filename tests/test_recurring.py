from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from datetime import datetime
import re
from pathlib import Path
from textwrap import dedent
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from coga import git as coga_git
from coga import launch_script
from coga import spool
from coga import recurring as recurring_module
from coga import recurring_runner as recurring_cmd
from coga.cli import app
from coga.commands.launch import RecurringPeriodLaunchResult
from coga.config import Config, load_config
from coga.create import create_task
from coga.logfile import append_log, task_log_lines
from coga.paths import log_path, tasks_dir
from coga.period_state import write_snapshot
from coga.recurring import (
    DueScan,
    DueTask,
    PeriodLease,
    RecurringError,
    Template,
    create_named,
    format_serviced_log,
    list_templates,
    read_serviced_ledger,
    scan_due,
    serviced_periods,
)
from coga.repl_supervisor import _TIMEOUT_EXIT_CODE
from coga.taskfile import read_blackboard, replace_blackboard, upsert_blackboard
from coga.tasks import TaskRef, list_tasks
from coga.ticket import Ticket
from coga.validate import Issue, TaskValidationError
from coga.workspace_discovery import discover_coga_repos

from conftest import init_git_repo


def read_serviced_period(template_ticket: Path) -> str | None:
    """The period `recurring/<name>` last serviced, per the repo-global log.

    Takes the template `ticket.md` path so call sites read the same as they did
    when the ledger was a mark in that file's blackboard; the value now comes
    from `coga/log.md`.
    """
    coga_os = template_ticket.parents[2]
    name = template_ticket.parent.name
    return serviced_periods(load_config(coga_os)).get(f"recurring/{name}")


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
FLOW_WEBHOOK = "https://hooks.slack.com/services/flow"
IMPORTANT_WEBHOOK = "https://hooks.slack.com/services/important"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _write_recurring(company: Path, name: str, text: str) -> None:
    """Write a recurring task as a ticket-format directory."""
    _write(company / "recurring" / name / "ticket.md", text)


def _write_recurring_script(company: Path, name: str, text: str = "") -> Path:
    """Give a recurring template the reserved `ticket.py` deterministic half."""
    path = company / "recurring" / name / "ticket.py"
    _write(path, text or "raise SystemExit(0)\n")
    return path


def _push_competing_serviced_period(git_repo, name: str, period: str) -> None:
    """Land a rival checkout's serviced-period record straight on control.

    The ledger is the repo-global log, so a competing process that handled the
    period announces it by appending there — this is what the local scan must
    notice and defer to.
    """
    git_repo.push_competing_commit(
        "coga/log.md",
        f"2026-06-08 10:00 [recurring/{name}] [system] "
        f"created recurring/{name} for {period}\n",
    )


def _control_serviced_period(git_repo, name: str) -> str | None:
    """The newest period `recurring/<name>` serviced per the *control* log.

    The cross-checkout ledger is `coga/log.md` on the control branch, so this
    is what a second checkout reads to decide a period was already handled.
    """
    text = git_repo.git("show", "main:coga/log.md", cwd=git_repo.origin)
    periods = re.findall(
        rf"\[recurring/{re.escape(name)}\] \[[^\]]*\] "
        r"(?:created|reused) \S+ for (\S+)",
        text,
    )
    return max(periods) if periods else None


def _seed_serviced_period(
    company: Path, name: str, period: str, *, verb: str = "created"
) -> None:
    """Seed the ledger: record that `recurring/<name>` serviced `period`.

    The serviced-period ledger is the repo-global append-only log, so a test
    that wants a period to read as already handled writes the same line
    `_record_run` would have written.
    """
    append_log(
        load_config(company),
        f"recurring/{name}",
        "system",
        format_serviced_log(verb, f"recurring/{name}", period),
    )


def _seed_template_blackboard(company: Path, name: str, region: str) -> None:
    """Seed a recurring template's persistent working state.

    In the single-file format a template's task-specific cross-run state — its
    `state_keys` values — lives in the blackboard region of
    `recurring/<name>/ticket.md`, not a separate `blackboard.md`.
    `upsert_blackboard` adds the fence if the hand-authored template ticket
    doesn't have one yet.

    The fence must stay on its own line, so the region text is normalized to
    start with a blank line after the fence (matching what `read_blackboard`
    returns).
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


_AGENT_WORKFLOW = "agent-run/run"
_AGENT_SKILL = "agent-run/run"


def _seed_agent_workflow(company: Path) -> None:
    """Seed a real one-step agent workflow and skill for recurring tests."""
    skill_dir = company / "skills" / _AGENT_SKILL
    skill_dir.mkdir(parents=True, exist_ok=True)
    _write(
        skill_dir / "SKILL.md",
        f"""
        ---
        name: {_AGENT_SKILL}
        description: stub agent skill
        ---

        # Agent run
        """,
    )
    _write(
        company / "workflows" / f"{_AGENT_WORKFLOW}.md",
        f"""
        ---
        name: {_AGENT_WORKFLOW}
        description: One-step agent workflow for tests.
        steps:
          - name: run
            skills:
              - {_AGENT_SKILL}
            assignee: agent
        ---

        ## run

        Agent step. Uses `{_AGENT_SKILL}`.
        """,
    )


def _write_recurring_agent(
    company: Path,
    name: str,
    *,
    schedule: str,
    title: str,
    extra: str = "",
) -> None:
    """Write an agent-backed recurring template.

    `extra` appends additional frontmatter lines (e.g. `state_keys`); each line
    is re-indented to the 8-space block so `dedent` strips uniformly.
    """
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
        workflow: {_AGENT_WORKFLOW}
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
    """Delegate agent-backed child launches while the scan runs in-process."""
    def typed_child_launch(task: str, **kwargs):  # type: ignore[no-untyped-def]
        result = child_launch(task, **kwargs)
        if isinstance(result, RecurringPeriodLaunchResult):
            return result
        cfg = load_config(repo)
        ref = next(ref for ref in list_tasks(cfg) if ref.id_slug == task)
        return RecurringPeriodLaunchResult(
            result,
            recurring_module.local_period_lease(cfg, ref),
            False,
        )

    monkeypatch.setattr(
        "coga.commands.launch.launch_recurring_period", typed_child_launch
    )


def _finish_period_task(coga_os: Path, slug: str) -> None:
    ticket_path = coga_os / "tasks" / slug / "ticket.md"
    ticket = Ticket.read(ticket_path)
    ticket.frontmatter["status"] = "done"
    ticket.write(ticket_path)
    coga_git.sync_task_state(
        load_config(coga_os), ticket_path.parent, message=f"Ticket: {slug} — done"
    )


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    company = tmp_path / "coga"
    _write(
        company / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [notification.slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        important_webhook = "env:COGA_IMPORTANT_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')
    monkeypatch.setenv("SLACK_WEBHOOK_URL", FLOW_WEBHOOK)
    monkeypatch.setenv("COGA_IMPORTANT_WEBHOOK_URL", IMPORTANT_WEBHOOK)
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


def test_bare_recurring_head_runs_registered_scan_recipe_with_argv(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, list[str]]] = []

    def fake_run_recipe(cfg, name: str, argv: list[str]) -> int:  # type: ignore[no-untyped-def]
        assert cfg.repo_root == repo.resolve()
        calls.append((name, argv))
        return 0

    monkeypatch.chdir(repo)
    monkeypatch.setattr("coga.commands.recurring.run_recipe", fake_run_recipe)

    result = CliRunner().invoke(
        app, ["recurring", "--force", "--interactive", "--agent", "claude"]
    )

    assert result.exit_code == 0, result.output
    assert calls == [
        (
            "recurring-scan",
            ["--force", "--interactive", "--agent", "claude"],
        )
    ]


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


# --- the committed `owner` gate: one operator launches recurring -------------


def _set_owner(company: Path, owner: str) -> None:
    """Name the repo's recurring owner in the committed coga.toml."""
    path = company / "coga.toml"
    path.write_text(f'owner = "{owner}"\n' + path.read_text())


def test_recurring_ungated_when_no_owner_is_configured(repo: Path) -> None:
    """A repo that names no owner keeps today's behavior — nothing to opt into."""
    assert recurring_cmd.recurring_owner_refusal(load_config(repo)) is None


def test_recurring_refusal_names_the_configured_owner(repo: Path) -> None:
    _set_owner(repo, "nick")

    refusal = recurring_cmd.recurring_owner_refusal(load_config(repo))

    assert refusal is not None
    assert "'nick'" in refusal
    assert "runs as 'marc'" in refusal


def test_recurring_refusal_reports_a_checkout_with_no_user(repo: Path) -> None:
    """A clone that never set `user` is a non-owner, not a silent owner."""
    _set_owner(repo, "nick")
    (repo / "coga.local.toml").unlink()

    refusal = recurring_cmd.recurring_owner_refusal(
        load_config(repo, require_user=False)
    )

    assert refusal is not None
    assert "'nick'" in refusal
    assert "no `user` set in coga.local.toml" in refusal


def test_recurring_scan_refuses_non_owner_before_scanning(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """The gate runs before any period state is read or written."""
    _set_owner(repo, "nick")

    def unreachable(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("scan_due ran for a non-owner")

    monkeypatch.setattr(recurring_cmd, "scan_due", unreachable)

    assert recurring_cmd.run_recurring_scan(load_config(repo)) == 2
    assert "belong to 'nick'" in capsys.readouterr().err


def test_recurring_scan_force_stays_gated_for_non_owner(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--force` forces the schedule and status filters, not the owner gate."""
    _set_owner(repo, "nick")

    def unreachable(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("scan_due ran for a non-owner")

    monkeypatch.setattr(recurring_cmd, "scan_due", unreachable)

    assert recurring_cmd.run_recurring_scan(load_config(repo), force=True) == 2


def test_recurring_scan_runs_for_the_configured_owner(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_owner(repo, "marc")
    scanned: list[Path] = []

    def fake_scan(cfg, **kwargs):  # type: ignore[no-untyped-def]
        scanned.append(cfg.repo_root)
        return DueScan(tasks=[], errors=[])

    monkeypatch.setattr(recurring_cmd, "scan_due", fake_scan)

    assert recurring_cmd.run_recurring_scan(load_config(repo)) == 0
    assert scanned == [repo]


def test_recurring_launch_refuses_non_owner_before_creating(
    repo: Path, capsys
) -> None:
    _set_owner(repo, "nick")

    code = recurring_cmd.run_recurring_named(load_config(repo), "weekly-check")

    assert code == 2
    assert not (repo / "tasks" / "recurring").exists()
    assert "belong to 'nick'" in capsys.readouterr().err


@pytest.mark.parametrize("force", [False, True], ids=["bare", "force"])
def test_recurring_scan_refuses_non_control_branch_before_scanning(
    git_repo, monkeypatch: pytest.MonkeyPatch, capsys, force: bool
) -> None:
    """Bare and forced sweeps refuse before reading any period state."""
    git_repo.checkout_branch("feature/recurring-scan")

    monkeypatch.setattr(
        recurring_cmd,
        "_sync_control_checkout_ahead",
        lambda *args, **kwargs: pytest.fail("branch refusal reached catch-up"),
    )
    monkeypatch.setattr(
        recurring_cmd,
        "scan_due",
        lambda *args, **kwargs: pytest.fail("branch refusal reached scan_due"),
    )

    assert recurring_cmd.run_recurring_scan(
        load_config(git_repo.coga_os), force=force
    ) == 2
    assert list_tasks(load_config(git_repo.coga_os)) == []
    error = capsys.readouterr().err
    assert "branch 'feature/recurring-scan'" in error
    assert "control branch 'main'" in error
    assert "git switch main" in error
    assert "--force` does not override" in error


def test_recurring_named_refuses_non_control_branch_before_creating(
    git_repo, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """The named launcher applies the same gate before creating its task."""
    git_repo.checkout_branch("feature/recurring-launch")

    monkeypatch.setattr(
        recurring_cmd,
        "_sync_control_checkout_ahead",
        lambda *args, **kwargs: pytest.fail("branch refusal reached catch-up"),
    )
    monkeypatch.setattr(
        recurring_cmd,
        "create_named",
        lambda *args, **kwargs: pytest.fail("branch refusal created a task"),
    )

    assert recurring_cmd.run_recurring_named(
        load_config(git_repo.coga_os), "weekly-check"
    ) == 2
    assert list_tasks(load_config(git_repo.coga_os)) == []
    error = capsys.readouterr().err
    assert "branch 'feature/recurring-launch'" in error
    assert "control branch 'main'" in error
    assert "git switch main" in error


def test_recurring_scan_refuses_detached_head_before_scanning(
    git_repo, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    git_repo.git("checkout", "--detach")
    monkeypatch.setattr(
        recurring_cmd,
        "_sync_control_checkout_ahead",
        lambda *args, **kwargs: pytest.fail("branch refusal reached catch-up"),
    )
    monkeypatch.setattr(
        recurring_cmd,
        "scan_due",
        lambda *args, **kwargs: pytest.fail("branch refusal reached scan_due"),
    )

    assert recurring_cmd.run_recurring_scan(load_config(git_repo.coga_os)) == 2
    assert list_tasks(load_config(git_repo.coga_os)) == []
    error = capsys.readouterr().err
    assert "detached HEAD" in error
    assert "control branch 'main'" in error


def test_recurring_branch_gate_accepts_control_branch_shadowed_by_tag(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A same-named tag cannot disguise the checked-out control branch."""
    git_repo.git("tag", "main")
    scanned: list[Path] = []
    monkeypatch.setattr(
        recurring_cmd,
        "_sync_control_checkout_ahead",
        lambda *args, **kwargs: recurring_cmd._ControlCatchup(fresh=True, reason=""),
    )
    monkeypatch.setattr(recurring_cmd, "_refuse_non_owner", lambda *args: False)
    monkeypatch.setattr(
        recurring_cmd,
        "scan_due",
        lambda task_cfg, **kwargs: scanned.append(task_cfg.repo_root)
        or DueScan(tasks=[], errors=[]),
    )

    assert recurring_cmd.run_recurring_scan(load_config(git_repo.coga_os)) == 0
    assert scanned == [git_repo.coga_os]


def test_recurring_branch_gate_refuses_git_inspection_failure(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """A broken Git probe cannot masquerade as an exempt non-git workspace."""

    def fail_toplevel(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise coga_git.GitError("simulated dubious ownership")

    monkeypatch.setattr(recurring_cmd.git, "_toplevel", fail_toplevel)
    monkeypatch.setattr(
        recurring_cmd,
        "_sync_control_checkout_ahead",
        lambda *args, **kwargs: pytest.fail("inspection refusal reached catch-up"),
    )
    monkeypatch.setattr(
        recurring_cmd,
        "scan_due",
        lambda *args, **kwargs: pytest.fail("inspection refusal reached scan_due"),
    )

    assert recurring_cmd.run_recurring_scan(load_config(repo)) == 2
    error = capsys.readouterr().err
    assert "could not determine the current branch" in error
    assert "simulated dubious ownership" in error
    assert "control branch 'main'" in error


def test_recurring_branch_gate_skips_git_disabled_checkout(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The new local-branch policy does not opt git-disabled repos back in."""
    git_repo.checkout_branch("feature/git-disabled")
    git_repo.coga_os.joinpath("coga.local.toml").write_text(
        'user = "marc"\n[git]\nenabled = false\n'
    )
    cfg = load_config(git_repo.coga_os)
    scanned: list[Path] = []
    monkeypatch.setattr(
        recurring_cmd,
        "_sync_control_checkout_ahead",
        lambda *args, **kwargs: recurring_cmd._ControlCatchup(
            fresh=False, reason="[git].enabled = false"
        ),
    )
    monkeypatch.setattr(recurring_cmd, "_refuse_non_owner", lambda *args: False)
    monkeypatch.setattr(
        recurring_cmd,
        "scan_due",
        lambda task_cfg, **kwargs: scanned.append(task_cfg.repo_root)
        or DueScan(tasks=[], errors=[]),
    )

    assert recurring_cmd.run_recurring_scan(cfg) == 0
    assert scanned == [git_repo.coga_os]


def test_recurring_branch_gate_skips_non_git_workspace(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A local markdown-only workspace has no control checkout to require."""
    cfg = load_config(repo)
    scanned: list[Path] = []
    monkeypatch.setattr(
        recurring_cmd,
        "_sync_control_checkout_ahead",
        lambda *args, **kwargs: recurring_cmd._ControlCatchup(
            fresh=False, reason="workspace is not inside a git checkout"
        ),
    )
    monkeypatch.setattr(recurring_cmd, "_refuse_non_owner", lambda *args: False)
    monkeypatch.setattr(
        recurring_cmd,
        "scan_due",
        lambda task_cfg, **kwargs: scanned.append(task_cfg.repo_root)
        or DueScan(tasks=[], errors=[]),
    )

    assert recurring_cmd.run_recurring_scan(cfg) == 0
    assert scanned == [repo]


def test_recurring_scan_ignores_uncommitted_owner_takeover(
    git_repo, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Only the committed control owner counts, never a working-tree edit."""
    config = git_repo.coga_os / "coga.toml"
    config.write_text('owner = "nick"\n' + config.read_text())
    git_repo.git("add", "coga/coga.toml")
    git_repo.git("commit", "-m", "assign recurring owner")
    git_repo.git("push", "origin", "main")
    config.write_text(
        config.read_text().replace('owner = "nick"', 'owner = "marc"')
    )
    dirty_cfg = load_config(git_repo.coga_os)
    assert dirty_cfg.owner == "marc"

    monkeypatch.setattr(
        recurring_cmd,
        "scan_due",
        lambda *args, **kwargs: pytest.fail("uncommitted takeover reached scan_due"),
    )

    assert recurring_cmd.run_recurring_scan(dirty_cfg) == 2
    assert load_config(git_repo.coga_os).owner == "marc"
    assert "belong to 'nick'" in capsys.readouterr().err


def test_recurring_scan_refuses_owner_when_control_owner_cannot_be_confirmed(
    git_repo, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """An opted-in owner cannot run offline through a pending transfer."""
    config = git_repo.coga_os / "coga.toml"
    config.write_text('owner = "marc"\n' + config.read_text())
    git_repo.git("add", "coga/coga.toml")
    git_repo.git("commit", "-m", "assign recurring owner")
    git_repo.git("push", "origin", "main")

    def fail_fetch(*args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        raise coga_git.GitError("simulated offline remote")

    monkeypatch.setattr(recurring_cmd, "_fetch_control_branch", fail_fetch)
    monkeypatch.setattr(recurring_cmd.git, "_fetch_branch_oid", fail_fetch)
    monkeypatch.setattr(
        recurring_cmd,
        "scan_due",
        lambda *args, **kwargs: pytest.fail("unconfirmed owner reached scan_due"),
    )

    assert recurring_cmd.run_recurring_scan(load_config(git_repo.coga_os)) == 2
    error = capsys.readouterr().err
    assert "could not confirm the latest committed `owner`" in error
    assert "local commit names 'marc'" in error


def test_control_tip_owner_reads_command_scoped_fetched_commit(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Owner authorization never reads checkout-wide FETCH_HEAD."""
    config = git_repo.coga_os / "coga.toml"
    git_repo.push_competing_commit(
        "coga/coga.toml", 'owner = "nick"\n' + config.read_text()
    )
    control_tip = git_repo.git("rev-parse", "main", cwd=git_repo.origin).strip()
    git_repo.git("fetch", "origin", "main")
    seen: list[tuple[Path, str, str]] = []

    def scoped_fetch(root: Path, source: str, branch: str) -> str:
        seen.append((root, source, branch))
        return control_tip

    monkeypatch.setattr(recurring_cmd.git, "_fetch_branch_oid", scoped_fetch)
    monkeypatch.setattr(
        recurring_cmd,
        "_fetch_control_branch",
        lambda *args, **kwargs: pytest.fail("owner lookup used FETCH_HEAD fetch"),
    )

    owner, error, reached = recurring_cmd._control_tip_owner(
        load_config(git_repo.coga_os)
    )

    assert (owner, error, reached) == ("nick", "", True)
    assert seen == [(git_repo.root, str(git_repo.origin), "main")]


def test_control_tip_owner_reads_the_effective_push_destination(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A distinct `pushurl` owns the state, so it owns the authorization.

    `_push_control_branch` writes period state to the push URL. Reading the
    owner from the fetch repository would let whoever *it* names create and
    launch work in a push repository owned by someone else.
    """
    config = git_repo.coga_os / "coga.toml"
    # The fetch repository says `marc` may launch...
    git_repo.push_competing_commit(
        "coga/coga.toml", 'owner = "marc"\n' + config.read_text()
    )
    # ...but pushes land somewhere that names `nick`.
    push_origin = _clone_bare_with_owner(git_repo, "nick")
    git_repo.git("remote", "set-url", "--push", "origin", str(push_origin))

    owner, error, reached = recurring_cmd._control_tip_owner(
        load_config(git_repo.coga_os)
    )

    assert (owner, error, reached) == ("nick", "", True)


def test_recurring_scan_refuses_a_multi_push_remote(
    git_repo, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Split state has no single owning repository to authorize against."""
    second = _clone_bare_with_owner(git_repo, "nick")
    # The first `--add --push` replaces the implicit fetch-URL default rather
    # than joining it, so both destinations have to be named explicitly.
    git_repo.git(
        "remote", "set-url", "--add", "--push", "origin", str(git_repo.origin)
    )
    git_repo.git("remote", "set-url", "--add", "--push", "origin", str(second))

    monkeypatch.setattr(
        recurring_cmd,
        "scan_due",
        lambda *args, **kwargs: pytest.fail("multi-push remote reached scan_due"),
    )

    cfg = load_config(git_repo.coga_os)
    owner, error, reached = recurring_cmd._control_tip_owner(cfg)
    assert owner is None and reached is True
    assert "2 effective push URLs" in error

    assert recurring_cmd.run_recurring_scan(cfg) == 2
    assert "could not confirm the latest committed `owner`" in capsys.readouterr().err


def test_control_tip_owner_reads_head_without_a_configured_remote(
    git_repo,
) -> None:
    """A genuinely remote-less checkout has no tip but its own HEAD."""
    config = git_repo.coga_os / "coga.toml"
    config.write_text('owner = "nick"\n' + config.read_text())
    git_repo.git("add", "coga/coga.toml")
    git_repo.git("commit", "-m", "assign recurring owner")
    git_repo.git("remote", "remove", "origin")

    owner, error, reached = recurring_cmd._control_tip_owner(
        load_config(git_repo.coga_os)
    )

    assert (owner, error, reached) == ("nick", "", True)


def test_local_git_disablement_does_not_bypass_the_owner_gate(
    git_repo, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """`[git].enabled = false` is the sync opt-out, not an authorization override.

    It is machine-local and uncommitted, so honoring it here would let a stale
    clone read no owner at all — while the sweep still created period state and
    launched real work.
    """
    config = git_repo.coga_os / "coga.toml"
    local = git_repo.coga_os / "coga.local.toml"
    local.write_text(local.read_text() + "\n[git]\nenabled = false\n")
    git_repo.push_competing_commit(
        "coga/coga.toml", 'owner = "nick"\n' + config.read_text()
    )
    stale_cfg = load_config(git_repo.coga_os)
    assert stale_cfg.git_enabled is False
    assert stale_cfg.owner == ""

    monkeypatch.setattr(
        recurring_cmd,
        "scan_due",
        lambda *args, **kwargs: pytest.fail("git-disabled sweep reached scan_due"),
    )

    assert recurring_cmd.run_recurring_scan(stale_cfg) == 2
    assert "belong to 'nick'" in capsys.readouterr().err


def _clone_bare_with_owner(git_repo, owner: str) -> Path:
    """A second bare repo whose control tip names `owner`."""
    bare = git_repo.origin.parent / f"push-origin-{owner}.git"
    work = git_repo.origin.parent / f"push-work-{owner}"
    git_repo.git("clone", "--bare", str(git_repo.origin), str(bare), cwd=git_repo.root)
    git_repo.git("clone", str(bare), str(work), cwd=git_repo.origin.parent)
    git_repo.git("config", "user.email", "other@example.com", cwd=work)
    git_repo.git("config", "user.name", "Other", cwd=work)
    git_repo.git("config", "commit.gpgsign", "false", cwd=work)
    git_repo.git("checkout", "-B", "main", "origin/main", cwd=work)
    config = work / "coga" / "coga.toml"
    kept = [
        line
        for line in config.read_text().splitlines(keepends=True)
        if not line.startswith("owner =")
    ]
    config.write_text(f'owner = "{owner}"\n' + "".join(kept))
    git_repo.git("add", "--", "coga/coga.toml", cwd=work)
    git_repo.git("commit", "-m", f"push-side owner {owner}", cwd=work)
    git_repo.git("push", "origin", "main", cwd=work)
    return bare


def test_recurring_all_skips_repos_owned_by_someone_else(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The gate is per repo: sweep the ones this operator owns, skip the rest."""
    root = tmp_path / "workspaces"
    mine = root / "mine" / "coga"
    theirs = root / "theirs" / "coga"
    _write(mine / "coga.toml", 'version = 1\nowner = "marc"\n')
    _write(theirs / "coga.toml", 'version = 1\nowner = "nick"\n')
    for coga_os in (mine, theirs):
        _write(coga_os / "coga.local.toml", 'user = "marc"\n')
    seen: list[Path] = []

    monkeypatch.setattr(
        recurring_cmd,
        "_run_repo_recurring",
        lambda coga_os, **kwargs: seen.append(coga_os) or 0,
    )
    result = CliRunner().invoke(app, ["recurring", "--all", str(root)])

    assert result.exit_code == 0, result.output
    assert seen == [mine]
    assert "Swept 1 of 2 Coga repo(s)." in result.output
    assert "Skipped 1 repo owned by someone else:" in result.output
    assert "theirs — Recurring launches in this repo belong to 'nick'" in result.output


def test_recurring_all_owner_skip_cannot_shadow_a_runnable_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A skipped non-owned checkout is never the keeper for its remote."""
    root = tmp_path / "workspaces"
    first = root / "alpha" / "coga"
    second = root / "beta" / "coga"
    _write(first / "coga.toml", 'version = 1\nowner = "nick"\n')
    _write(second / "coga.toml", 'version = 1\nowner = "marc"\n')
    for coga_os in (first, second):
        _write(coga_os / "coga.local.toml", 'user = "marc"\n')

    monkeypatch.setattr(
        recurring_cmd, "_git_toplevel", lambda coga_os: coga_os.parent
    )
    monkeypatch.setattr(recurring_cmd, "_current_branch", lambda _root: "main")

    def fake_subprocess_run(command, **kwargs):  # type: ignore[no-untyped-def]
        assert command[-3:] == ["remote", "get-url", "origin"]
        return SimpleNamespace(returncode=0, stdout="https://example.com/team/repo\n")

    monkeypatch.setattr(recurring_cmd.subprocess, "run", fake_subprocess_run)
    seen: list[Path] = []
    monkeypatch.setattr(
        recurring_cmd,
        "_run_repo_recurring",
        lambda coga_os, **kwargs: seen.append(coga_os) or 0,
    )
    monkeypatch.setattr(
        recurring_cmd,
        "_control_tip_owner",
        lambda cfg, **kwargs: (cfg.owner, "", True),
    )

    assert recurring_cmd.run_recurring_all_repos(root) == 0
    assert seen == [second]


def test_recurring_all_resolves_owner_from_control_tip_before_prefilter(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An owner transfer cannot leave the new owner pre-skipped forever."""
    config = git_repo.coga_os / "coga.toml"
    config.write_text('owner = "nick"\n' + config.read_text())
    git_repo.git("add", "coga/coga.toml")
    git_repo.git("commit", "-m", "assign old recurring owner")
    git_repo.git("push", "origin", "main")
    git_repo.push_competing_commit(
        "coga/coga.toml", config.read_text().replace('owner = "nick"', 'owner = "marc"')
    )

    seen: list[Path] = []
    monkeypatch.setattr(
        recurring_cmd,
        "_run_repo_recurring",
        lambda coga_os, **kwargs: seen.append(coga_os) or 0,
    )

    assert recurring_cmd.run_recurring_all_repos(git_repo.root) == 0
    assert load_config(git_repo.coga_os).owner == "nick"
    assert seen == [git_repo.coga_os]


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
        cfg = load_config(coga_root)
        ref = next(ref for ref in list_tasks(cfg) if ref.id_slug == task)
        return RecurringPeriodLaunchResult(
            None, recurring_module.local_period_lease(cfg, ref), False
        )

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
    monkeypatch.setattr("coga.commands.launch.launch_recurring_period", fake_launch)
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


def test_repo_recurring_dispatch_uses_current_python_and_ordinary_argv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    coga_os = tmp_path / "project" / "coga"
    _write(coga_os / "coga.toml", "version = 1\n")
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
        "run",
        "recurring-scan",
        "--require-fresh-control",
        "--force",
        "--interactive",
        "--agent",
        "codex",
    ]
    assert captured["cwd"] == coga_os.parent
    assert captured["check"] is False


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
    assert read_serviced_period(
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
    assert read_serviced_period(
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
    a template's extra run configuration was dropped. The full template body
    must be carried verbatim, with a `## Context` appended.
    """
    _write_recurring(
        repo,
        "run-config-template",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Has run config"
        assignee: claude
        owner: marc
        state_keys:
        - cursor
        ---

        ## Description

        Verify daily that every row has an alert.

        ## Run config

        ```yaml
        mode: watchdog
        ```

        ## Output

        Writes one JSON summary to stdout.
        """,
    )
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    task = next(t for t in scan.tasks if t.template == "run-config-template")
    body = (task.ref.path / "ticket.md").read_text()
    assert "## Run config" in body
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
    assert read_serviced_period(
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
    _seed_template_blackboard(repo, "weekly-check", "cursor: new\n")
    _seed_serviced_period(repo, "weekly-check", "2026-W17")

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
    assert read_serviced_period(
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
    assert read_serviced_period(
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
    _patch_recurring_command_launch(monkeypatch, repo, fake_launch)

    assert recurring_cmd.run_recurring_scan(cfg) == 0

    assert launched == ["recurring/weekly-check"]
    assert "Replaced completed recurring/weekly-check" in capsys.readouterr().out
    assert read_serviced_period(
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
    _patch_recurring_command_launch(monkeypatch, repo, fake_launch)
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
    assert read_serviced_period(
        repo / "recurring" / "weekly-check" / "ticket.md"
    ) == "2026-W17"
    # Only the stuck run exists — no duplicate create.
    assert {r.id_slug for r in list_tasks(cfg)} == {"recurring/weekly-check"}

    ticket.frontmatter["status"] = "done"
    ticket.write(ref.path / "ticket.md")
    shutil.rmtree(ref.path)
    next_scan = scan_due(cfg, now=datetime(2026, 4, 29, 10, 0, 0))
    assert next_scan.tasks[0].created is True
    assert read_serviced_period(
        repo / "recurring" / "weekly-check" / "ticket.md"
    ) == "2026-W18"


def test_scan_due_does_not_recreate_after_period_task_deleted(
    repo: Path,
) -> None:
    """A completed-this-period task that has been deleted stays completed.

    A later Dream retro pass deletes done recurring period tickets; a human
    `coga delete` is the other case. The repo-global log carries the
    serviced-period high-water mark, so a successful run isn't silently
    re-launched by the next `coga recurring`.
    """
    cfg = load_config(repo)
    now = datetime(2026, 4, 22, 10, 0, 0)  # a Wednesday after Monday 9am

    first = scan_due(cfg, now=now)
    assert first.tasks[0].created is True
    ref = first.tasks[0].ref

    # The load-bearing period state is the append-only log record tagged
    # `recurring/<name>`.
    log = "\n".join(task_log_lines(cfg, "recurring/weekly-check"))
    bb_path = repo / "recurring" / "weekly-check" / "ticket.md"
    assert "created recurring/weekly-check for 2026-W17" in log
    assert read_serviced_period(bb_path) == "2026-W17"

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


def test_scan_due_recognizes_serviced_period_ledger(repo: Path) -> None:
    """A period recorded in the repo-global ledger is honored."""
    now = datetime(2026, 4, 22, 10, 0, 0)  # week 17
    _seed_serviced_period(repo, "weekly-check", "2026-W17")

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


@pytest.mark.parametrize("legacy_value", ['""', "[]", "not-registered"])
def test_template_ignores_the_deleted_recipe_key(
    repo: Path, legacy_value: str
) -> None:
    """`recipe:` is gone from the format, so a leftover key is inert.

    Execution is deduced from the reserved `ticket.py` sibling alone. A stale
    declaration no longer selects a mode, and — like the legacy `script: null`
    keys — it is not an error either.
    """
    _write_recurring(
        repo,
        "legacy-recipe",
        f"""
        ---
        schedule: "0 9 * * *"
        title: Legacy recipe
        recipe: {legacy_value}
        ---
        """,
    )

    template = Template.load(repo / "recurring" / "legacy-recipe")

    assert template.script_entry_point is None
    assert not hasattr(template, "recipe")


def test_template_rejects_materialized_period_generation(repo: Path) -> None:
    """A template cannot pin every future run to one generated lease token."""
    _write_recurring(
        repo,
        "bad-generation",
        """
        ---
        schedule: "0 9 * * *"
        title: Bad generation
        period_generation: copied-token
        ---
        """,
    )

    with pytest.raises(RecurringError, match="reserved for materialized period"):
        Template.load(repo / "recurring" / "bad-generation")


def test_script_template_bypasses_agent_tty_gate(repo: Path) -> None:
    """A `ticket.py` template runs headlessly; the agent template is gated."""
    _write_recurring(
        repo,
        "script-check",
        """
        ---
        schedule: "0 9 * * *"
        title: Script check
        owner: marc
        ---

        ## Description

        Run a deterministic half.
        """,
    )
    _write_recurring_script(repo, "script-check")

    scan = scan_due(
        load_config(repo),
        now=datetime(2026, 4, 22, 10, 0, 0),
        allow_interactive=False,
    )

    task = next(task for task in scan.tasks if task.template == "script-check")
    assert task.status == "active"
    assert (task.ref.task_dir / "ticket.py").is_file()
    assert any(name == "weekly-check" for name, _ in scan.errors)


@pytest.mark.parametrize(
    ("status", "force"),
    [
        ("active", False),
        ("in_progress", False),
        ("done", True),
        ("paused", True),
    ],
)
def test_headless_scan_classifies_existing_period_from_frozen_script(
    repo: Path, capsys, status: str, force: bool
) -> None:
    """A later template script cannot turn a frozen agent period headless."""
    cfg = load_config(repo)
    outcome = create_named(
        cfg, "weekly-check", now=datetime(2026, 4, 22, 10, 0, 0)
    )
    ticket = Ticket.read(outcome.ref.ticket_path)
    ticket.frontmatter["status"] = status
    if status in {"done", "paused"}:
        ticket.frontmatter.pop("step", None)
    ticket.write(outcome.ref.ticket_path)

    # Dispatch is frozen with the materialized period. Mutating the source
    # template after creation must not reclassify this existing agent run.
    _write_recurring_script(repo, "weekly-check")
    reason = "temporary control worktree accepts recipe periods only"

    scan = scan_due(
        cfg,
        now=datetime(2026, 4, 22, 10, 1, 0),
        allow_interactive=False,
        force=force,
        agent_unavailable_reason=reason,
    )

    assert all(task.template != "weekly-check" for task in scan.tasks)
    assert dict(scan.errors)["weekly-check"] == reason
    assert Ticket.read(outcome.ref.ticket_path).status == status
    assert "skipping weekly-check" in capsys.readouterr().err


def test_local_period_lease_does_not_read_unbounded_global_log(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Generation safety stays bounded to the materialized ticket."""
    cfg = load_config(repo)
    outcome = create_named(
        cfg, "weekly-check", now=datetime(2026, 4, 22, 10, 0, 0)
    )
    ticket = Ticket.read(outcome.ref.ticket_path)
    generation = ticket.frontmatter.get("period_generation")
    assert isinstance(generation, str) and generation

    audit_path = log_path(cfg).resolve()
    original_read_bytes = Path.read_bytes

    def refuse_audit_read(path: Path) -> bytes:
        if path.resolve() == audit_path:
            pytest.fail("period lease reread the unbounded global audit log")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", refuse_audit_read)

    lease = recurring_module.local_period_lease(cfg, outcome.ref)

    assert lease.generation == generation
    assert lease.ticket_bytes == outcome.ref.ticket_path.read_bytes()


def test_local_period_lease_treats_ticket_deleted_during_capture_as_missing(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A reap racing the ticket read becomes the existing skipped lease."""
    cfg = load_config(repo)
    outcome = create_named(
        cfg, "weekly-check", now=datetime(2026, 4, 22, 10, 0, 0)
    )
    ticket_path = outcome.ref.ticket_path
    original_read_bytes = Path.read_bytes

    def disappear_during_read(path: Path) -> bytes:
        if path == ticket_path:
            raise FileNotFoundError(ticket_path)
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", disappear_during_read)

    lease = recurring_module.local_period_lease(cfg, outcome.ref)

    assert lease == PeriodLease(ticket_bytes=None, generation=None)


@pytest.mark.parametrize(
    (
        "starting_status",
        "script_code",
        "expected_status",
        "failure_important",
        "expected_url",
    ),
    [
        ("active", 0, "in_progress", True, None),
        ("active", 17, "in_progress", False, FLOW_WEBHOOK),
        ("active", 17, "in_progress", True, IMPORTANT_WEBHOOK),
        ("in_progress", 0, "in_progress", True, None),
    ],
)
def test_period_script_runs_with_period_context_secrets_and_lifecycle(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    starting_status: str,
    script_code: int,
    expected_status: str,
    failure_important: bool,
    expected_url: str | None,
) -> None:
    """The copied `ticket.py` runs with the period task's scoped environment.

    The launcher never advances the workflow on the script's behalf, so the
    status it leaves behind is `in_progress` in every case — the shim's own
    `coga bump` is what closes the step.
    """
    _write_recurring(
        repo,
        "script-check",
        """
        ---
        schedule: "0 9 * * *"
        title: Script check
        owner: marc
        secrets:
          - JOB_TOKEN: env:SCRIPT_SOURCE_TOKEN
        ---

        ## Description

        Run a deterministic half.
        """,
    )
    template_script = _write_recurring_script(repo, "script-check")
    monkeypatch.setenv("SCRIPT_SOURCE_TOKEN", "source-secret")
    monkeypatch.setenv("COGA_TASK_SLUG", "inherited-parent")
    cfg = load_config(repo)
    outcome = create_named(cfg, "script-check", now=datetime(2026, 4, 22, 10, 0, 0))
    ref = outcome.ref

    # The template's deterministic half travels into the period task; every
    # other sibling stays with the template.
    copied = ref.task_dir / "ticket.py"
    assert copied.is_file()
    assert copied.read_text() == template_script.read_text()

    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter["status"] = starting_status
    ticket.write(ref.ticket_path)
    ticket = Ticket.read(ref.ticket_path)

    captured: dict[str, object] = {}

    def fake_subprocess_run(command, **kwargs):  # type: ignore[no-untyped-def]
        captured["command"] = command
        captured.update(kwargs)
        return SimpleNamespace(returncode=script_code)

    monkeypatch.setattr(launch_script.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(launch_script, "append_log", lambda *a, **k: None)
    monkeypatch.setattr(launch_script.git, "sync_log", lambda *a, **k: None)

    deliveries: list[tuple[str, str]] = []

    def capture_post(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        deliveries.append((url, (json or {}).get("text", "")))

        class Response:
            status_code = 200
            text = "ok"

        return Response()

    monkeypatch.setattr("coga.notification.slack.requests.post", capture_post)

    result = launch_script.run_script_phase(
        cfg,
        ref,
        ticket,
        stateless=False,
        failure_important=failure_important,
    )

    assert result.exit_code == script_code
    assert Ticket.read(ref.ticket_path).status == expected_status
    assert captured["command"] == [launch_script.sys.executable, str(copied)]
    assert captured["cwd"] == repo.parent
    assert captured["check"] is False
    env = captured["env"]
    assert env["JOB_TOKEN"] == "source-secret"
    assert "SCRIPT_SOURCE_TOKEN" not in env
    assert env["COGA_TASK_SLUG"] == "recurring/script-check"
    assert env["COGA_TASK_DIR"] == str(ref.path.resolve())
    assert env["COGA_TASK_TICKET"] == str(ref.ticket_path.resolve())
    assert env["COGA_TASK_BLACKBOARD"] == str(ref.ticket_path.resolve())
    assert env["COGA_COGA_OS_ROOT"] == str(repo.resolve())
    assert env["COGA_REPO_ROOT"] == str(repo.parent.resolve())
    failures = [
        (url, text)
        for url, text in deliveries
        if "💥 script failed" in text
    ]
    assert bool(failures) is (script_code != 0)
    assert [url for url, _text in failures] == (
        [] if expected_url is None else [expected_url]
    )
    if script_code != 0:
        assert f"exit {script_code}" in failures[0][1]


def _write_delegating_template(company: Path, name: str) -> None:
    """Write a recurring template that delegates to a bootstrap ticket."""
    _write_recurring(
        company,
        name,
        """
        ---
        schedule: "0 9 * * *"
        title: "Delegated sweep"
        delegate: bootstrap/resolve-conflicts
        owner: marc
        ---

        ## Description

        Delegate the period's work to the stateless bootstrap target.
        """,
    )


@pytest.mark.parametrize(
    ("delegate_value", "message"),
    [
        ('""', "`delegate` must be a non-empty string"),
        ("[]", "`delegate` must be a non-empty string"),
        ("resolve-conflicts", "must name a stateless bootstrap command"),
        ("bootstrap/", "must name a stateless bootstrap command"),
        ("bootstrap/nested/name", "must name a stateless bootstrap command"),
        ("bootstrap/.", "must name a stateless bootstrap command"),
        ("bootstrap/..", "must name a stateless bootstrap command"),
        (r"'bootstrap/nested\name'", "must name a stateless bootstrap command"),
    ],
)
def test_template_rejects_invalid_delegate_declarations(
    repo: Path, delegate_value: str, message: str
) -> None:
    _write_recurring(
        repo,
        "delegate-check",
        f"""
        ---
        schedule: "0 9 * * *"
        title: Delegate check
        delegate: {delegate_value}
        ---
        """,
    )

    with pytest.raises(recurring_cmd.RecurringError, match=message):
        Template.load(repo / "recurring" / "delegate-check")


def test_template_rejects_delegate_combined_with_script(repo: Path) -> None:
    """`delegate:` and a `ticket.py` sibling pick opposite admission classes —
    one template cannot be both TTY-gated agent work and a headless script.

    The `recipe:` field this rule originally guarded against is gone; the
    reserved entry point is what selects deterministic execution now, so the
    exclusion is against that file's presence.
    """
    _write_recurring(
        repo,
        "delegate-check",
        """
        ---
        schedule: "0 9 * * *"
        title: Delegate check
        delegate: bootstrap/resolve-conflicts
        ---
        """,
    )
    (repo / "recurring" / "delegate-check" / "ticket.py").write_text(
        "raise SystemExit(0)\n"
    )

    with pytest.raises(
        recurring_cmd.RecurringError, match="mutually exclusive"
    ):
        Template.load(repo / "recurring" / "delegate-check")


def test_headless_scan_refuses_delegating_template_at_admission(
    repo: Path, capsys
) -> None:
    """A no-TTY sweep refuses a delegating template *before* the period task
    exists — the refusal stays at admission, exactly like any agent-backed
    template, instead of relocating into a mid-run agent-launch failure.
    """
    _write_delegating_template(repo, "delegate-check")

    cfg = load_config(repo)
    scan = scan_due(
        cfg, now=datetime(2026, 4, 22, 10, 0, 0), allow_interactive=False
    )

    errors = dict(scan.errors)
    assert "an agent run requires a TTY" in errors["delegate-check"]
    assert all(task.template != "delegate-check" for task in scan.tasks)
    assert not any(
        ref.id_slug == "recurring/delegate-check" for ref in list_tasks(cfg)
    )
    assert "skipping delegate-check" in capsys.readouterr().err


@pytest.mark.parametrize("starting_status", ["active", "in_progress"])
def test_headless_scan_skips_resumed_delegated_period_before_launch(
    repo: Path, capsys, starting_status: str
) -> None:
    """A materialized delegate remains TTY-gated on later orphan resumes.

    Admission leaves the live period untouched and still returns later
    deterministic work, so a bootstrap TTY refusal cannot abort the sweep.
    """
    _write_delegating_template(repo, "delegate-check")
    _write_recurring(
        repo,
        "z-script-check",
        """
        ---
        schedule: "0 9 * * *"
        title: Later deterministic check
        ---

        ## Description

        Run after the skipped delegated orphan.
        """,
    )
    _write_recurring_script(repo, "z-script-check")
    cfg = load_config(repo)
    outcome = create_named(
        cfg, "delegate-check", now=datetime(2026, 4, 22, 10, 0, 0)
    )
    period = Ticket.read(outcome.ref.ticket_path)
    period.frontmatter["status"] = starting_status
    period.write(outcome.ref.ticket_path)

    scan = scan_due(
        cfg, now=datetime(2026, 4, 22, 10, 1, 0), allow_interactive=False
    )

    errors = dict(scan.errors)
    assert "an agent run requires a TTY" in errors["delegate-check"]
    assert all(task.template != "delegate-check" for task in scan.tasks)
    assert [task.template for task in scan.due] == ["z-script-check"]
    assert Ticket.read(outcome.ref.ticket_path).status == starting_status
    assert "skipping delegate-check" in capsys.readouterr().err


@pytest.mark.parametrize(
    (
        "starting_status",
        "launch_kind",
        "continue_after_timeout",
        "expected_code",
        "expected_status",
        "expected_transitions",
    ),
    [
        ("active", "done", True, 0, "done", ["in_progress", "done"]),
        ("in_progress", "done", True, 0, "done", ["done"]),
        ("active", "timeout", True, 0, "paused", ["in_progress", "paused"]),
        (
            "active",
            "timeout",
            False,
            _TIMEOUT_EXIT_CODE,
            "in_progress",
            ["in_progress"],
        ),
        ("active", "natural", True, 2, "in_progress", ["in_progress"]),
        ("active", "crash", True, 2, "in_progress", ["in_progress"]),
    ],
)
def test_delegated_task_launches_target_and_owns_lifecycle(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    starting_status: str,
    launch_kind: str,
    continue_after_timeout: bool,
    expected_code: int,
    expected_status: str,
    expected_transitions: list[str],
) -> None:
    """The runner owns the delegating period task's lifecycle: it marks
    `in_progress`, launches the bootstrap target in-process (never an agent
    session on the period task), then marks `done` only for its done sentinel.
    A sweep may pause-and-continue after a watchdog timeout; named timeouts and
    natural/crashed exits fail while leaving the task retryable.
    """
    _write_delegating_template(repo, "delegate-check")
    cfg = load_config(repo)
    outcome = create_named(
        cfg, "delegate-check", now=datetime(2026, 4, 22, 10, 0, 0)
    )
    ref = outcome.ref
    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter["status"] = starting_status
    ticket.write(ref.ticket_path)

    transitions: list[str] = []
    launches: list[tuple] = []

    def fake_mark_in_progress(
        task_cfg, task_ref, current: Ticket, **kwargs  # type: ignore[no-untyped-def]
    ) -> None:
        transitions.append("in_progress")
        current.frontmatter["status"] = "in_progress"
        current.write(task_ref.ticket_path)

    def fake_mark_done(
        task_cfg, task_ref, current: Ticket, **kwargs  # type: ignore[no-untyped-def]
    ) -> None:
        transitions.append("done")
        current.frontmatter["status"] = "done"
        current.frontmatter.pop("step", None)
        current.write(task_ref.ticket_path)

    def fake_mark_paused(
        task_cfg, task_ref, current: Ticket, **kwargs  # type: ignore[no-untyped-def]
    ) -> None:
        transitions.append("paused")
        current.frontmatter["status"] = "paused"
        current.write(task_ref.ticket_path)

    def fake_launch(task: str, **kwargs) -> str | None:  # type: ignore[no-untyped-def]
        launches.append(
            (
                task,
                kwargs.get("agent_override"),
                kwargs.get("idle_timeout"),
                kwargs.get("max_session"),
                kwargs.get("return_timeout"),
                kwargs.get("launch_context"),
            )
        )
        kwargs["before_spawn"]()
        kwargs["revalidate_before_spawn"]()
        return launch_kind

    monkeypatch.setattr(recurring_cmd, "mark_in_progress", fake_mark_in_progress)
    monkeypatch.setattr(recurring_cmd, "mark_done", fake_mark_done)
    monkeypatch.setattr(recurring_cmd, "mark_paused", fake_mark_paused)
    monkeypatch.setattr("coga.commands.launch.launch_with_before_spawn", fake_launch)

    delegated = recurring_cmd._run_delegated_task(
        cfg,
        ref,
        agent_override="claude",
        idle_timeout=900.0,
        max_session=None,
        launch_context="recurring",
        continue_after_timeout=continue_after_timeout,
    )

    assert delegated.exit_code == expected_code
    assert delegated.kind == launch_kind
    assert transitions == expected_transitions
    assert Ticket.read(ref.ticket_path).status == expected_status
    # The delegated launch targets the bootstrap ticket — never the period
    # task — with the sweep's liveness and queue posture threaded through.
    assert launches == [
        (
            "bootstrap/resolve-conflicts",
            "claude",
            900.0,
            None,
            True,
            "recurring",
        )
    ]


@pytest.mark.parametrize(
    ("boundary", "termination", "capture_to_race", "expected_status"),
    [
        ("start", "done", 1, "active"),
        ("completion", "done", 2, "in_progress"),
        ("timeout", "timeout", 2, "in_progress"),
    ],
)
def test_delegated_lifecycle_snapshot_rejects_edit_after_lease(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    boundary: str,
    termination: str,
    capture_to_race: int,
    expected_status: str,
) -> None:
    """Start, done, and pause cannot render an older leased ticket over a peer."""
    _write_delegating_template(repo, "delegate-check")
    cfg = load_config(repo)
    outcome = create_named(
        cfg, "delegate-check", now=datetime(2026, 4, 22, 10, 0, 0)
    )
    real_snapshot = recurring_cmd._period_mutation_snapshot
    captures = 0
    note = f"Concurrent edit before {boundary} mutation."

    def race_snapshot(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal captures
        captures += 1
        assert kwargs["expected_ticket_bytes"] is not None
        if captures == capture_to_race:
            concurrent = Ticket.read(outcome.ref.ticket_path)
            concurrent.body += f"\n{note}\n"
            concurrent.write(outcome.ref.ticket_path)
        return real_snapshot(*args, **kwargs)

    def fake_launch(task: str, **kwargs) -> str:  # type: ignore[no-untyped-def]
        kwargs["before_spawn"]()
        kwargs["revalidate_before_spawn"]()
        return termination

    monkeypatch.setattr(recurring_cmd, "_period_mutation_snapshot", race_snapshot)
    monkeypatch.setattr(
        "coga.commands.launch.launch_with_before_spawn", fake_launch
    )
    monkeypatch.setattr("coga.mark.notify", lambda *args, **kwargs: None)

    delegated = recurring_cmd._run_delegated_task(
        cfg,
        outcome.ref,
        idle_timeout=900.0,
        max_session=None,
        continue_after_timeout=True,
    )

    final = Ticket.read(outcome.ref.ticket_path)
    assert delegated == recurring_cmd.DelegatedRunResult(2, "refused")
    assert captures == capture_to_race
    assert final.status == expected_status
    assert note in final.body


def test_delegated_completion_reloads_post_session_config(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Completion validates, publishes, and notifies with live post-child config."""
    _write_delegating_template(repo, "delegate-check")
    cfg = load_config(repo)
    outcome = create_named(
        cfg, "delegate-check", now=datetime(2026, 4, 22, 10, 0, 0)
    )
    completion_configs: list[Config] = []

    def fake_mark_in_progress(
        task_cfg, task_ref, current: Ticket, **kwargs  # type: ignore[no-untyped-def]
    ) -> None:
        current.frontmatter["status"] = "in_progress"
        current.write(task_ref.ticket_path)

    def fake_mark_done(
        task_cfg: Config, task_ref, current: Ticket, **kwargs  # type: ignore[no-untyped-def]
    ) -> None:
        completion_configs.append(task_cfg)
        current.frontmatter["status"] = "done"
        current.frontmatter.pop("step", None)
        current.write(task_ref.ticket_path)

    def fake_launch(task: str, **kwargs) -> str:  # type: ignore[no-untyped-def]
        kwargs["before_spawn"]()
        kwargs["revalidate_before_spawn"]()
        config_path = repo / "coga.toml"
        config_path.write_text(
            config_path.read_text().replace(
                'default_status = "draft"', 'default_status = "active"'
            )
        )
        return "done"

    monkeypatch.setattr(recurring_cmd, "mark_in_progress", fake_mark_in_progress)
    monkeypatch.setattr(recurring_cmd, "mark_done", fake_mark_done)
    monkeypatch.setattr("coga.commands.launch.launch_with_before_spawn", fake_launch)

    delegated = recurring_cmd._run_delegated_task(
        cfg,
        outcome.ref,
        idle_timeout=900.0,
        max_session=None,
        continue_after_timeout=True,
    )

    assert delegated == recurring_cmd.DelegatedRunResult(0, "done")
    assert len(completion_configs) == 1
    assert completion_configs[0] is not cfg
    assert completion_configs[0].default_status == "active"


@pytest.mark.parametrize(
    "mutation",
    ["terminal", "different-target", "missing-target", "ticket-bytes"],
)
def test_delegated_spawn_revalidates_exact_period_lease_after_publication(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    """No bootstrap agent starts after control movement invalidates the
    period snapshot that was published between launch preflight passes.
    """
    _write_delegating_template(repo, "delegate-check")
    cfg = load_config(repo)
    outcome = create_named(
        cfg, "delegate-check", now=datetime(2026, 4, 22, 10, 0, 0)
    )
    spawned = False

    def fake_mark_in_progress(
        task_cfg, task_ref, current: Ticket, **kwargs  # type: ignore[no-untyped-def]
    ) -> None:
        current.frontmatter["status"] = "in_progress"
        current.write(task_ref.ticket_path)

    def fake_launch(task: str, **kwargs) -> str:  # type: ignore[no-untyped-def]
        nonlocal spawned
        kwargs["before_spawn"]()
        current = Ticket.read(outcome.ref.ticket_path)
        if mutation == "terminal":
            current.frontmatter["status"] = "done"
        elif mutation == "different-target":
            current.frontmatter["delegate"] = "bootstrap/ticket"
        elif mutation == "missing-target":
            current.frontmatter.pop("delegate")
        else:
            current.body += "\nConcurrent control-plane edit.\n"
        current.write(outcome.ref.ticket_path)
        kwargs["revalidate_before_spawn"]()
        spawned = True
        return "done"

    monkeypatch.setattr(recurring_cmd, "mark_in_progress", fake_mark_in_progress)
    monkeypatch.setattr(
        recurring_cmd,
        "mark_done",
        lambda *args, **kwargs: pytest.fail("a refused spawn cannot complete"),
    )
    monkeypatch.setattr("coga.commands.launch.launch_with_before_spawn", fake_launch)

    delegated = recurring_cmd._run_delegated_task(
        cfg,
        outcome.ref,
        idle_timeout=900.0,
        max_session=None,
        continue_after_timeout=True,
    )

    assert delegated == recurring_cmd.DelegatedRunResult(2, "refused")
    assert spawned is False


def test_delegated_start_refuses_a_new_generation_before_publication(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An otherwise-identical replacement is a different period generation.

    The creator-owned token changes before the start callback, so the runner
    must refuse without marking or announcing the stale period.
    """
    _write_delegating_template(repo, "delegate-check")
    cfg = load_config(repo)
    outcome = create_named(
        cfg, "delegate-check", now=datetime(2026, 4, 22, 10, 0, 0)
    )

    def fake_launch(task: str, **kwargs) -> str:  # type: ignore[no-untyped-def]
        replacement = Ticket.read(outcome.ref.ticket_path)
        replacement.frontmatter["period_generation"] = "replacement-generation"
        replacement.write(outcome.ref.ticket_path)
        append_log(
            cfg,
            outcome.ref.id_slug,
            "system",
            "created recurring/delegate-check for 2026-W18",
        )
        kwargs["before_spawn"]()
        pytest.fail("a replaced generation must not reach spawn")

    monkeypatch.setattr(
        recurring_cmd,
        "mark_in_progress",
        lambda *args, **kwargs: pytest.fail(
            "a replaced generation must not be marked in_progress"
        ),
    )
    monkeypatch.setattr(
        "coga.commands.launch.launch_with_before_spawn", fake_launch
    )

    delegated = recurring_cmd._run_delegated_task(
        cfg,
        outcome.ref,
        idle_timeout=900.0,
        max_session=None,
        continue_after_timeout=True,
    )

    assert delegated == recurring_cmd.DelegatedRunResult(2, "refused")
    assert Ticket.read(outcome.ref.ticket_path).status == "active"


def test_delegated_start_control_cas_rejects_a_remote_generation_race(
    git_repo,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A remote replacement loses before start notification or spawn."""
    cfg = load_config(git_repo.coga_os)
    created = create_task(
        cfg=cfg,
        title="Delegated period",
        workflow_name="direct/body",
        contexts=[],
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
        slug_override="recurring/delegate-check",
        force_directory=True,
        delegate="bootstrap/resolve-conflicts",
        period_generation="generation-1",
    )
    append_log(
        cfg,
        created["slug"],
        "system",
        "created recurring/delegate-check for 2026-W17",
    )
    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", "seed delegated period")
    git_repo.git("push", "origin", "main")
    ref = next(item for item in list_tasks(cfg) if item.id_slug == created["slug"])

    replacement = Ticket.read(ref.ticket_path)
    replacement.frontmatter["period_generation"] = "generation-2"
    git_repo.push_competing_commit(
        ref.ticket_path.relative_to(git_repo.root).as_posix(),
        replacement.render(),
    )
    notifications: list[str] = []

    def fake_launch(task: str, **kwargs) -> str:  # type: ignore[no-untyped-def]
        kwargs["before_spawn"]()
        pytest.fail("a refused control CAS must not reach spawn")

    monkeypatch.setattr(
        "coga.commands.launch._preflight_push_auth", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        "coga.commands.launch.launch_with_before_spawn", fake_launch
    )
    monkeypatch.setattr(
        "coga.mark.post",
        lambda cfg, message, **kwargs: notifications.append(message),
    )

    delegated = recurring_cmd._run_delegated_task(
        cfg,
        ref,
        idle_timeout=900.0,
        max_session=None,
        continue_after_timeout=True,
    )

    assert delegated == recurring_cmd.DelegatedRunResult(2, "refused")
    assert Ticket.read(ref.ticket_path).status == "active"
    assert notifications == []


@pytest.mark.parametrize("starting_status", ["active", "in_progress"])
def test_delegated_start_fails_closed_when_control_verification_loses_transport(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    starting_status: str,
) -> None:
    """Neither a fresh start nor orphan resume may spawn from an unverified lease."""
    _write_delegating_template(repo, "delegate-check")
    cfg = load_config(repo)
    outcome = create_named(
        cfg, "delegate-check", now=datetime(2026, 4, 22, 10, 0, 0)
    )
    ticket = Ticket.read(outcome.ref.ticket_path)
    ticket.frontmatter["status"] = starting_status
    ticket.write(outcome.ref.ticket_path)
    spawned = False

    def fail_sync(*args: object, **kwargs: object) -> None:
        assert kwargs["raise_git_error"] is True
        raise coga_git.GitError("simulated transport loss")

    def fake_launch(task: str, **kwargs) -> str:  # type: ignore[no-untyped-def]
        nonlocal spawned
        kwargs["before_spawn"]()
        spawned = True
        return "done"

    monkeypatch.setattr(
        "coga.commands.launch._preflight_push_auth",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(coga_git, "sync_task_state", fail_sync)
    monkeypatch.setattr(
        "coga.commands.launch.launch_with_before_spawn", fake_launch
    )

    delegated = recurring_cmd._run_delegated_task(
        cfg,
        outcome.ref,
        idle_timeout=900.0,
        max_session=None,
        continue_after_timeout=True,
    )

    assert delegated == recurring_cmd.DelegatedRunResult(2, "refused")
    assert spawned is False
    assert Ticket.read(outcome.ref.ticket_path).status == starting_status


def test_delegated_completion_fails_closed_when_control_publication_loses_transport(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A completed child cannot announce done when its final CAS is unverified."""
    _write_delegating_template(repo, "delegate-check")
    cfg = load_config(repo)
    outcome = create_named(
        cfg, "delegate-check", now=datetime(2026, 4, 22, 10, 0, 0)
    )
    sync_calls = 0
    announcements: list[str] = []

    def fail_completion_sync(*args: object, **kwargs: object) -> None:
        nonlocal sync_calls
        sync_calls += 1
        assert kwargs["raise_git_error"] is True
        if sync_calls == 3:
            raise coga_git.GitError("simulated completion transport loss")

    def fake_launch(task: str, **kwargs) -> str:  # type: ignore[no-untyped-def]
        kwargs["before_spawn"]()
        kwargs["revalidate_before_spawn"]()
        return "done"

    monkeypatch.setattr(
        "coga.commands.launch._preflight_push_auth",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(coga_git, "sync_task_state", fail_completion_sync)
    monkeypatch.setattr(
        "coga.commands.launch.launch_with_before_spawn", fake_launch
    )
    monkeypatch.setattr(
        "coga.mark.notify",
        lambda cfg, message, **kwargs: announcements.append(message),
    )

    delegated = recurring_cmd._run_delegated_task(
        cfg,
        outcome.ref,
        idle_timeout=900.0,
        max_session=None,
        continue_after_timeout=True,
    )

    assert delegated == recurring_cmd.DelegatedRunResult(2, "refused")
    assert sync_calls == 3
    assert Ticket.read(outcome.ref.ticket_path).status == "in_progress"
    assert announcements == []


def test_delegated_completion_publishes_parent_cross_run_state(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The strict done transaction includes the recurring template cursor."""
    coga_os = git_repo.coga_os
    _write_delegating_template(coga_os, "delegate-check")
    parent_ticket = coga_os / "recurring" / "delegate-check" / "ticket.md"
    parent = Ticket.read(parent_ticket)
    parent.frontmatter["state_keys"] = ["cursor"]
    parent.write(parent_ticket)
    _seed_template_blackboard(coga_os, "delegate-check", "cursor: old\n")
    cfg = load_config(coga_os)
    created = create_task(
        cfg=cfg,
        title="Delegated period",
        workflow_name="direct/body",
        contexts=[],
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
        slug_override="recurring/delegate-check",
        force_directory=True,
        delegate="bootstrap/resolve-conflicts",
        period_generation="generation-1",
    )
    ref = next(item for item in list_tasks(cfg) if item.id_slug == created["slug"])
    write_snapshot(ref.path, "delegate-check", parent_ticket, ["cursor"])
    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", "seed delegated period with parent state")
    git_repo.git("push", "origin", "main")

    def fake_launch(task: str, **kwargs) -> str:  # type: ignore[no-untyped-def]
        kwargs["before_spawn"]()
        kwargs["revalidate_before_spawn"]()
        _seed_template_blackboard(coga_os, "delegate-check", "cursor: new\n")
        return "done"

    monkeypatch.setattr(
        "coga.commands.launch._preflight_push_auth",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        "coga.commands.launch.launch_with_before_spawn", fake_launch
    )

    delegated = recurring_cmd._run_delegated_task(
        cfg,
        ref,
        idle_timeout=900.0,
        max_session=None,
        continue_after_timeout=True,
    )

    parent_rel = parent_ticket.relative_to(git_repo.root).as_posix()
    remote_parent = git_repo.git("show", f"main:{parent_rel}", cwd=git_repo.origin)
    assert delegated == recurring_cmd.DelegatedRunResult(0, "done")
    assert Ticket.read(ref.ticket_path).status == "done"
    assert "cursor: new" in remote_parent


def test_delegated_completion_refuses_a_concurrent_parent_state_edit(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale child cursor cannot overwrite newer recurring parent state."""
    coga_os = git_repo.coga_os
    _write_delegating_template(coga_os, "delegate-check")
    parent_ticket = coga_os / "recurring" / "delegate-check" / "ticket.md"
    parent = Ticket.read(parent_ticket)
    parent.frontmatter["state_keys"] = ["cursor"]
    parent.write(parent_ticket)
    _seed_template_blackboard(coga_os, "delegate-check", "cursor: old\n")
    cfg = load_config(coga_os)
    created = create_task(
        cfg=cfg,
        title="Delegated period",
        workflow_name="direct/body",
        contexts=[],
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
        slug_override="recurring/delegate-check",
        force_directory=True,
        delegate="bootstrap/resolve-conflicts",
        period_generation="generation-1",
    )
    ref = next(item for item in list_tasks(cfg) if item.id_slug == created["slug"])
    write_snapshot(ref.path, "delegate-check", parent_ticket, ["cursor"])
    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", "seed delegated period with parent state")
    git_repo.git("push", "origin", "main")
    completion_notifications: list[str] = []

    def fake_launch(task: str, **kwargs) -> str:  # type: ignore[no-untyped-def]
        kwargs["before_spawn"]()
        kwargs["revalidate_before_spawn"]()
        _seed_template_blackboard(coga_os, "delegate-check", "cursor: child\n")
        competing_parent = _template_ticket_with_blackboard(
            coga_os,
            "delegate-check",
            "cursor: concurrent\n",
        )
        git_repo.push_competing_commit(
            parent_ticket.relative_to(git_repo.root).as_posix(),
            competing_parent,
        )
        return "done"

    monkeypatch.setattr(
        "coga.commands.launch._preflight_push_auth",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        "coga.commands.launch.launch_with_before_spawn", fake_launch
    )
    monkeypatch.setattr(
        "coga.mark.notify",
        lambda cfg, message, **kwargs: completion_notifications.append(message),
    )

    delegated = recurring_cmd._run_delegated_task(
        cfg,
        ref,
        idle_timeout=900.0,
        max_session=None,
        continue_after_timeout=True,
    )

    parent_rel = parent_ticket.relative_to(git_repo.root).as_posix()
    remote_parent = git_repo.git("show", f"main:{parent_rel}", cwd=git_repo.origin)
    period_rel = ref.ticket_path.relative_to(git_repo.root).as_posix()
    remote_period = git_repo.git("show", f"main:{period_rel}", cwd=git_repo.origin)
    assert delegated == recurring_cmd.DelegatedRunResult(2, "refused")
    assert Ticket.read(ref.ticket_path).status == "in_progress"
    assert "cursor: child" in parent_ticket.read_text()
    assert "cursor: concurrent" in remote_parent
    assert "status: in_progress" in remote_period
    assert completion_notifications == []


def test_delegated_completion_publishes_digest_event_with_done_state(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The strict completion transaction includes its configured digest event."""
    coga_os = git_repo.coga_os
    _write_delegating_template(coga_os, "delegate-check")
    digest_spool = coga_os / "recurring" / "digest" / "spool.md"
    _write(
        digest_spool,
        "# Digest spool\n\n## Spool (pending)\n\nconsumed_through:\n",
    )
    cfg = load_config(coga_os)
    outcome = create_named(
        cfg, "delegate-check", now=datetime(2026, 4, 22, 10, 0, 0)
    )
    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", "seed delegated period with digest spool")
    git_repo.git("push", "origin", "main")

    def fake_launch(task: str, **kwargs) -> str:  # type: ignore[no-untyped-def]
        kwargs["before_spawn"]()
        kwargs["revalidate_before_spawn"]()
        return "done"

    monkeypatch.setattr(
        "coga.commands.launch._preflight_push_auth",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        "coga.commands.launch.launch_with_before_spawn", fake_launch
    )

    delegated = recurring_cmd._run_delegated_task(
        cfg,
        outcome.ref,
        idle_timeout=900.0,
        max_session=None,
        continue_after_timeout=True,
    )

    ticket_rel = outcome.ref.ticket_path.relative_to(git_repo.root).as_posix()
    spool_rel = digest_spool.relative_to(git_repo.root).as_posix()
    remote_ticket = git_repo.git("show", f"main:{ticket_rel}", cwd=git_repo.origin)
    remote_spool = git_repo.git("show", f"main:{spool_rel}", cwd=git_repo.origin)
    ticket_commit = git_repo.git(
        "log", "-1", "--format=%H", "main", "--", ticket_rel,
        cwd=git_repo.origin,
    ).strip()
    spool_commit = git_repo.git(
        "log", "-1", "--format=%H", "main", "--", spool_rel,
        cwd=git_repo.origin,
    ).strip()

    assert delegated == recurring_cmd.DelegatedRunResult(0, "done")
    assert "status: done" in remote_ticket
    assert '"kind":"done"' in remote_spool
    assert '"ticket":"recurring/delegate-check"' in remote_spool
    assert ticket_commit == spool_commit


def test_delegated_completion_retains_state_when_publication_is_uncertain(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An ambiguous accepted push is reconciliation evidence, not rollback input."""
    _write_delegating_template(repo, "delegate-check")
    cfg = load_config(repo)
    outcome = create_named(
        cfg, "delegate-check", now=datetime(2026, 4, 22, 10, 0, 0)
    )
    sync_calls = 0
    announcements: list[str] = []

    def lose_completion_probe(*args: object, **kwargs: object) -> None:
        nonlocal sync_calls
        sync_calls += 1
        assert kwargs["raise_git_error"] is True
        if sync_calls == 3:
            raise coga_git.UncertainFeaturePublicationError(
                "simulated unknown control outcome"
            )

    def fake_launch(task: str, **kwargs) -> str:  # type: ignore[no-untyped-def]
        kwargs["before_spawn"]()
        kwargs["revalidate_before_spawn"]()
        return "done"

    monkeypatch.setattr(
        "coga.commands.launch._preflight_push_auth",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(coga_git, "sync_task_state", lose_completion_probe)
    monkeypatch.setattr(
        "coga.commands.launch.launch_with_before_spawn", fake_launch
    )
    monkeypatch.setattr(
        "coga.mark.notify",
        lambda cfg, message, **kwargs: announcements.append(message),
    )

    delegated = recurring_cmd._run_delegated_task(
        cfg,
        outcome.ref,
        idle_timeout=900.0,
        max_session=None,
        continue_after_timeout=True,
    )

    assert delegated == recurring_cmd.DelegatedRunResult(2, "refused")
    assert sync_calls == 3
    assert Ticket.read(outcome.ref.ticket_path).status == "done"
    assert announcements == []


def test_delegated_timeout_fails_when_control_pause_publication_loses_transport(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A sweep cannot report success when its watchdog pause is unverified."""
    _write_delegating_template(repo, "delegate-check")
    cfg = load_config(repo)
    outcome = create_named(
        cfg, "delegate-check", now=datetime(2026, 4, 22, 10, 0, 0)
    )
    sync_calls = 0
    announcements: list[str] = []

    def fail_timeout_sync(*args: object, **kwargs: object) -> None:
        nonlocal sync_calls
        sync_calls += 1
        assert kwargs["raise_git_error"] is True
        if sync_calls == 3:
            raise coga_git.GitError("simulated timeout transport loss")

    def fake_launch(task: str, **kwargs) -> str:  # type: ignore[no-untyped-def]
        kwargs["before_spawn"]()
        kwargs["revalidate_before_spawn"]()
        return "timeout"

    monkeypatch.setattr(
        "coga.commands.launch._preflight_push_auth",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(coga_git, "sync_task_state", fail_timeout_sync)
    monkeypatch.setattr(
        "coga.commands.launch.launch_with_before_spawn", fake_launch
    )
    monkeypatch.setattr(
        "coga.mark.notify",
        lambda cfg, message, **kwargs: announcements.append(message),
    )

    delegated = recurring_cmd._run_delegated_task(
        cfg,
        outcome.ref,
        idle_timeout=900.0,
        max_session=None,
        continue_after_timeout=True,
    )

    assert delegated == recurring_cmd.DelegatedRunResult(2, "refused")
    assert sync_calls == 3
    assert Ticket.read(outcome.ref.ticket_path).status == "in_progress"
    assert announcements == []


def test_delegated_completion_control_cas_rejects_a_remote_generation_race(
    git_repo,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A remote later generation cannot receive the old child's done result."""
    cfg = load_config(git_repo.coga_os)
    created = create_task(
        cfg=cfg,
        title="Delegated period",
        workflow_name="direct/body",
        contexts=[],
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
        slug_override="recurring/delegate-check",
        force_directory=True,
        delegate="bootstrap/resolve-conflicts",
    )
    append_log(
        cfg,
        created["slug"],
        "system",
        "created recurring/delegate-check for 2026-W17",
    )
    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", "seed delegated period")
    git_repo.git("push", "origin", "main")
    ref = next(item for item in list_tasks(cfg) if item.id_slug == created["slug"])
    completion_notifications: list[str] = []

    def fake_launch(task: str, **kwargs) -> str:  # type: ignore[no-untyped-def]
        kwargs["before_spawn"]()
        kwargs["revalidate_before_spawn"]()
        replacement = Ticket.read(ref.ticket_path)
        replacement.frontmatter["period_generation"] = "generation-2"
        git_repo.push_competing_commit(
            ref.ticket_path.relative_to(git_repo.root).as_posix(),
            replacement.render(),
        )
        return "done"

    monkeypatch.setattr(
        "coga.commands.launch._preflight_push_auth", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        "coga.commands.launch.launch_with_before_spawn", fake_launch
    )
    monkeypatch.setattr(
        "coga.mark.notify",
        lambda cfg, message, **kwargs: completion_notifications.append(message),
    )

    delegated = recurring_cmd._run_delegated_task(
        cfg,
        ref,
        idle_timeout=900.0,
        max_session=None,
        continue_after_timeout=True,
    )

    assert delegated == recurring_cmd.DelegatedRunResult(2, "refused")
    assert Ticket.read(ref.ticket_path).status == "in_progress"
    assert completion_notifications == []
    control_ticket = git_repo.git(
        "show", "main:coga/tasks/recurring/delegate-check/ticket.md",
        cwd=git_repo.origin,
    )
    assert "status: in_progress" in control_ticket
    assert "period_generation: generation-2" in control_ticket


@pytest.mark.parametrize(
    ("termination", "expected"),
    [
        ("done", recurring_cmd.DelegatedRunResult(2, "refused")),
        ("timeout", recurring_cmd.DelegatedRunResult(2, "refused")),
    ],
)
def test_delegated_result_cannot_mutate_a_later_period_generation(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    termination: str,
    expected: recurring_cmd.DelegatedRunResult,
) -> None:
    """The stable task path is re-leased after the child exits.

    A later generation can have otherwise-identical ``in_progress`` ticket
    state; its creator-owned token is therefore part of the lease that keeps
    the old child's done/timeout result from completing or pausing it.
    """
    _write_delegating_template(repo, "delegate-check")
    cfg = load_config(repo)
    outcome = create_named(
        cfg, "delegate-check", now=datetime(2026, 4, 22, 10, 0, 0)
    )

    def fake_mark_in_progress(
        task_cfg, task_ref, current: Ticket, **kwargs  # type: ignore[no-untyped-def]
    ) -> None:
        current.frontmatter["status"] = "in_progress"
        current.write(task_ref.ticket_path)

    def fake_launch(task: str, **kwargs) -> str:  # type: ignore[no-untyped-def]
        kwargs["before_spawn"]()
        kwargs["revalidate_before_spawn"]()
        replacement = Ticket.read(outcome.ref.ticket_path)
        replacement.frontmatter["period_generation"] = "replacement-generation"
        replacement.write(outcome.ref.ticket_path)
        append_log(
            cfg,
            outcome.ref.id_slug,
            "system",
            "created recurring/delegate-check for 2026-W18",
        )
        return termination

    monkeypatch.setattr(recurring_cmd, "mark_in_progress", fake_mark_in_progress)
    monkeypatch.setattr(
        recurring_cmd,
        "mark_done",
        lambda *args, **kwargs: pytest.fail(
            "an old child must not complete the later generation"
        ),
    )
    monkeypatch.setattr(
        recurring_cmd,
        "mark_paused",
        lambda *args, **kwargs: pytest.fail(
            "an old watchdog must not pause the later generation"
        ),
    )
    monkeypatch.setattr(
        "coga.commands.launch.launch_with_before_spawn", fake_launch
    )

    delegated = recurring_cmd._run_delegated_task(
        cfg,
        outcome.ref,
        idle_timeout=900.0,
        max_session=None,
        continue_after_timeout=True,
    )

    assert delegated == expected
    assert Ticket.read(outcome.ref.ticket_path).status == "in_progress"


def test_delegated_done_refuses_a_malformed_replacement_ticket(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Present but unparsable replacement bytes are not a reaped period."""
    _write_delegating_template(repo, "delegate-check")
    cfg = load_config(repo)
    outcome = create_named(
        cfg, "delegate-check", now=datetime(2026, 4, 22, 10, 0, 0)
    )
    malformed = b"\xffnot a ticket\n"

    def fake_launch(task: str, **kwargs) -> str:  # type: ignore[no-untyped-def]
        kwargs["before_spawn"]()
        kwargs["revalidate_before_spawn"]()
        outcome.ref.ticket_path.write_bytes(malformed)
        return "done"

    monkeypatch.setattr(
        "coga.commands.launch.launch_with_before_spawn", fake_launch
    )
    monkeypatch.setattr(
        recurring_cmd,
        "mark_done",
        lambda *args, **kwargs: pytest.fail(
            "malformed replacement state must not be completed"
        ),
    )

    delegated = recurring_cmd._run_delegated_task(
        cfg,
        outcome.ref,
        idle_timeout=900.0,
        max_session=None,
        continue_after_timeout=True,
    )

    assert delegated == recurring_cmd.DelegatedRunResult(2, "refused")
    assert outcome.ref.ticket_path.read_bytes() == malformed


def test_delegated_period_push_auth_is_preflighted_before_bootstrap_work(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The stateless bootstrap target cannot self-skip the period's auth gate."""
    _write_delegating_template(repo, "delegate-check")
    cfg = load_config(repo)
    outcome = create_named(
        cfg, "delegate-check", now=datetime(2026, 4, 22, 10, 0, 0)
    )
    checked: list[tuple[str, bool]] = []

    def refuse_auth(task_cfg, task_ref, *, is_bootstrap):  # type: ignore[no-untyped-def]
        checked.append((task_ref.id_slug, is_bootstrap))
        raise SystemExit(2)

    monkeypatch.setattr("coga.commands.launch._preflight_push_auth", refuse_auth)
    monkeypatch.setattr(
        "coga.commands.launch.launch_with_before_spawn",
        lambda *args, **kwargs: pytest.fail("bootstrap work must not start"),
    )

    with pytest.raises(SystemExit) as excinfo:
        recurring_cmd._run_delegated_task(
            cfg,
            outcome.ref,
            idle_timeout=900.0,
            max_session=None,
            continue_after_timeout=True,
        )

    assert excinfo.value.code == 2
    assert checked == [(outcome.ref.id_slug, False)]
    assert Ticket.read(outcome.ref.ticket_path).status == "active"


@pytest.mark.parametrize(
    ("starting_status", "expected_transitions"),
    [
        ("active", []),
        ("in_progress", []),
    ],
)
def test_delegated_preflight_refusal_does_not_start_period(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    starting_status: str,
    expected_transitions: list[str],
) -> None:
    """A refusal before agent spawn leaves a new active period untouched and
    preserves an existing in-progress orphan so a real prior run is not erased.
    """
    _write_delegating_template(repo, "delegate-check")
    cfg = load_config(repo)
    outcome = create_named(
        cfg, "delegate-check", now=datetime(2026, 4, 22, 10, 0, 0)
    )
    ref = outcome.ref
    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter["status"] = starting_status
    ticket.write(ref.ticket_path)
    transitions: list[str] = []

    def fake_mark_in_progress(
        task_cfg, task_ref, current: Ticket, **kwargs  # type: ignore[no-untyped-def]
    ) -> None:
        transitions.append("in_progress")
        current.frontmatter["status"] = "in_progress"
        current.write(task_ref.ticket_path)

    def refuse_before_spawn(task: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        raise SystemExit(2)

    monkeypatch.setattr(recurring_cmd, "mark_in_progress", fake_mark_in_progress)
    monkeypatch.setattr(
        "coga.commands.launch.launch_with_before_spawn", refuse_before_spawn
    )

    with pytest.raises(SystemExit) as excinfo:
        recurring_cmd._run_delegated_task(
            cfg,
            ref,
            agent_override="claude",
            idle_timeout=900.0,
            max_session=None,
            launch_context="recurring",
            continue_after_timeout=True,
        )

    assert excinfo.value.code == 2
    assert transitions == expected_transitions
    assert Ticket.read(ref.ticket_path).status == starting_status


def test_materialized_delegate_is_frozen_when_template_changes(repo: Path) -> None:
    """A live run dispatches from its task snapshot, never mutable template
    frontmatter. Removing delegation affects only the next materialization.
    """
    _write_delegating_template(repo, "delegate-check")
    cfg = load_config(repo)
    outcome = create_named(
        cfg, "delegate-check", now=datetime(2026, 4, 22, 10, 0, 0)
    )
    assert Ticket.read(outcome.ref.ticket_path).delegate == (
        "bootstrap/resolve-conflicts"
    )

    template_path = repo / "recurring" / "delegate-check" / "ticket.md"
    template_path.write_text(
        template_path.read_text().replace(
            "delegate: bootstrap/resolve-conflicts\n", ""
        )
    )

    scan = scan_due(
        cfg, now=datetime(2026, 4, 22, 10, 1, 0), allow_interactive=True
    )
    due = next(task for task in scan.tasks if task.template == "delegate-check")
    assert due.ref == outcome.ref
    assert due.delegate == "bootstrap/resolve-conflicts"


@pytest.mark.parametrize(
    ("cached_delegate", "durable_delegate", "expected_dispatch"),
    [
        ("bootstrap/resolve-conflicts", None, "ordinary"),
        (None, "bootstrap/resolve-conflicts", "delegated"),
    ],
)
def test_launch_due_tasks_reloads_frozen_dispatch_after_reconciliation(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    cached_delegate: str | None,
    durable_delegate: str | None,
    expected_dispatch: str,
) -> None:
    """The post-reconciliation period ticket, not scan cache, owns routing."""
    _write_delegating_template(repo, "delegate-check")
    cfg = load_config(repo)
    scan = scan_due(
        cfg, now=datetime(2026, 4, 22, 10, 0, 0), allow_interactive=True
    )
    task = next(item for item in scan.due if item.template == "delegate-check")
    task.delegate = cached_delegate
    current = Ticket.read(task.ref.ticket_path)
    if durable_delegate is None:
        current.frontmatter.pop("delegate")
    else:
        current.frontmatter["delegate"] = durable_delegate
    current.write(task.ref.ticket_path)
    dispatches: list[str] = []

    def fake_ordinary_launch(*args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        dispatches.append("ordinary")

    def fake_delegated_launch(*args, **kwargs):  # type: ignore[no-untyped-def]
        dispatches.append("delegated")
        return recurring_cmd.DelegatedRunResult(0, "done")

    _patch_recurring_command_launch(monkeypatch, repo, fake_ordinary_launch)
    monkeypatch.setattr(recurring_cmd, "_run_delegated_task", fake_delegated_launch)
    monkeypatch.setattr(
        recurring_cmd,
        "_stop_if_unfinished_after_launch",
        lambda *args, **kwargs: None,
    )
    record = recurring_cmd.RunRecord(started=datetime(2026, 4, 22, 10, 0, 0))

    result = recurring_cmd._launch_due_tasks(
        cfg,
        [task],
        record,
        force=False,
        interactive=True,
        agent_override=None,
        control_remote_expected=False,
    )

    assert result == 0
    assert dispatches == [expected_dispatch]
    assert task.delegate == durable_delegate


def test_launch_due_tasks_skips_a_later_period_reaped_by_an_earlier_child(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A child teardown may remove a later admitted path without aborting."""
    cfg = load_config(repo)
    now = datetime(2026, 4, 22, 10, 0, 0)
    refs: list[TaskRef] = []
    due: list[DueTask] = []
    for name in ("first-check", "later-check"):
        created = create_task(
            cfg=cfg,
            title=name,
            workflow_name="direct/body",
            contexts=[],
            owner="marc",
            assignee="claude",
            watchers=[],
            status="active",
            slug_override=f"recurring/{name}",
            force_directory=True,
        )
        ref = next(
            item for item in list_tasks(cfg) if item.id_slug == created["slug"]
        )
        refs.append(ref)
        due.append(
            DueTask(
                template=name,
                ref=ref,
                last_fire=now,
                created=False,
                status="active",
            )
        )

    launches: list[str] = []

    def fake_ordinary_launch(task: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        launches.append(task)
        if task == refs[0].id_slug:
            refs[1].ticket_path.unlink()

    _patch_recurring_command_launch(monkeypatch, repo, fake_ordinary_launch)
    monkeypatch.setattr(
        recurring_cmd,
        "_stop_if_unfinished_after_launch",
        lambda *args, **kwargs: None,
    )
    record = recurring_cmd.RunRecord(started=now)

    result = recurring_cmd._launch_due_tasks(
        cfg,
        due,
        record,
        force=False,
        interactive=True,
        agent_override=None,
        control_remote_expected=False,
    )

    assert result == 0
    assert launches == [refs[0].id_slug]
    assert any(
        "later-check changed after sweep admission" in note for note in record.notes
    )


def test_script_backed_delegate_is_rejected_before_period_creation(
    repo: Path,
) -> None:
    """A bootstrap script is already deterministic; admitting it as an agent
    delegate would create a period before launch returns through script mode.
    """
    _write(
        repo / "bootstrap" / "scripted" / "ticket.md",
        """
        ---
        title: Scripted command
        assignee: claude
        ---

        Run deterministically.
        """,
    )
    _write(repo / "bootstrap" / "scripted" / "ticket.py", "raise SystemExit(0)\n")
    _write_delegating_template(repo, "delegate-check")
    template_path = repo / "recurring" / "delegate-check" / "ticket.md"
    template_path.write_text(
        template_path.read_text().replace(
            "bootstrap/resolve-conflicts", "bootstrap/scripted"
        )
    )

    cfg = load_config(repo)
    with pytest.raises(RecurringError, match="script-backed"):
        create_named(
            cfg, "delegate-check", now=datetime(2026, 4, 22, 10, 0, 0)
        )

    assert not any(
        ref.id_slug == "recurring/delegate-check" for ref in list_tasks(cfg)
    )


def test_bare_recurring_launches_delegate_target_directly(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The sweep services a delegating template by launching its bootstrap
    target in-process; no launch of the period task itself ever happens."""
    shutil.rmtree(repo / "recurring" / "weekly-check")
    _write_delegating_template(repo, "delegate-check")
    monkeypatch.chdir(repo)
    _allow_interactive_recurring(monkeypatch)

    launches: list[tuple[str, str | None, bool | None]] = []

    def fake_launch(task: str, **kwargs) -> str:  # type: ignore[no-untyped-def]
        launches.append(
            (task, kwargs.get("agent_override"), kwargs.get("launch_context"))
        )
        kwargs["before_spawn"]()
        kwargs["revalidate_before_spawn"]()
        return "done"

    monkeypatch.setattr("coga.commands.launch.launch_with_before_spawn", fake_launch)

    def capture_slack(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        class R:
            status_code = 200
            text = "ok"

        return R()

    monkeypatch.setattr("coga.notification.slack.requests.post", capture_slack)

    result = CliRunner().invoke(app, ["recurring"])

    assert result.exit_code == 0, result.output
    assert launches == [("bootstrap/resolve-conflicts", None, "recurring")]
    ticket = Ticket.read(
        repo / "tasks" / "recurring" / "delegate-check" / "ticket.md"
    )
    assert ticket.status == "done"


def test_direct_launch_routes_frozen_recurring_delegate(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ordinary `coga launch` recognizes a materialized delegate instead of
    starting the obsolete wrapper task session, even after its template moves.
    """
    _write_delegating_template(repo, "delegate-check")
    monkeypatch.chdir(repo)
    cfg = load_config(repo)
    outcome = create_named(
        cfg, "delegate-check", now=datetime(2026, 4, 22, 10, 0, 0)
    )
    (repo / "recurring" / "delegate-check" / "ticket.md").unlink()
    launches: list[str] = []

    def fake_launch(task: str, **kwargs) -> str:  # type: ignore[no-untyped-def]
        launches.append(task)
        kwargs["before_spawn"]()
        kwargs["revalidate_before_spawn"]()
        return "done"

    monkeypatch.setattr("coga.commands.launch.launch_with_before_spawn", fake_launch)
    monkeypatch.setattr(recurring_cmd, "run_autofix", lambda *args, **kwargs: 0)

    result = CliRunner().invoke(app, ["launch", outcome.ref.id_slug])

    assert result.exit_code == 0, result.output
    assert launches == ["bootstrap/resolve-conflicts"]
    assert Ticket.read(outcome.ref.ticket_path).status == "done"


def test_direct_launch_reactivates_a_paused_delegated_period(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Typing ``coga launch`` remains the readiness signal for delegation."""
    _write_delegating_template(repo, "delegate-check")
    monkeypatch.chdir(repo)
    cfg = load_config(repo)
    outcome = create_named(
        cfg, "delegate-check", now=datetime(2026, 4, 22, 10, 0, 0)
    )
    paused = Ticket.read(outcome.ref.ticket_path)
    paused.frontmatter["status"] = "paused"
    paused.write(outcome.ref.ticket_path)

    def fake_launch(task: str, **kwargs) -> str:  # type: ignore[no-untyped-def]
        kwargs["before_spawn"]()
        kwargs["revalidate_before_spawn"]()
        return "done"

    monkeypatch.setattr(
        "coga.commands.launch.launch_with_before_spawn", fake_launch
    )
    monkeypatch.setattr(recurring_cmd, "run_autofix", lambda *args, **kwargs: 0)

    result = CliRunner().invoke(app, ["launch", outcome.ref.id_slug])

    assert result.exit_code == 0, result.output
    assert Ticket.read(outcome.ref.ticket_path).status == "done"


def test_sweep_records_delegated_timeout_as_timed_out(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A continue-on-timeout sweep keeps exit zero but does not erase the
    watchdog classification in its durable run record.
    """
    shutil.rmtree(repo / "recurring" / "weekly-check")
    _write_delegating_template(repo, "delegate-check")
    monkeypatch.chdir(repo)
    _allow_interactive_recurring(monkeypatch)
    records = []

    def fake_launch(task: str, **kwargs) -> str:  # type: ignore[no-untyped-def]
        kwargs["before_spawn"]()
        kwargs["revalidate_before_spawn"]()
        return "timeout"

    monkeypatch.setattr("coga.commands.launch.launch_with_before_spawn", fake_launch)
    monkeypatch.setattr(
        recurring_cmd,
        "run_autofix",
        lambda cfg, record, **kwargs: records.append(record) or 0,
    )

    result = CliRunner().invoke(app, ["recurring"])

    assert result.exit_code == 0, result.output
    assert records[-1].outcomes[0].result == "timed-out"
    assert records[-1].outcomes[0].exit_code is None
    ticket = Ticket.read(
        repo / "tasks" / "recurring" / "delegate-check" / "ticket.md"
    )
    assert ticket.status == "paused"


def test_named_recurring_delegate_timeout_fails_and_remains_retryable(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The one-task entrypoint must not turn a watchdog kill into success or
    park the task; a second explicit launch can resume the in-progress period.
    """
    shutil.rmtree(repo / "recurring" / "weekly-check")
    _write_delegating_template(repo, "delegate-check")
    monkeypatch.chdir(repo)
    _allow_interactive_recurring(monkeypatch)
    outcomes = iter(("timeout", "done"))

    def fake_launch(task: str, **kwargs) -> str:  # type: ignore[no-untyped-def]
        assert task == "bootstrap/resolve-conflicts"
        assert kwargs.get("return_timeout") is True
        kwargs["before_spawn"]()
        kwargs["revalidate_before_spawn"]()
        return next(outcomes)

    monkeypatch.setattr("coga.commands.launch.launch_with_before_spawn", fake_launch)

    def capture_slack(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        class R:
            status_code = 200
            text = "ok"

        return R()

    monkeypatch.setattr("coga.notification.slack.requests.post", capture_slack)

    first = CliRunner().invoke(app, ["recurring", "launch", "delegate-check"])
    assert first.exit_code == _TIMEOUT_EXIT_CODE, first.output
    ticket_path = (
        repo / "tasks" / "recurring" / "delegate-check" / "ticket.md"
    )
    assert Ticket.read(ticket_path).status == "in_progress"

    retry = CliRunner().invoke(app, ["recurring", "launch", "delegate-check"])
    assert retry.exit_code == 0, retry.output
    assert Ticket.read(ticket_path).status == "done"


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


def test_scan_due_rejects_non_five_field_year_scoped_schedule(
    repo: Path, capsys
) -> None:
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
    assert [task.template for task in scan.tasks] == ["weekly-check"]
    assert scan.errors == [
        (
            "year-scoped",
            "`schedule` is not a valid cron expression: expected exactly "
            "5 fields, got 7",
        )
    ]
    assert "skipping year-scoped" in capsys.readouterr().err


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

    A leftover `mode:` key — any value — neither dispatches nor fails.
    """
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
    """Unattended scans skip agent templates before creating.

    The error lands in
    `DueScan.errors`, so `coga recurring` can post its scan-error summary and
    still continue to other due templates. A `ticket.py` template bypasses the
    TTY gate, so it still creates while the agent template is skipped.
    """
    _write_recurring(
        repo,
        "z-script-check",
        """
        ---
        schedule: "0 9 * * *"
        title: "Script check"
        owner: marc
        ---

        ## Description

        Run a deterministic half.
        """,
    )
    _write_recurring_script(repo, "z-script-check")
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
    """A template with no `ticket.py` is an agent run."""
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
    assert read_serviced_period(
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
    assert read_serviced_period(
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

        [notification.slack]
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
    monkeypatch.setattr(
        "coga.commands.launch.launch_recurring_period", lambda *a, **k: None
    )
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
    assert read_serviced_period(
        dream_repo / "recurring" / "dream" / "ticket.md"
    ) is not None


def test_recurring_launch_syncs_period_task_and_high_water(
    git_repo, monkeypatch
) -> None:
    """The git control branch gets the task dir and period high-water together.

    Dream later deletes done recurring period tickets. That deletion is
    idempotent only if another checkout can still see the serviced-period log
    record after the task dir is gone.
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
    monkeypatch.setattr(
        "coga.commands.launch.launch_recurring_period", lambda *a, **k: None
    )
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
    assert _control_serviced_period(git_repo, "weekly-check") == "2026-W24"
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
    ) == coga_git.STALE_CONTROL_EXIT_CODE
    assert list_tasks(cfg) == []
    captured = capsys.readouterr()
    assert "Recurring scan skipped" in captured.err
    assert "simulated rebase conflict" in captured.err
    # The gate is about to fail loud with the reason, so the best-effort
    # stderr note is suppressed — one conflict, one report.
    assert "pre-scan catch-up skipped" not in captured.err


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
    ) == coga_git.STALE_CONTROL_EXIT_CODE
    assert "[git].enabled = false" in capsys.readouterr().err


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
    _patch_recurring_command_launch(monkeypatch, coga_os, fake_launch)

    assert recurring_cmd.run_recurring_scan(cfg) == 0
    assert launched == ["recurring/weekly-check"]
    assert _control_serviced_period(git_repo, "weekly-check") == "2026-W18"


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
    monkeypatch.setattr(
        "coga.commands.launch.launch_recurring_period", lambda *a, **k: None
    )
    result = CliRunner().invoke(app, ["recurring", "launch", "weekly-check"])

    assert result.exit_code == 0, result.output
    assert "not fast-forwarded" not in result.output
    cfg = load_config(coga_os)
    ref = list_tasks(cfg)[0]
    assert git_repo.origin_tracks(f"coga/tasks/{ref.id_slug}/ticket.md")
    # The pre-create catch-up (or post-landing rebase) leaves the checkout at
    # origin's tip, competing commit included.
    assert (git_repo.root / "notes.md").is_file()


def test_feature_branch_landing_preserves_remote_ledger_entries(git_repo) -> None:
    """The retained low-level landing path union-merges a stale branch's log.

    Normal recurring entry points now refuse this checkout, but repos
    mid-upgrade may already have feature-branch period state to land.
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

    cfg = load_config(coga_os)
    outcome = create_named(cfg, "weekly-check", now=datetime(2026, 6, 8, 10, 5))
    recurring_cmd._sync_recurring_create(
        cfg,
        "weekly-check",
        outcome.ref,
        respect_handled_period=False,
    )
    ref = outcome.ref
    # The repo-global log is union-merged across branches: the concurrent
    # remote append and this run's create line both survive on control.
    ledger = git_repo.git("show", "main:coga/log.md", cwd=git_repo.origin)
    assert remote_line in ledger
    assert f"created {ref.id_slug}" in ledger
    assert git_repo.origin_tracks(f"coga/tasks/{ref.id_slug}/ticket.md")


def test_feature_branch_landing_does_not_publish_feature_only_template_log(
    git_repo,
) -> None:
    """The retained landing path does not turn a feature template into main.

    Normal recurring entry points now refuse this checkout; this pins the
    low-level migration behavior until its later cleanup.
    """
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

    cfg = load_config(coga_os)
    outcome = create_named(cfg, "new-weekly", now=datetime(2026, 6, 8, 10, 5))
    recurring_cmd._sync_recurring_create(
        cfg,
        "new-weekly",
        outcome.ref,
        respect_handled_period=False,
    )
    ref = outcome.ref
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

    monkeypatch.setattr(
        "coga.commands.launch.launch_recurring_period", lambda *a, **k: None
    )
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
        "coga.commands.launch.launch_recurring_period",
        lambda *a, **k: launch_calls.append(a),
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

    monkeypatch.setattr(
        "coga.commands.launch.launch_recurring_period", lambda *a, **k: None
    )
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


def test_feature_branch_landing_preserves_midflight_remote_ledger_race(
    git_repo, monkeypatch
) -> None:
    """The retained landing path preserves a peer append during publication.

    Normal recurring entry points no longer reach feature-branch landing, but
    already-created state in a repo mid-upgrade can still use this path.
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
    cfg = load_config(coga_os)
    outcome = create_named(cfg, "weekly-check", now=datetime(2026, 6, 8, 10, 5))
    recurring_cmd._sync_recurring_create(
        cfg,
        "weekly-check",
        outcome.ref,
        respect_handled_period=False,
    )
    ref = outcome.ref
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
        "\nstate\n\nremote_cursor: kept\n"
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
            _push_competing_serviced_period(git_repo, "weekly-check", "2026-W24")
            raced = True
        return committed

    monkeypatch.setattr("coga.recurring_runner.git._commit_paths", racing_commit)

    recurring_cmd._sync_recurring_create(cfg, "weekly-check", outcome.ref)

    # The handled control state (its cursor and W24 high-water) lives in the
    # template ticket's blackboard region; the stale checkout adopts it.
    ticket_rel = "coga/recurring/weekly-check/ticket.md"
    control_ticket = git_repo.git("show", f"main:{ticket_rel}", cwd=git_repo.origin)
    assert "remote_cursor: kept" in control_ticket
    assert _control_serviced_period(git_repo, "weekly-check") == "2026-W24"
    local_template = coga_os / "recurring" / "weekly-check" / "ticket.md"
    assert "remote_cursor: kept" in read_blackboard(local_template)
    assert read_serviced_period(local_template) == "2026-W24"
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
    handled_region = "\nstate\n"
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
            _push_competing_serviced_period(git_repo, "weekly-check", "2026-W24")

    monkeypatch.setattr(recurring_cmd, "_fetch_control_branch", racing_fetch)

    recurring_cmd._sync_recurring_create(cfg, "weekly-check", outcome.ref)

    assert "sync failed" not in capsys.readouterr().err
    assert not outcome.ref.path.exists()
    assert not git_repo.origin_tracks(f"coga/tasks/{outcome.ref.id_slug}/ticket.md")
    assert _control_serviced_period(git_repo, "weekly-check") == "2026-W24"
    local_template = coga_os / "recurring" / "weekly-check" / "ticket.md"
    assert read_serviced_period(local_template) == "2026-W24"
    assert git_repo.git("status", "--porcelain") == ""


def test_named_launch_replaces_a_done_task_control_still_tracks(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An on-demand launch must land the task that replaces a stale `done` run.

    Regression: `run_recurring_named` left `respect_existing_task` at its
    default, so control still tracking the prior period's `done` task read as
    "this firing was already handled" — `run_delete_task` had removed it from
    the working tree only. The landing returned early, the unwind restored the
    committed `done` ticket over the freshly created `active` one, and the
    launch reported "is done; not launching" *after* the ledger recorded the
    new period as serviced, so the scheduled sweep skipped it too. The sweep
    disables the guard for the same case (`_broadcast_scan`); every named
    spelling — `coga autoclose`, `coga dream`, `coga skill-update` — rides
    this path.
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
        owner: marc
        assignee: claude
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _seed_global_log(git_repo)
    git_repo.git("add", "coga/contexts", "coga/recurring")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    cfg = load_config(coga_os)
    first = create_named(cfg, "weekly-check", now=datetime(2026, 6, 8, 10, 5))
    recurring_cmd._sync_recurring_create(
        cfg, "weekly-check", first.ref, respect_handled_period=False
    )
    task_rel = f"coga/tasks/{first.ref.id_slug}/ticket.md"
    assert git_repo.origin_tracks(task_rel)
    assert _control_serviced_period(git_repo, "weekly-check") == "2026-W24"

    # The prior period finished but Dream never reaped it, so control keeps
    # tracking a `done` task at the stable path.
    ticket = Ticket.read(first.ref.ticket_path)
    ticket.frontmatter["status"] = "done"
    ticket.frontmatter.pop("step", None)
    ticket.write(first.ref.ticket_path)
    git_repo.git("add", "--", task_rel)
    git_repo.git("commit", "-m", "weekly-check done")
    git_repo.git("push", "origin", "main")

    launched: list[str] = []
    _allow_interactive_recurring(monkeypatch)
    _freeze_recurring_now(monkeypatch, datetime(2026, 6, 15, 10, 5))
    monkeypatch.setattr(
        "coga.commands.launch.launch_recurring_period",
        lambda slug, **kwargs: launched.append(slug),
    )

    assert recurring_cmd.run_recurring_named(cfg, "weekly-check") == 0

    assert launched == [first.ref.id_slug]
    assert Ticket.read(first.ref.ticket_path).status == "active"
    assert _control_serviced_period(git_repo, "weekly-check") == "2026-W25"
    control_ticket = git_repo.git(
        "show", f"main:{task_rel}", cwd=git_repo.origin
    )
    assert "status: active" in control_ticket


def test_named_replacement_does_not_launch_a_concurrent_generation(
    git_repo, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Only the exact stale ``done`` generation may be replaced on control."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        owner: marc
        assignee: claude
        ---

        ## Description

        Run the weekly check.
        """,
    )
    _seed_global_log(git_repo)
    git_repo.git("add", "coga/contexts", "coga/recurring")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")

    cfg = load_config(coga_os)
    first = create_named(cfg, "weekly-check", now=datetime(2026, 6, 8, 10, 5))
    recurring_cmd._sync_recurring_create(
        cfg, "weekly-check", first.ref, respect_handled_period=False
    )
    task_rel = f"coga/tasks/{first.ref.id_slug}/ticket.md"

    stale_done = Ticket.read(first.ref.ticket_path)
    stale_done.frontmatter["status"] = "done"
    stale_done.frontmatter.pop("step", None)
    stale_done.write(first.ref.ticket_path)
    git_repo.git("add", "--", task_rel)
    git_repo.git("commit", "-m", "weekly-check done")
    git_repo.git("push", "origin", "main")

    winner = Ticket.read(first.ref.ticket_path)
    winner.frontmatter["status"] = "active"
    winner.frontmatter["period_generation"] = "concurrent-generation"
    winner.body += "\nConcurrent replacement.\n"

    real_fetch = recurring_cmd._fetch_control_branch
    fetch_calls = 0

    def racing_fetch(cfg_arg, root):
        nonlocal fetch_calls
        fetch_calls += 1
        if fetch_calls == 2:
            git_repo.push_competing_commit(task_rel, winner.render())
            _push_competing_serviced_period(git_repo, "weekly-check", "2026-W25")
        real_fetch(cfg_arg, root)

    monkeypatch.setattr(recurring_cmd, "_fetch_control_branch", racing_fetch)
    launched: list[str] = []
    _allow_interactive_recurring(monkeypatch)
    _freeze_recurring_now(monkeypatch, datetime(2026, 6, 15, 10, 5))
    monkeypatch.setattr(
        "coga.commands.launch.launch_recurring_period",
        lambda slug, **kwargs: launched.append(slug),
    )

    assert recurring_cmd.run_recurring_named(cfg, "weekly-check") == 0

    assert launched == []
    assert "changed on the control branch during recurring admission" in (
        capsys.readouterr().out
    )
    local = Ticket.read(first.ref.ticket_path)
    assert local.frontmatter["period_generation"] == "concurrent-generation"
    assert "Concurrent replacement." in local.body
    control = git_repo.git("show", f"main:{task_rel}", cwd=git_repo.origin)
    assert "period_generation: concurrent-generation" in control
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

    monkeypatch.setattr(
        "coga.commands.launch.launch_recurring_period", lambda *a, **k: None
    )
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
    monkeypatch.setattr(
        "coga.commands.launch.launch_recurring_period", lambda *a, **k: None
    )
    CliRunner().invoke(app, ["recurring", "launch", "dream"])

    cfg = load_config(dream_repo)
    refs = list_tasks(cfg)
    ticket = Ticket.read(refs[0].path / "ticket.md")
    assert ticket.workflow["name"] == "direct/body"
    assert ticket.assignee == "claude"


def test_recurring_launch_is_idempotent(
    dream_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "coga.commands.launch.launch_recurring_period", lambda *a, **k: None
    )
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


def test_forced_recurring_run_refuses_canceled_period(repo: Path) -> None:
    cfg = load_config(repo)
    now = datetime(2026, 4, 22, 10, 0, 0)
    period = scan_due(cfg, now=now)
    ticket_path = period.tasks[0].ref.path / "ticket.md"
    ticket = Ticket.read(ticket_path)
    ticket.frontmatter["status"] = "canceled"
    ticket.frontmatter.pop("step", None)
    ticket.write(ticket_path)
    forced = scan_due(cfg, now=now, force=True)

    with pytest.raises(
        recurring_cmd.RecurringError,
        match="task is canceled and cannot be reactivated",
    ):
        recurring_cmd._prepare_forced_launch(cfg, forced.forced[0])

    assert Ticket.read(ticket_path).status == "canceled"


def test_forced_recurring_scan_reports_canceled_and_continues(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cfg = load_config(repo)
    canceled = SimpleNamespace(
        template="canceled-period",
        ref=SimpleNamespace(
            id_slug="canceled-period", ticket_path=Path("no-such-ticket.md")
        ),
        delegate=None,
    )
    later = SimpleNamespace(
        template="later-period",
        ref=SimpleNamespace(
            id_slug="later-period", ticket_path=Path("no-such-ticket.md")
        ),
        delegate=None,
    )
    scan = SimpleNamespace(forced=[canceled, later], due=[], tasks=[], errors=[])
    launched: list[str] = []

    monkeypatch.setattr(
        recurring_cmd,
        "_sync_control_checkout_ahead",
        lambda *args, **kwargs: recurring_cmd._ControlCatchup(fresh=True, reason=""),
    )
    monkeypatch.setattr(recurring_cmd, "scan_due", lambda *args, **kwargs: scan)
    monkeypatch.setattr(recurring_cmd, "_broadcast_scan", lambda *args, **kwargs: None)
    monkeypatch.setattr(recurring_cmd, "_print_table", lambda *args, **kwargs: None)

    def prepare(task_cfg, task):  # type: ignore[no-untyped-def]
        if task is canceled:
            raise recurring_cmd.RecurringError(
                "cannot force-run canceled-period: its task is canceled"
            )

    monkeypatch.setattr(recurring_cmd, "_prepare_forced_launch", prepare)
    active_lease = PeriodLease(
        Ticket(frontmatter={"status": "active"}, body="").render().encode(),
        "generation-1",
    )
    monkeypatch.setattr(
        recurring_cmd, "_local_period_lease", lambda *args: active_lease
    )
    monkeypatch.setattr(
        recurring_cmd,
        "read_ticket",
        lambda ref: SimpleNamespace(status="active"),
    )
    monkeypatch.setattr(
        recurring_cmd, "frozen_task_delegate", lambda ref, ticket: None
    )
    monkeypatch.setattr(
        "coga.commands.launch.launch_recurring_period",
        lambda slug, **kwargs: (
            launched.append(slug),
            RecurringPeriodLaunchResult(None, active_lease, False),
        )[1],
    )
    monkeypatch.setattr(
        recurring_cmd,
        "_stop_if_unfinished_after_launch",
        lambda *args, **kwargs: None,
    )

    result = recurring_cmd.run_recurring_scan(cfg, force=True)

    assert result == 2
    assert launched == ["later-period"]
    assert "cannot force-run canceled-period" in capsys.readouterr().err


def test_forced_recurring_scan_prepares_then_launches_task(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Forced runs prepare, then hand every template to one `launch` call."""
    cfg = load_config(repo)
    task = SimpleNamespace(
        template="script-check",
        ref=SimpleNamespace(
            id_slug="recurring/script-check", ticket_path=Path("no-such-ticket.md")
        ),
        delegate=None,
    )
    prepared: list[object] = []
    launched: list[str] = []

    monkeypatch.setattr(
        recurring_cmd,
        "_sync_control_checkout_ahead",
        lambda *args, **kwargs: recurring_cmd._ControlCatchup(fresh=True, reason=""),
    )
    monkeypatch.setattr(
        recurring_cmd,
        "scan_due",
        lambda *args, **kwargs: SimpleNamespace(
            forced=[task], due=[], tasks=[], errors=[]
        ),
    )
    monkeypatch.setattr(recurring_cmd, "_broadcast_scan", lambda *args, **kwargs: None)
    monkeypatch.setattr(recurring_cmd, "_print_table", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        recurring_cmd,
        "_prepare_forced_launch",
        lambda task_cfg, due_task: prepared.append(due_task),
    )
    active_lease = PeriodLease(
        Ticket(frontmatter={"status": "active"}, body="").render().encode(),
        "generation-1",
    )
    monkeypatch.setattr(
        recurring_cmd, "_local_period_lease", lambda *args: active_lease
    )
    monkeypatch.setattr(
        recurring_cmd,
        "read_ticket",
        lambda ref: SimpleNamespace(status="active"),
    )
    monkeypatch.setattr(
        recurring_cmd, "frozen_task_delegate", lambda ref, ticket: None
    )
    monkeypatch.setattr(
        "coga.commands.launch.launch_recurring_period",
        lambda slug, **kwargs: (
            launched.append(slug),
            RecurringPeriodLaunchResult(None, active_lease, False),
        )[1],
    )
    monkeypatch.setattr(
        recurring_cmd,
        "_stop_if_unfinished_after_launch",
        lambda *args, **kwargs: None,
    )

    assert recurring_cmd.run_recurring_scan(cfg, force=True) == 0
    assert prepared == [task]
    assert launched == ["recurring/script-check"]


def test_recurring_scan_returns_failed_script_exit_without_unwinding(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed `ticket.py` stops the sweep as a return, not a process abort.

    `coga launch` raises `SystemExit` for a non-zero deterministic phase. The
    sweep has to turn that back into a return code, or the command never
    reaches its exit-boundary git sync — and the tasks behind it lose the
    ordinary refusal path they had under the old recipe dispatch.
    """
    cfg = load_config(repo)
    first = SimpleNamespace(
        template="failing",
        ref=SimpleNamespace(
            id_slug="recurring/failing", ticket_path=Path("no-such-ticket.md")
        ),
        delegate=None,
    )
    second = SimpleNamespace(
        template="later",
        ref=SimpleNamespace(
            id_slug="recurring/later", ticket_path=Path("no-such-ticket.md")
        ),
        delegate=None,
    )
    launched: list[str] = []

    def failing_launch(slug: str, **kwargs: object) -> str | None:
        launched.append(slug)
        if slug == "recurring/failing":
            raise SystemExit(17)
        return None

    monkeypatch.setattr(
        recurring_cmd,
        "_sync_control_checkout_ahead",
        lambda *args, **kwargs: recurring_cmd._ControlCatchup(fresh=True, reason=""),
    )
    monkeypatch.setattr(
        recurring_cmd,
        "scan_due",
        lambda *args, **kwargs: SimpleNamespace(
            forced=[], due=[first, second], tasks=[], errors=[]
        ),
    )
    monkeypatch.setattr(recurring_cmd, "_broadcast_scan", lambda *args, **kwargs: None)
    monkeypatch.setattr(recurring_cmd, "_print_table", lambda *args, **kwargs: None)
    active_lease = PeriodLease(
        Ticket(frontmatter={"status": "active"}, body="").render().encode(),
        "generation-1",
    )
    monkeypatch.setattr(
        recurring_cmd, "_local_period_lease", lambda *args: active_lease
    )
    monkeypatch.setattr(
        recurring_cmd,
        "read_ticket",
        lambda ref: SimpleNamespace(status="active"),
    )
    monkeypatch.setattr(
        recurring_cmd, "frozen_task_delegate", lambda ref, ticket: None
    )
    monkeypatch.setattr(
        "coga.commands.launch.launch_recurring_period", failing_launch
    )
    monkeypatch.setattr(
        recurring_cmd,
        "_stop_if_unfinished_after_launch",
        lambda *args, **kwargs: None,
    )

    assert recurring_cmd.run_recurring_scan(cfg) == 17
    assert launched == ["recurring/failing"]


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
    # Rewrite the template blackboard region to just the cursor. This used to
    # clobber the W17 high-water the first create wrote; the ledger lives in
    # the repo-global log now, so nothing a blackboard rewrite can reach.
    _seed_template_blackboard(repo, "weekly-check", "cursor: new\n")

    forced = scan_due(cfg, now=datetime(2026, 4, 29, 10, 0, 0), force=True)

    assert forced.forced[0].ref == ref
    # Still W17: the scan discovered the finished task but has not recorded the
    # forced W18 rerun — that happens when the launch loop reaches it.
    assert (
        read_serviced_period(repo / "recurring" / "weekly-check" / "ticket.md")
        == "2026-W17"
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
    _seed_template_blackboard(repo, "weekly-check", "cursor: new\n")
    _seed_serviced_period(repo, "weekly-check", "2026-W17")

    forced = scan_due(cfg, now=datetime(2026, 4, 29, 10, 0, 0), force=True)

    assert forced.forced[0].ref == ref
    assert forced.forced[0].status == "active"
    assert read_serviced_period(
        repo / "recurring" / "weekly-check" / "ticket.md"
    ) == "2026-W17"
    log = "\n".join(task_log_lines(cfg, "recurring/weekly-check"))
    assert "reused recurring/weekly-check for 2026-W18" not in log
    assert '"cursor": "old"' in (ref.path / ".state-snapshot.json").read_text()


def test_scan_due_force_recreates_serviced_deleted_period(repo: Path) -> None:
    """`--force` bypasses the serviced-period ledger: a period that already
    ran and had its task dir deleted is re-created as a real run."""
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
    _seed_agent_workflow(coga_os)
    _write_recurring_agent(
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
    _allow_interactive_recurring(monkeypatch)
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
    _seed_agent_workflow(coga_os)
    _write_recurring_agent(
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
    _allow_interactive_recurring(monkeypatch)
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
    assert _control_serviced_period(git_repo, "weekly-check") == "2026-W18"


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
    _seed_template_blackboard(coga_os, "weekly-check", "cursor: new\n")
    _seed_serviced_period(coga_os, "weekly-check", "2026-W17")

    launched: list[str] = []

    def fake_launch(slug: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        launched.append(slug)
        _finish_period_task(coga_os, slug)

    _patch_recurring_command_launch(monkeypatch, coga_os, fake_launch)
    _allow_interactive_recurring(monkeypatch)
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
    assert _control_serviced_period(git_repo, "weekly-check") == "2026-W18"
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
    _allow_interactive_recurring(monkeypatch)
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
    _seed_template_blackboard(coga_os, "weekly-check", "cursor: new\n")
    _seed_serviced_period(coga_os, "weekly-check", "2026-W17")

    launched: list[str] = []

    def fake_launch(slug: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        launched.append(slug)
        _finish_period_task(coga_os, slug)

    _patch_recurring_command_launch(monkeypatch, coga_os, fake_launch)
    _allow_interactive_recurring(monkeypatch)
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
    _seed_agent_workflow(coga_os)
    _write_recurring_agent(
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
        _finish_period_task(coga_os, slug)

    _patch_recurring_command_launch(monkeypatch, coga_os, fake_launch)
    _freeze_recurring_now(monkeypatch, datetime(2026, 4, 29, 10, 0, 0))
    _allow_interactive_recurring(monkeypatch)
    monkeypatch.chdir(coga_os)

    result = CliRunner().invoke(app, ["recurring", "--force"])

    assert result.exit_code == 0, result.output
    assert launched == [remote.ref.id_slug]
    control_template = git_repo.git(
        "show",
        "main:coga/recurring/weekly-check/ticket.md",
        cwd=git_repo.origin,
    )
    assert _control_serviced_period(git_repo, "weekly-check") == "2026-W17"


def test_recurring_force_reconciles_existing_tasks_before_launch_order(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A control-branch orphan must resume before stale local fresh work."""
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _seed_agent_workflow(coga_os)
    for name in ("aaa-first", "zzz-live"):
        _write_recurring_agent(
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
    # One ledger snapshot for the whole sweep, as `_broadcast_scan` does: the
    # log is shared, so the first sync publishes records for templates that
    # have not synced yet.
    control_ledger: dict[str, str] = {}
    for task in first_scan.tasks:
        assert task.ref is not None
        recurring_cmd._sync_recurring_create(
            cfg, task.template, task.ref, control_ledger=control_ledger
        )
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
        _finish_period_task(coga_os, slug)

    _patch_recurring_command_launch(monkeypatch, coga_os, fake_launch)
    _freeze_recurring_now(monkeypatch, datetime(2026, 4, 29, 10, 0, 0))
    _allow_interactive_recurring(monkeypatch)
    monkeypatch.chdir(coga_os)

    result = CliRunner().invoke(app, ["recurring", "--force"])

    assert result.exit_code == 0, result.output
    assert launched == [live.ref.id_slug, "recurring/aaa-first"]
    assert read_blackboard(live.ref.path / "ticket.md") == "\nremote live state\n"


def test_recurring_force_does_not_service_unreached_existing_task(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A forced done task is serviced only once the launch loop reaches it."""
    _seed_agent_workflow(repo)
    _write_recurring_agent(
        repo, "aaa-first", schedule="0 9 * * 1", title="First check"
    )
    _write_recurring_agent(
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
    _allow_interactive_recurring(monkeypatch)
    monkeypatch.chdir(repo)

    result = CliRunner().invoke(app, ["recurring", "--force"])

    assert result.exit_code == 1
    assert launched == ["recurring/aaa-first"]
    assert read_serviced_period(
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
    _allow_interactive_recurring(monkeypatch)
    _freeze_recurring_now(monkeypatch, datetime(2026, 4, 29, 10, 0, 0))
    monkeypatch.chdir(coga_os)

    result = CliRunner().invoke(app, ["recurring", "--force"])

    assert result.exit_code == 0, result.output
    assert launched == [ref.id_slug]
    assert "skip (done)" not in result.output
    assert "→ launch" in result.output
    assert _control_serviced_period(git_repo, "weekly-check") == "2026-W18"


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
        expected_period_lease: PeriodLease,
        control_remote_expected: bool,
        agent_override: str | None,
        prompt_report: bool,
        idle_timeout: float | None = None,
        max_session: float | None = None,
        return_timeout: bool = False,
        launch_context: str = "attended",
        script_failure_important: bool = False,
    ) -> None:
        assert return_timeout is False
        assert idle_timeout == 900.0
        assert max_session is None
        # On-demand named launches are automatic queue launches too.
        assert launch_context == "recurring"
        assert script_failure_important is True
        assert expected_period_lease.ticket_bytes is not None
        assert control_remote_expected is False
        ticket = Ticket.read(dream_repo / "tasks" / task / "ticket.md")
        assert ticket.status == "active"
        calls.append(task)

    monkeypatch.setattr("coga.commands.launch.launch_recurring_period", fake_launch)

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
        "coga.commands.launch.launch_recurring_period",
        lambda task, **kwargs: seen.append(kwargs.get("agent_override")),
    )

    result = CliRunner().invoke(app, args)

    assert result.exit_code == 0, result.output
    assert seen == ["codex"]
    ticket = Ticket.read(dream_repo / "tasks" / "recurring" / "dream" / "ticket.md")
    assert ticket.assignee == "claude"


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

    monkeypatch.setattr("coga.commands.launch.launch_recurring_period", fake_launch)

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
        "coga.commands.launch.launch_recurring_period",
        lambda task, **k: calls.append(task),
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
        "coga.commands.launch.launch_recurring_period",
        lambda task, **k: calls.append(task),
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
        "coga.commands.launch.launch_recurring_period",
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
    """The sweep threads `--agent` into agent-backed period tasks."""
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
    """Unattended recurring skips agent work and runs a later script."""
    _write_recurring(
        repo,
        "z-script-check",
        """
        ---
        schedule: "* * * * *"
        title: "Script check"
        owner: marc
        ---

        ## Description

        Run the deterministic half.
        """,
    )
    _write_recurring_script(repo, "z-script-check")
    monkeypatch.chdir(repo)
    monkeypatch.setattr(
        "coga.recurring_runner._interactive_stdio_has_tty", lambda: False
    )
    launched: list[str] = []
    slack_msgs: list[str] = []

    def capture_slack(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        slack_msgs.append(json["text"])

        class R:
            status_code = 200
            text = "ok"

        return R()

    _patch_recurring_command_launch(
        monkeypatch, repo, lambda slug, **kwargs: launched.append(slug)
    )
    monkeypatch.setattr(
        "coga.recurring_runner._stop_if_unfinished_after_launch",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr("coga.notification.slack.requests.post", capture_slack)

    result = CliRunner().invoke(app, ["recurring"])

    assert result.exit_code == 0, result.output
    assert launched == ["recurring/z-script-check"]
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
        "z-agent-check",
        """
        ---
        schedule: "0 9 * * *"
        title: "Agent check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Agent work.
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
    assert calls == ["recurring/weekly-check", "recurring/z-agent-check"]
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
    assert "paused and continuing to next due task." in result.output

    cfg = load_config(repo)
    refs = list_tasks(cfg)
    assert {Ticket.read(ref.path / "ticket.md").status for ref in refs} == {"paused"}

    calls.clear()
    second = CliRunner().invoke(app, ["recurring"])
    assert second.exit_code == 0, second.output
    assert calls == []
    assert "No recurring tasks due." in second.output


def test_bare_recurring_refuses_to_pause_replacement_after_ordinary_agent_exit(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An old ordinary child cannot park a replacement at the stable path."""
    monkeypatch.chdir(repo)
    _allow_interactive_recurring(monkeypatch)

    def replace_during_child(task: str, **kwargs):  # type: ignore[no-untyped-def]
        del kwargs
        cfg = load_config(repo)
        ref = next(ref for ref in list_tasks(cfg) if ref.id_slug == task)
        launched = Ticket.read(ref.ticket_path)
        launched.frontmatter["status"] = "in_progress"
        launched.write(ref.ticket_path)
        launched_lease = recurring_module.local_period_lease(cfg, ref)

        replacement = Ticket.read(ref.ticket_path)
        replacement.frontmatter["status"] = "active"
        replacement.frontmatter["period_generation"] = "replacement-generation"
        replacement.body += "\nReplacement generation.\n"
        replacement.write(ref.ticket_path)
        append_log(
            cfg,
            ref.id_slug,
            "system",
            "created (status=active)",
        )
        return RecurringPeriodLaunchResult(None, launched_lease, False)

    _patch_recurring_command_launch(monkeypatch, repo, replace_during_child)

    result = CliRunner().invoke(app, ["recurring"])

    assert result.exit_code == 1
    assert isinstance(result.exception, RecurringError)
    assert "stable-path generation changed after the child exited" in str(
        result.exception
    )
    cfg = load_config(repo)
    ref = list_tasks(cfg)[0]
    assert Ticket.read(ref.ticket_path).status == "active"
    assert "Replacement generation." in ref.ticket_path.read_text()
    assert not any("→ paused" in line for line in task_log_lines(cfg, ref.id_slug))


def test_bare_recurring_refuses_to_pause_replacement_after_ticket_script_exit(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A deterministic child retains its admitted generation through teardown."""
    _write_recurring(
        repo,
        "script-check",
        """
        ---
        schedule: "0 9 * * *"
        title: Script check
        owner: marc
        ---

        ## Description

        Run deterministic work.
        """,
    )
    _write_recurring_script(repo, "script-check")
    monkeypatch.chdir(repo)
    monkeypatch.setattr(
        "coga.recurring_runner._interactive_stdio_has_tty", lambda: False
    )

    def replace_during_script(task: str, **kwargs):  # type: ignore[no-untyped-def]
        del kwargs
        cfg = load_config(repo)
        ref = next(ref for ref in list_tasks(cfg) if ref.id_slug == task)
        launched = Ticket.read(ref.ticket_path)
        launched.frontmatter["status"] = "in_progress"
        launched.write(ref.ticket_path)

        replacement = Ticket.read(ref.ticket_path)
        replacement.frontmatter["status"] = "active"
        replacement.frontmatter["period_generation"] = "replacement-generation"
        replacement.body += "\nReplacement generation.\n"
        replacement.write(ref.ticket_path)
        append_log(cfg, ref.id_slug, "system", "created (status=active)")
        return "script"

    monkeypatch.setattr(
        "coga.commands.launch._launch",
        replace_during_script,
    )

    result = CliRunner().invoke(app, ["recurring"])

    assert result.exit_code == 1
    assert isinstance(result.exception, RecurringError)
    assert "stable-path generation changed after the child exited" in str(
        result.exception
    )
    cfg = load_config(repo)
    ref = next(
        ref for ref in list_tasks(cfg) if ref.id_slug == "recurring/script-check"
    )
    assert Ticket.read(ref.ticket_path).status == "active"
    assert "Replacement generation." in ref.ticket_path.read_text()
    assert not any("→ paused" in line for line in task_log_lines(cfg, ref.id_slug))


def test_unfinished_ordinary_pause_accepts_same_generation_child_edits(
    repo: Path,
) -> None:
    """Usage/audit and blackboard writes do not masquerade as replacement."""
    cfg, ref = _in_progress_period(repo)
    launched_lease = recurring_module.local_period_lease(cfg, ref)
    current = Ticket.read(ref.ticket_path)
    current.body += "\nChild working note.\n"
    current.write(ref.ticket_path)
    append_log(cfg, ref.id_slug, "system", '{"usage_status":"unknown"}')

    recurring_cmd._stop_if_unfinished_after_launch(
        cfg,
        ref,
        expected_period_lease=launched_lease,
    )

    paused = Ticket.read(ref.ticket_path)
    assert paused.status == "paused"
    assert "Child working note." in paused.body


def test_unfinished_ordinary_pause_uses_the_newly_leased_ticket(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A same-generation edit between lookup and lease survives the pause."""
    cfg, ref = _in_progress_period(repo)
    launched_lease = recurring_module.local_period_lease(cfg, ref)
    real_local_period_lease = recurring_module.local_period_lease

    def lease_after_concurrent_edit(
        lease_cfg: Config, lease_ref: TaskRef
    ) -> PeriodLease:
        current = Ticket.read(lease_ref.ticket_path)
        if "Concurrent child note." not in current.body:
            current.body += "\nConcurrent child note.\n"
            current.write(lease_ref.ticket_path)
        return real_local_period_lease(lease_cfg, lease_ref)

    monkeypatch.setattr(
        recurring_cmd,
        "_local_period_lease",
        lease_after_concurrent_edit,
    )

    recurring_cmd._stop_if_unfinished_after_launch(
        cfg,
        ref,
        expected_period_lease=launched_lease,
    )

    paused = Ticket.read(ref.ticket_path)
    assert paused.status == "paused"
    assert "Concurrent child note." in paused.body


def _in_progress_period(repo: Path) -> tuple[Config, TaskRef]:
    cfg = load_config(repo)
    ref = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0)).tasks[0].ref
    assert ref is not None
    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(ref.ticket_path)
    return cfg, ref


def test_watchdog_timeout_uses_important_live_fallback(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, ref = _in_progress_period(repo)
    urls: list[str] = []

    def capture(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        urls.append(url)

        class Response:
            status_code = 200
            text = "ok"

        return Response()

    monkeypatch.setattr("coga.notification.slack.requests.post", capture)

    recurring_cmd._stop_if_unfinished_after_launch(cfg, ref, timed_out=True)

    assert urls == [IMPORTANT_WEBHOOK]
    assert Ticket.read(ref.ticket_path).status == "paused"


def test_watchdog_timeout_spools_once_without_live_post(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    digest_spool = repo / "recurring" / "digest" / "spool.md"
    _write(
        digest_spool,
        "# Digest spool\n\n## Spool (pending)\n\nconsumed_through:\n",
    )
    cfg, ref = _in_progress_period(repo)
    urls: list[str] = []

    def capture(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        urls.append(url)

        class Response:
            status_code = 200
            text = "ok"

        return Response()

    monkeypatch.setattr("coga.notification.slack.requests.post", capture)

    recurring_cmd._stop_if_unfinished_after_launch(cfg, ref, timed_out=True)

    assert urls == []
    records = spool.read_records(digest_spool)
    assert len(records) == 1
    assert set(records[0]) == {
        "id",
        "ts",
        "project",
        "kind",
        "detail",
        "ticket",
        "owner",
    }
    assert records[0]["kind"] == "recurring-error"


def test_non_timeout_unfinished_pause_stays_silent(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, ref = _in_progress_period(repo)
    urls: list[str] = []

    def capture(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        urls.append(url)
        raise AssertionError("a non-timeout pause must stay silent")

    monkeypatch.setattr("coga.notification.slack.requests.post", capture)

    recurring_cmd._stop_if_unfinished_after_launch(cfg, ref, timed_out=False)

    assert urls == []
    assert Ticket.read(ref.ticket_path).status == "paused"


@pytest.mark.parametrize(
    ("script_stopped", "expected_status"),
    [(True, "blocked"), (False, "paused")],
    ids=["script-signal", "agent-unfinished"],
)
def test_only_script_owned_block_is_preserved_after_recurring_launch(
    repo: Path,
    script_stopped: bool,
    expected_status: str,
) -> None:
    """A script block is completion; an unfinished agent block is parked."""
    cfg, ref = _in_progress_period(repo)
    ticket = Ticket.read(ref.ticket_path)
    ticket.frontmatter["status"] = "blocked"
    ticket.write(ref.ticket_path)

    recurring_cmd._stop_if_unfinished_after_launch(
        cfg,
        ref,
        script_stopped=script_stopped,
    )

    assert Ticket.read(ref.ticket_path).status == expected_status


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


def test_pre_scan_catch_up_conflict_names_files_and_fix(git_repo, capsys) -> None:
    """A real diverged-with-conflict checkout yields a distilled reason: the
    CONFLICT line plus the exact resolve command — no rebase progress spew."""
    (git_repo.root / "notes.md").write_text("local\n")
    git_repo.git("add", "notes.md")
    git_repo.git("commit", "-m", "local note")
    git_repo.push_competing_commit("notes.md", "remote\n")

    cfg = load_config(git_repo.coga_os)
    catchup = recurring_cmd._sync_control_checkout_ahead(
        cfg, announce_failure=False
    )
    fresh, reason = catchup.fresh, catchup.reason

    assert not fresh
    # The control branch *is* checked out here — this is a real integration
    # conflict, not the recoverable off-branch case.
    assert not catchup.off_control_branch
    assert "CONFLICT" in reason
    assert "notes.md" in reason
    assert "Rebasing (" not in reason
    assert "hint:" not in reason
    assert f"git -C {git_repo.root} rebase origin/main" in reason
    # announce_failure=False: the caller reports the reason itself, so no
    # duplicate stderr note.
    assert "pre-scan catch-up skipped" not in capsys.readouterr().err


def test_bare_scan_notes_catch_up_failure_once_and_continues(
    git_repo, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """An offline control checkout warns once and still scans."""

    def fail_fetch(*args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        raise coga_git.GitError("simulated fetch failure")

    monkeypatch.setattr(recurring_cmd, "_fetch_control_branch", fail_fetch)
    monkeypatch.setattr(recurring_cmd.git, "_fetch_branch_oid", fail_fetch)
    cfg = load_config(git_repo.coga_os)

    assert recurring_cmd.run_recurring_scan(cfg) == 0

    err = capsys.readouterr().err
    assert err.count("pre-scan catch-up skipped") == 1
    assert "simulated fetch failure" in err
    # A fetch failure (offline, dead remote) gets no rebase advice.
    assert "Resolve in that checkout" not in err


def test_recurring_all_names_stale_control_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A child refusing for a stale control checkout gets a cause-naming parent
    line, and the summary names the failed repo."""
    root = tmp_path / "workspaces"
    first = root / "alpha" / "coga"
    second = root / "beta" / "coga"
    for coga_os in (first, second):
        _write(coga_os / "coga.toml", "version = 1\n")
        _write(coga_os / "coga.local.toml", 'user = "marc"\n')

    monkeypatch.setattr(
        recurring_cmd,
        "_run_repo_recurring",
        lambda coga_os, **kwargs: (
            coga_git.STALE_CONTROL_EXIT_CODE if coga_os == first else 0
        ),
    )

    result = CliRunner().invoke(app, ["recurring", "--all", str(root)])

    assert result.exit_code == 1
    assert "alpha — control checkout could not integrate the latest control tip" in (
        result.output
    )
    assert "recurring exited" not in result.output
    assert "1 repo(s) failed: alpha" in result.output


def test_automatic_sweep_launches_select_recurring_conduct(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Automatic recurring launches select the recurring queue conduct layer
    so the agent announces-and-continues and ends owner decisions in
    `coga block` instead of hanging the queue on a conversational ask."""
    cfg = load_config(repo)
    seen: list[dict] = []

    def fake_launch(slug: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        seen.append(kwargs)
        ticket_path = repo / "tasks" / "recurring" / "weekly-check" / "ticket.md"
        finished = Ticket.read(ticket_path)
        finished.frontmatter["status"] = "done"
        finished.frontmatter.pop("step", None)
        finished.write(ticket_path)

    _allow_interactive_recurring(monkeypatch)
    _freeze_recurring_now(monkeypatch, datetime(2026, 4, 22, 10, 0, 0))
    _patch_recurring_command_launch(monkeypatch, repo, fake_launch)

    assert recurring_cmd.run_recurring_scan(cfg) == 0

    assert len(seen) == 1
    assert seen[0]["launch_context"] == "recurring"
    assert seen[0]["script_failure_important"] is True


def test_authorized_sweep_uses_the_internal_period_launch_seam(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An already-gated sweep never re-enters public recurring admission."""
    cfg = load_config(repo)
    launched: list[str] = []
    kwargs_seen: list[bool] = []

    def fake_period_launch(slug: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        launched.append(slug)
        kwargs_seen.append(kwargs["control_remote_expected"])
        ticket_path = repo / "tasks" / slug / "ticket.md"
        finished = Ticket.read(ticket_path)
        finished.frontmatter["status"] = "done"
        finished.frontmatter.pop("step", None)
        finished.write(ticket_path)

    _allow_interactive_recurring(monkeypatch)
    _freeze_recurring_now(monkeypatch, datetime(2026, 4, 22, 10, 0, 0))
    _patch_recurring_command_launch(monkeypatch, repo, fake_period_launch)
    monkeypatch.setattr(
        "coga.commands.launch.launch",
        lambda *args, **kwargs: pytest.fail(
            "an authorized sweep must not call the public launch gate"
        ),
    )

    assert recurring_cmd.run_recurring_scan(cfg) == 0
    assert launched == ["recurring/weekly-check"]
    assert kwargs_seen == [False]


def test_interactive_sweep_launches_select_attended_conduct(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--interactive` is a human stepping through by hand — attended
    conduct, so the agent may ask and wait instead of blocking."""
    cfg = load_config(repo)
    seen: list[dict] = []

    def fake_launch(slug: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        seen.append(kwargs)
        ticket_path = repo / "tasks" / "recurring" / "weekly-check" / "ticket.md"
        finished = Ticket.read(ticket_path)
        finished.frontmatter["status"] = "done"
        finished.frontmatter.pop("step", None)
        finished.write(ticket_path)

    _allow_interactive_recurring(monkeypatch)
    _freeze_recurring_now(monkeypatch, datetime(2026, 4, 22, 10, 0, 0))
    _patch_recurring_command_launch(monkeypatch, repo, fake_launch)

    assert recurring_cmd.run_recurring_scan(cfg, interactive=True) == 0

    assert len(seen) == 1
    assert seen[0]["launch_context"] == "attended"
    assert seen[0]["script_failure_important"] is True


def test_named_recurring_launch_selects_recurring_conduct(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """On-demand `coga recurring launch <name>` (and the `coga dream` alias)
    is an automatic launch too — same conduct as the sweep."""
    cfg = load_config(repo)
    seen: list[dict] = []

    def fake_launch(slug: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        seen.append(kwargs)

    _allow_interactive_recurring(monkeypatch)
    _freeze_recurring_now(monkeypatch, datetime(2026, 4, 22, 10, 0, 0))
    monkeypatch.setattr("coga.commands.launch.launch_recurring_period", fake_launch)

    assert recurring_cmd.run_recurring_named(cfg, "weekly-check") == 0

    assert len(seen) == 1
    assert seen[0]["launch_context"] == "recurring"
    assert seen[0]["script_failure_important"] is True
    assert seen[0]["control_remote_expected"] is False


# --- coga recurring promote: task → template authoring ------------------------


def _write_task(company: Path, slug: str, text: str) -> None:
    """Write a file-form task (`tasks/<slug>.md`), the shape `coga create`
    produces for a plain ticket."""
    _write(company / "tasks" / f"{slug}.md", text)


def test_promote_moves_task_into_a_valid_recurring_template(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The move a human would otherwise hand-do: the ticket leaves `tasks/`,
    lands as `recurring/<slug>/ticket.md`, and loads as a template."""
    monkeypatch.chdir(repo)
    _write_task(
        repo,
        "deliverability-review",
        """
        ---
        slug: deliverability-review
        title: Deliverability review
        status: draft
        owner: marc
        human: marc
        agent: claude
        assignee: claude
        watchers:
        - dana
        contexts:
        - coga/period-task
        skills: []
        workflow: null
        secrets: null
        script: null
        ---

        ## Description

        Run the deliverability diagnostic suite.

        ## Context

        Uses the shared sending domain.

        <!-- coga:blackboard -->

        Scratch from the one-off run.
        """,
    )

    result = CliRunner().invoke(
        app,
        [
            "recurring",
            "promote",
            "deliverability-review",
            "--schedule",
            "0 9 * * 1",
        ],
    )

    assert result.exit_code == 0, result.output
    assert not (repo / "tasks" / "deliverability-review.md").exists()
    ticket_path = repo / "recurring" / "deliverability-review" / "ticket.md"
    template = Template.load(ticket_path.parent)
    assert template.schedule == "0 9 * * 1"
    assert template.frontmatter["title"] == "Deliverability review"
    assert template.frontmatter["owner"] == "marc"
    assert template.frontmatter["assignee"] == "claude"
    assert template.frontmatter["watchers"] == ["dana"]
    # Task-only fields never reach a template; the creator re-derives them.
    for dropped in ("slug", "status", "step", "human", "agent", "skills"):
        assert dropped not in template.frontmatter
    # An empty/`null` passthrough is omitted rather than written as `null`.
    assert "workflow" not in template.frontmatter
    assert "script" not in template.frontmatter
    # `coga/period-task` is auto-attached per period; it is not template state.
    assert "contexts" not in template.frontmatter
    assert "Run the deliverability diagnostic suite." in template.body
    assert "Uses the shared sending domain." in template.body
    blackboard = read_blackboard(ticket_path, blackboard_required=False)
    assert "Scratch from the one-off run." not in blackboard
    assert "cross-run state" in blackboard


def test_promote_reports_the_move_and_what_it_dropped(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    _write_task(
        repo,
        "weekly-audit",
        """
        ---
        slug: weekly-audit
        title: Weekly audit
        status: active
        owner: marc
        assignee: claude
        skills:
        - infra/tests
        workflow:
          name: code/with-review
          steps:
          - name: implement
            skills:
            - code/implement
        step: 1 (implement)
        ---

        ## Description

        Audit the thing.

        <!-- coga:blackboard -->

        Notes.
        """,
    )

    result = CliRunner().invoke(
        app, ["recurring", "promote", "weekly-audit", "--schedule", "0 9 * * 1"]
    )

    assert result.exit_code == 0, result.output
    assert "Promoted weekly-audit → recurring/weekly-audit" in result.output
    assert "infra/tests" in result.output
    assert "blackboard" in result.output
    template = Template.load(repo / "recurring" / "weekly-audit")
    # A frozen workflow snapshot collapses back to the name the creator freezes
    # per period.
    assert template.frontmatter["workflow"] == "code/with-review"
    assert "step" not in template.frontmatter


def test_promote_names_template_and_preserves_attachments(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A directory-form task promotes under an explicit name, siblings and all."""
    monkeypatch.chdir(repo)
    _write(
        repo / "tasks" / "old-slug" / "ticket.md",
        """
        ---
        slug: old-slug
        title: Nightly drain
        status: draft
        owner: marc
        ---

        ## Description

        Drain the queue.

        <!-- coga:blackboard -->
        """,
    )
    (repo / "tasks" / "old-slug" / "notes.txt").write_text("supporting material\n")
    (repo / "tasks" / "old-slug" / ".state-snapshot.json").write_text("{}\n")

    result = CliRunner().invoke(
        app,
        [
            "recurring",
            "promote",
            "old-slug",
            "--schedule",
            "0 3 * * *",
            "--name",
            "nightly-drain",
        ],
    )

    assert result.exit_code == 0, result.output
    assert not (repo / "tasks" / "old-slug").exists()
    dest = repo / "recurring" / "nightly-drain"
    assert (dest / "notes.txt").is_file()
    # A period task's create-time baseline is not template state.
    assert not (dest / ".state-snapshot.json").exists()
    assert "script" not in Template.load(dest).frontmatter


def test_promote_preserves_sibling_symlinks_without_reading_their_targets(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Promotion is a move: symlink siblings and nested links remain links
    rather than turning external target contents into committed attachments."""
    monkeypatch.chdir(repo)
    source = repo / "tasks" / "linked-task"
    _write(
        source / "ticket.md",
        """
        ---
        slug: linked-task
        title: Linked task
        status: draft
        owner: marc
        ---

        ## Description

        Keep the links as links.

        <!-- coga:blackboard -->
        """,
    )
    external_file = repo.parent / "outside.txt"
    external_file.write_text("outside the repository\n")
    external_dir = repo.parent / "outside-dir"
    external_dir.mkdir()
    (external_dir / "payload.txt").write_text("also outside\n")
    (source / "file-link").symlink_to(external_file)
    (source / "dir-link").symlink_to(external_dir, target_is_directory=True)
    attachments = source / "attachments"
    attachments.mkdir()
    (attachments / "nested-link").symlink_to(external_file)

    result = CliRunner().invoke(
        app, ["recurring", "promote", "linked-task", "--schedule", "0 3 * * *"]
    )

    assert result.exit_code == 0, result.output
    dest = repo / "recurring" / "linked-task"
    assert (dest / "file-link").is_symlink()
    assert (dest / "file-link").readlink() == external_file
    assert (dest / "dir-link").is_symlink()
    assert (dest / "dir-link").readlink() == external_dir
    assert (dest / "attachments" / "nested-link").is_symlink()
    assert (dest / "attachments" / "nested-link").readlink() == external_file


def test_promote_refuses_a_missing_collapsed_workflow_before_deleting_source(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A terminal task can outlive its workflow definition. Promotion must
    catch that stale snapshot before replacing the recoverable source ticket."""
    monkeypatch.chdir(repo)
    _write_task(
        repo,
        "stale-workflow",
        """
        ---
        slug: stale-workflow
        title: Stale workflow
        status: done
        owner: marc
        workflow:
          name: removed/weekly
          steps:
          - name: run
            skills: []
        ---

        ## Description

        This must still be launchable after promotion.

        <!-- coga:blackboard -->
        """,
    )

    result = CliRunner().invoke(
        app,
        [
            "recurring",
            "promote",
            "stale-workflow",
            "--schedule",
            "0 3 * * *",
        ],
    )

    assert result.exit_code == 2
    assert "workflow 'removed/weekly'" in result.output
    assert (repo / "tasks" / "stale-workflow.md").is_file()
    assert not (repo / "recurring" / "stale-workflow").exists()


def test_promote_refuses_an_existing_template_and_leaves_the_task(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    _write_task(
        repo,
        "weekly-check",
        """
        ---
        slug: weekly-check
        title: Weekly check
        status: draft
        owner: marc
        ---

        ## Description

        Check.

        <!-- coga:blackboard -->
        """,
    )
    before = (repo / "recurring" / "weekly-check" / "ticket.md").read_text()

    result = CliRunner().invoke(
        app, ["recurring", "promote", "weekly-check", "--schedule", "0 9 * * 1"]
    )

    assert result.exit_code == 2
    assert "already exists" in result.output
    assert (repo / "tasks" / "weekly-check.md").is_file()
    assert (repo / "recurring" / "weekly-check" / "ticket.md").read_text() == before


@pytest.mark.parametrize(
    "schedule",
    [
        pytest.param("every monday", id="malformed"),
        pytest.param("* * * * * *", id="six-fields"),
        pytest.param("@daily", id="alias"),
    ],
)
def test_promote_validates_the_cron_before_moving_anything(
    schedule: str,
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bad schedule fails up front — the source ticket is untouched and no
    half-built template is left behind."""
    monkeypatch.chdir(repo)
    _write_task(
        repo,
        "bad-cron",
        """
        ---
        slug: bad-cron
        title: Bad cron
        status: draft
        owner: marc
        ---

        ## Description

        Nope.

        <!-- coga:blackboard -->
        """,
    )

    result = CliRunner().invoke(
        app, ["recurring", "promote", "bad-cron", "--schedule", schedule]
    )

    assert result.exit_code == 2
    assert "not a valid cron expression" in result.output
    if schedule in {"* * * * * *", "@daily"}:
        assert "exactly 5 fields" in result.output
    assert (repo / "tasks" / "bad-cron.md").is_file()
    assert not (repo / "recurring" / "bad-cron").exists()


def test_promote_refuses_a_live_run(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`in_progress`/`blocked` carry step and blocker state a template cannot
    hold; land the run first rather than silently dropping the handoff."""
    monkeypatch.chdir(repo)
    _write_task(
        repo,
        "mid-flight",
        """
        ---
        slug: mid-flight
        title: Mid flight
        status: in_progress
        owner: marc
        ---

        ## Description

        Running.

        <!-- coga:blackboard -->
        """,
    )

    result = CliRunner().invoke(
        app, ["recurring", "promote", "mid-flight", "--schedule", "0 9 * * 1"]
    )

    assert result.exit_code == 2
    assert "in_progress" in result.output
    assert (repo / "tasks" / "mid-flight.md").is_file()
    assert not (repo / "recurring" / "mid-flight").exists()


def test_promoted_template_creates_a_real_period_task(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End to end: the promoted template fires like any other, creating
    `tasks/recurring/<name>/` with the body and roles it carried."""
    monkeypatch.chdir(repo)
    _write_task(
        repo,
        "monthly-report",
        """
        ---
        slug: monthly-report
        title: Monthly report
        status: draft
        owner: marc
        assignee: claude
        ---

        ## Description

        Write the monthly report.

        <!-- coga:blackboard -->
        """,
    )
    result = CliRunner().invoke(
        app, ["recurring", "promote", "monthly-report", "--schedule", "0 9 1 * *"]
    )
    assert result.exit_code == 0, result.output

    cfg = load_config(repo)
    outcome = create_named(cfg, "monthly-report", now=datetime(2026, 4, 1, 10, 0, 0))

    assert outcome.created is True
    ticket = Ticket.read(outcome.ref.path / "ticket.md")
    assert outcome.ref.id_slug == "recurring/monthly-report"
    assert ticket.frontmatter["title"] == "Monthly report"
    assert ticket.frontmatter["status"] == "active"
    assert ticket.frontmatter["assignee"] == "claude"
    assert "coga/period-task" in ticket.contexts
    assert "Write the monthly report." in ticket.body
    assert (
        read_serviced_period(repo / "recurring" / "monthly-report" / "ticket.md")
        == "2026-04"
    )


# --- the ledger is the log ----------------------------------------------------


def test_serviced_period_survives_a_blackboard_rewrite(repo: Path) -> None:
    """The bug this design replaced: a co-writer erasing the template state.

    The digest run rewrites its `### Digest State` section, which used to
    swallow a `last_serviced_period` mark appended after it. Every subsequent
    `coga recurring` then treated the period as unserviced, deleted the
    completed task, and reran the digest — reposting it each time.
    """
    _write_recurring(
        repo,
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
    cfg = load_config(repo)
    first = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    assert first.tasks[0].created is True

    # A run rewrites the whole blackboard region, taking any mark with it.
    _seed_template_blackboard(repo, "weekly-check", "### Run State\n\ncursor: 9\n")
    _finish_period_task(repo, "recurring/weekly-check")

    again = scan_due(cfg, now=datetime(2026, 4, 22, 11, 0, 0))

    assert again.tasks[0].created is False
    assert again.tasks[0].replaced_done is False
    assert again.due == []


def test_repeated_scans_in_one_period_service_it_once(repo: Path) -> None:
    """Three `coga recurring` invocations inside one period, one run."""
    _write_recurring(
        repo,
        "daily-digest",
        """
        ---
        schedule: "0 9 * * *"
        title: "Daily digest"
        assignee: claude
        owner: marc
        ---

        ## Description

        Post the digest.
        """,
    )
    cfg = load_config(repo)
    created = 0
    for hour in (10, 11, 12):
        scan = scan_due(cfg, now=datetime(2026, 4, 22, hour, 0, 0))
        if scan.tasks[0].created or scan.tasks[0].replaced_done:
            created += 1
            _finish_period_task(repo, "recurring/daily-digest")

    assert created == 1
    log = "\n".join(task_log_lines(cfg, "recurring/daily-digest"))
    assert log.count("for 2026-04-22") == 1


def test_serviced_log_format_is_pinned() -> None:
    """Dedup parses this line, so its wording is a contract, not prose.

    `serviced_periods` reads back what `_record_run` wrote. If the message is
    reworded without updating the parser, dedup silently stops working and
    every period re-fires — so the exact spelling is pinned here.
    """
    assert (
        format_serviced_log("created", "recurring/digest", "2026-08-13")
        == "created recurring/digest for 2026-08-13"
    )
    assert (
        format_serviced_log("reused", "recurring/dream", "2026-W33")
        == "reused recurring/dream for 2026-W33"
    )
    with pytest.raises(ValueError):
        format_serviced_log("advanced", "recurring/digest", "2026-08-13")
    with pytest.raises(ValueError, match="invalid period key 'none'"):
        format_serviced_log("created", "recurring/digest", "none")


@pytest.mark.parametrize(
    "period",
    ["2026-08", "2026-W33", "2026-08-13", "2026-08-13-17", "20260813T1722"],
)
def test_serviced_log_accepts_every_generated_period_shape(period: str) -> None:
    assert format_serviced_log("created", "recurring/check", period).endswith(
        f" for {period}"
    )


def test_serviced_periods_reads_the_newest_record_per_template(repo: Path) -> None:
    """`merge=union` can leave the log unsorted, so the max wins, not the last."""
    cfg = load_config(repo)
    for period in ("2026-W20", "2026-W22", "2026-W21"):
        _seed_serviced_period(repo, "weekly-check", period)
    _seed_serviced_period(repo, "other-check", "2026-W02")

    serviced = serviced_periods(cfg)

    assert serviced["recurring/weekly-check"] == "2026-W22"
    assert serviced["recurring/other-check"] == "2026-W02"


def test_serviced_periods_orders_mixed_key_shapes_as_calendar_periods(
    repo: Path,
) -> None:
    """A schedule change must not bring lexical period ordering back."""
    cfg = load_config(repo)
    _seed_serviced_period(repo, "weekly-check", "2026-12")
    _seed_serviced_period(repo, "weekly-check", "2026-W01")

    assert serviced_periods(cfg)["recurring/weekly-check"] == "2026-12"


@pytest.mark.parametrize(
    "period",
    ["none", "2026-13", "2026-W54", "2026-02-30", "2026-01-01-24"],
)
def test_serviced_periods_rejects_malformed_period_keys(
    repo: Path, period: str
) -> None:
    cfg = load_config(repo)
    append_log(
        cfg,
        "recurring/weekly-check",
        "system",
        f"created recurring/weekly-check for {period}",
    )

    with pytest.raises(
        RecurringError,
        match=rf"invalid serviced period {re.escape(repr(period))}.*weekly-check",
    ):
        serviced_periods(cfg)


def test_read_serviced_ledger_bounds_its_read_to_the_log_tail(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`coga/log.md` grows without bound, so a scan must not walk all of it.

    Once the target period is in the tail, older records cannot change the
    caller's "at least this period" answer. Reading forward from byte zero would
    make every repeated same-period sweep pay for the repo's whole history.
    """
    cfg = load_config(repo)
    for note in range(20):
        append_log(cfg, "ancient", "human:marc", f"ancient note {note}")
    _seed_serviced_period(repo, "weekly-check", "2026-W20")
    for note in range(20):
        append_log(cfg, "recent", "human:marc", f"recent note {note}")

    seen: list[tuple[str, str]] = []
    real = recurring_module.iter_log_messages_reverse

    def counting(cfg_arg, **kwargs):  # type: ignore[no-untyped-def]
        for entry in real(cfg_arg, **kwargs):
            seen.append(entry)
            yield entry

    monkeypatch.setattr(recurring_module, "iter_log_messages_reverse", counting)

    ledger = read_serviced_ledger(
        cfg, {"recurring/weekly-check": "2026-W20"}
    )

    assert ledger.periods == {"recurring/weekly-check": "2026-W20"}
    assert ("ancient", "ancient note 0") not in seen
    assert len(seen) < 41


def test_read_serviced_ledger_does_not_stop_at_an_older_union_merged_record(
    repo: Path,
) -> None:
    """An arbitrary tail window cannot make an unordered ledger correct.

    A long-lived branch can append an old period at EOF after more than any
    fixed number of unrelated union-merged lines. The older hit must leave the
    ref pending until the target period is found; otherwise dedup can re-fire
    already-serviced work.
    """
    cfg = load_config(repo)
    _seed_serviced_period(repo, "weekly-check", "2026-W22")
    for note in range(600):
        append_log(cfg, f"noise/{note}", "system", "union-merged note")
    _seed_serviced_period(repo, "weekly-check", "2026-W21")

    ledger = read_serviced_ledger(
        cfg, {"recurring/weekly-check": "2026-W22"}
    )

    assert ledger.periods == {"recurring/weekly-check": "2026-W22"}


def test_scan_does_not_refire_past_an_older_union_merged_tail_record(
    repo: Path,
) -> None:
    """The target-aware read must protect the real scan, not only its parser."""
    cfg = load_config(repo)
    _seed_serviced_period(repo, "weekly-check", "2026-W24")
    for note in range(600):
        append_log(cfg, f"noise/{note}", "system", "union-merged note")
    _seed_serviced_period(repo, "weekly-check", "2026-W23")

    scan = scan_due(cfg, now=datetime(2026, 6, 8, 10, 0, 0))

    assert len(scan.tasks) == 1
    assert scan.tasks[0].period_key == "2026-W24"
    assert scan.tasks[0].ref is None
    assert scan.tasks[0].created is False
    assert not (tasks_dir(cfg) / "recurring" / "weekly-check").exists()


def test_broadcast_reuses_the_fresh_prescan_control_ledger(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A normal caught-up sweep must not materialize control's whole log."""
    cfg = load_config(repo)
    _seed_serviced_period(repo, "weekly-check", "2026-W24")
    scan = scan_due(cfg, now=datetime(2026, 6, 8, 10, 0, 0))
    assert scan.ledger_periods == {"recurring/weekly-check": "2026-W24"}

    monkeypatch.setattr(recurring_cmd, "_git_toplevel", lambda *args: repo)
    monkeypatch.setattr(
        recurring_cmd,
        "_read_control_ledger",
        lambda *args, **kwargs: pytest.fail("fresh sweep reread control log"),
    )

    recurring_cmd._broadcast_scan(cfg, scan, control_is_fresh=True)

    assert scan.errors == []


def test_read_serviced_ledger_ignores_templates_the_caller_did_not_request(
    repo: Path,
) -> None:
    """One template's bad ledger state must not answer for another's."""
    cfg = load_config(repo)
    _seed_serviced_period(repo, "weekly-check", "2026-W20")
    append_log(
        cfg,
        "recurring/other-check",
        "system",
        "created recurring/other-check for none",
    )

    ledger = read_serviced_ledger(
        cfg, {"recurring/weekly-check": "2026-W20"}
    )

    assert ledger.periods == {"recurring/weekly-check": "2026-W20"}
    assert ledger.errors == {}


def test_read_serviced_ledger_stops_each_ref_after_its_target_resolves(
    repo: Path,
) -> None:
    """One unresolved template must not expose another's healed history."""
    cfg = load_config(repo)
    _seed_serviced_period(repo, "other-check", "2026-W20")
    append_log(
        cfg,
        "recurring/weekly-check",
        "system",
        "created recurring/weekly-check for none",
    )
    _seed_serviced_period(repo, "weekly-check", "2026-W20")

    ledger = read_serviced_ledger(
        cfg,
        {
            "recurring/weekly-check": "2026-W20",
            "recurring/other-check": "2026-W20",
        },
    )

    assert ledger.periods == {
        "recurring/weekly-check": "2026-W20",
        "recurring/other-check": "2026-W20",
    }
    assert ledger.errors == {}


def test_control_ledger_uses_the_same_per_ref_target_stop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The pinned control fallback must agree with the local reverse read."""
    monkeypatch.setattr(
        recurring_cmd,
        "_show_path",
        lambda *args: "".join(
            [
                "2026-05-01 09:00 [recurring/other-check] [system] "
                "created recurring/other-check for 2026-W20\n",
                "2026-05-01 09:01 [recurring/weekly-check] [system] "
                "created recurring/weekly-check for none\n",
                "2026-05-01 09:02 [recurring/weekly-check] [system] "
                "created recurring/weekly-check for 2026-W20\n",
            ]
        ),
    )

    ledger = recurring_cmd._read_control_ledger(
        tmp_path,
        "control",
        "coga/log.md",
        {
            "recurring/weekly-check": "2026-W20",
            "recurring/other-check": "2026-W20",
        },
    )

    assert ledger["recurring/weekly-check"] == "2026-W20"
    assert ledger["recurring/other-check"] == "2026-W20"
    assert recurring_cmd._control_ledger_error_key(
        "recurring/weekly-check"
    ) not in ledger


def test_rolled_back_create_re_fires_once_its_ledger_line_is_gone(
    repo: Path,
) -> None:
    """Removing a create's audit line must re-fire the period, not wedge it.

    The ledger *is* the audit line now, so the two states a rollback can leave
    behind are both checked here. With the line intact and the task reaped, the
    period reads as handled — that is the reaped-task case, not a bug. With the
    line removed as well (reverting the create), the next scan must behave as
    if the period never ran and create the task again.
    """
    cfg = load_config(repo)
    now = datetime(2026, 6, 8, 10, 0, 0)
    first = scan_due(cfg, now=now)
    assert first.tasks[0].created
    period_key = first.tasks[0].period_key

    task_dir = tasks_dir(cfg) / "recurring" / "weekly-check"
    shutil.rmtree(task_dir)

    reaped = scan_due(cfg, now=now)
    assert reaped.tasks[0].created is False
    assert reaped.tasks[0].ref is None

    log_file = log_path(cfg)
    log_file.write_text(
        "".join(
            f"{line}\n"
            for line in log_file.read_text().splitlines()
            if format_serviced_log("created", "recurring/weekly-check", period_key)
            not in line
        )
    )

    rolled_back = scan_due(cfg, now=now)

    assert rolled_back.tasks[0].created
    assert task_dir.is_dir()
    assert serviced_periods(cfg)["recurring/weekly-check"] == period_key


def test_scan_due_reports_malformed_period_and_continues(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_recurring(
        repo,
        "daily-check",
        """
        ---
        schedule: "0 9 * * *"
        title: "Daily check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the daily check.
        """,
    )
    cfg = load_config(repo)
    append_log(
        cfg,
        "recurring/weekly-check",
        "system",
        "created recurring/weekly-check for none",
    )

    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))

    assert [task.template for task in scan.tasks] == ["daily-check"]
    assert len(scan.errors) == 1
    assert scan.errors[0][0] == "weekly-check"
    assert "invalid serviced period 'none'" in scan.errors[0][1]
    assert "recurring/weekly-check" in scan.errors[0][1]
    assert "skipping weekly-check" in capsys.readouterr().err


def test_recurring_views_render_malformed_period_as_error(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(repo)
    append_log(
        cfg,
        "recurring/weekly-check",
        "system",
        "created recurring/weekly-check for none",
    )
    monkeypatch.chdir(repo)
    monkeypatch.setenv("COLUMNS", "240")

    statuses = list_templates(cfg, now=datetime(2026, 4, 22, 10, 0, 0))
    assert len(statuses) == 1
    assert statuses[0].error is not None
    assert "invalid serviced period 'none'" in statuses[0].error

    for argv in (["recurring", "list"], ["status"]):
        result = CliRunner().invoke(app, argv)
        assert result.exit_code == 0, result.output
        assert "error: invalid serviced period 'none'" in result.output
        assert "ran this period" not in result.output


def test_scan_due_compares_serviced_periods_after_schedule_change(repo: Path) -> None:
    """An early ISO week must not sort after a later calendar month."""
    _write_recurring(
        repo,
        "weekly-check",
        """
        ---
        schedule: "0 9 1 * *"
        title: "Monthly check"
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the monthly check.
        """,
    )
    _seed_serviced_period(repo, "weekly-check", "2026-W01")

    scan = scan_due(
        load_config(repo), now=datetime(2026, 12, 2, 10, 0, 0)
    )

    assert scan.errors == []
    assert len(scan.tasks) == 1
    assert scan.tasks[0].created is True


def test_control_guard_compares_serviced_periods_as_calendar_positions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        recurring_cmd,
        "_control_serviced_period_cached",
        lambda *args, **kwargs: "2026-W01",
    )

    assert recurring_cmd._control_already_has_period(
        tmp_path,
        "control",
        "coga/tasks/recurring/check",
        log_rel="coga/log.md",
        template_ref="recurring/check",
        period_key="2026-12",
        include_task=False,
    ) is False


def test_control_ledger_rejects_malformed_period(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        recurring_cmd,
        "_show_path",
        lambda *args: (
            "2026-08-13 17:22 [recurring/check] [system] "
            "created recurring/check for none\n"
        ),
    )

    with pytest.raises(RecurringError, match="invalid serviced period 'none'"):
        recurring_cmd._control_serviced_period_cached(
            tmp_path,
            "control",
            "coga/log.md",
            "recurring/check",
            None,
        )


def test_control_guard_validates_ledger_when_dedup_is_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def malformed_control_ledger(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RecurringError(
            "invalid serviced period 'none' for recurring/check"
        )

    monkeypatch.setattr(
        recurring_cmd,
        "_control_serviced_period_cached",
        malformed_control_ledger,
    )

    with pytest.raises(RecurringError, match="invalid serviced period 'none'"):
        recurring_cmd._control_already_has_period(
            tmp_path,
            "control",
            "coga/tasks/recurring/check",
            log_rel="coga/log.md",
            template_ref="recurring/check",
            period_key="2026-W33",
            include_ledger=False,
            include_task=False,
        )


def test_broadcast_scan_skips_a_template_with_a_control_ledger_error(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = load_config(repo)
    scan = scan_due(cfg, now=datetime(2026, 4, 22, 10, 0, 0))

    def malformed_control_ledger(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RecurringError(
            "invalid serviced period 'none' for recurring/weekly-check"
        )

    monkeypatch.setattr(
        recurring_cmd,
        "_sync_recurring_create",
        malformed_control_ledger,
    )
    monkeypatch.setattr(recurring_cmd, "notify", lambda *args, **kwargs: None)

    recurring_cmd._broadcast_scan(cfg, scan)

    assert scan.tasks == []
    assert scan.errors == [
        (
            "weekly-check",
            "invalid serviced period 'none' for recurring/weekly-check",
        )
    ]
    assert "skipping weekly-check" in capsys.readouterr().err


def test_named_launch_reports_a_control_ledger_error(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def malformed_control_ledger(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RecurringError(
            "invalid serviced period 'none' for recurring/weekly-check"
        )

    monkeypatch.setattr(
        recurring_cmd, "_sync_recurring_create", malformed_control_ledger
    )
    monkeypatch.setattr(
        recurring_cmd,
        "_launch_created",
        lambda *args, **kwargs: pytest.fail("malformed ledger reached launch"),
    )

    assert recurring_cmd.run_recurring_named(
        load_config(repo), "weekly-check"
    ) == 2
    assert "invalid serviced period 'none'" in capsys.readouterr().err


def test_feature_branch_landing_keeps_malformed_control_ledger_blocked_on_retry(
    git_repo,
) -> None:
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        owner: marc
        assignee: claude
        ---

        ## Description

        Run the weekly check.
        """,
    )
    git_repo.git("add", "coga/contexts", "coga/recurring")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")
    git_repo.push_competing_commit(
        "coga/log.md",
        "2026-08-13 17:22 [recurring/weekly-check] [system] "
        "created recurring/weekly-check for none\n",
    )
    cfg = load_config(coga_os)
    now = datetime(2026, 8, 17, 10, 0)

    first = create_named(cfg, "weekly-check", now=now)
    assert first.created
    with pytest.raises(RecurringError, match="invalid serviced period 'none'"):
        recurring_cmd._sync_recurring_create(
            cfg,
            "weekly-check",
            first.ref,
            respect_handled_period=False,
            expected_period_key=first.period_key,
        )

    retry = create_named(cfg, "weekly-check", now=now)
    assert not retry.created
    with pytest.raises(RecurringError, match="invalid serviced period 'none'"):
        recurring_cmd._validate_control_serviced_period(
            cfg,
            "weekly-check",
            expected_period_key=retry.period_key,
        )
    assert (
        coga_os / "tasks" / "recurring" / "weekly-check" / "ticket.md"
    ).is_file()


def test_feature_branch_sweep_revalidates_malformed_control_ledger_on_retry(
    git_repo,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    coga_os = git_repo.coga_os
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly check"
        owner: marc
        assignee: claude
        ---

        ## Description

        Run the weekly check.
        """,
    )
    git_repo.git("add", "coga/contexts", "coga/recurring")
    git_repo.git("commit", "-m", "seed recurring template")
    git_repo.git("push", "origin", "main")
    git_repo.push_competing_commit(
        "coga/log.md",
        "2026-08-13 17:22 [recurring/weekly-check] [system] "
        "created recurring/weekly-check for none\n",
    )
    monkeypatch.setattr(recurring_cmd, "notify", lambda *args, **kwargs: None)
    cfg = load_config(coga_os)
    now = datetime(2026, 8, 17, 10, 0)

    first = scan_due(cfg, now=now)
    recurring_cmd._broadcast_scan(cfg, first)
    retry = scan_due(cfg, now=now)
    recurring_cmd._broadcast_scan(cfg, retry)

    assert first.tasks == []
    assert retry.tasks == []
    assert [name for name, _error in first.errors] == ["weekly-check"]
    assert "invalid serviced period 'none'" in first.errors[0][1]
    assert retry.errors == first.errors
    assert capsys.readouterr().err.count("invalid serviced period 'none'") >= 2
    assert (
        coga_os / "tasks" / "recurring" / "weekly-check" / "ticket.md"
    ).is_file()


def test_serviced_periods_ignores_other_log_lines(repo: Path) -> None:
    """Ordinary history for the same ref must not parse as a ledger record."""
    cfg = load_config(repo)
    append_log(cfg, "recurring/weekly-check", "system", "started (active → in_progress)")
    append_log(cfg, "recurring/weekly-check", "system", "deleted completed prior-period task before 2026-W17")
    append_log(cfg, "some-task", "system", "created some-task for 2026-W30")

    serviced = serviced_periods(cfg)

    assert "recurring/weekly-check" not in serviced
    assert "some-task" not in serviced  # not a recurring ref


def test_feature_branch_create_lands_the_ledger_on_control(
    git_repo, monkeypatch
) -> None:
    """A create from a feature branch records the period on control *now*.

    The period task lands on control immediately, so the record that says the
    period ran has to land with it. Waiting for this branch's PR to merge is
    not enough: Dream's retro pass deletes completed period tickets, so a
    control checkout would see neither the task nor the record and fire the
    same period again — and a branch that never merges never delivers it.

    The log is `merge=union`, so it must reach control three-way merged rather
    than through the wholesale-replacement overlay.
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
    git_repo.checkout_branch("feature/never-merges")

    cfg = load_config(coga_os)
    outcome = create_named(cfg, "weekly-check", now=datetime(2026, 6, 8, 10, 5))
    recurring_cmd._sync_recurring_create(cfg, "weekly-check", outcome.ref)

    # Control has the task and the record, without this branch ever merging.
    assert git_repo.origin_tracks(f"coga/tasks/{outcome.ref.id_slug}/ticket.md")
    assert _control_serviced_period(git_repo, "weekly-check") == "2026-W24"

    # Dream reaps the completed task from control; the record must outlive it.
    git_repo.push_competing_commit("notes.md", "reaped\n")
    control_log = git_repo.git("show", "main:coga/log.md", cwd=git_repo.origin)
    assert "created recurring/weekly-check for 2026-W24" in control_log


def test_control_ledger_landing_preserves_a_peer_append(git_repo, monkeypatch) -> None:
    """The union landing must fold in, not overwrite, another checkout's lines."""
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
    git_repo.checkout_branch("feature/peer-append")

    cfg = load_config(coga_os)
    outcome = create_named(cfg, "weekly-check", now=datetime(2026, 6, 8, 10, 5))
    # Another checkout appends its own audit line to control first.
    git_repo.push_competing_commit(
        "coga/log.md",
        "2026-06-08 09:00 [some-other-task] [system] peer line\n",
    )

    recurring_cmd._sync_recurring_create(cfg, "weekly-check", outcome.ref)

    control_log = git_repo.git("show", "main:coga/log.md", cwd=git_repo.origin)
    assert "peer line" in control_log
    assert "created recurring/weekly-check for 2026-W24" in control_log


# --- servicing an off-control checkout from a temp control worktree ------------


def _seed_recipe_template_on_control(git_repo, name: str = "z-script-check") -> None:
    """Commit and push a recipe-backed template that is due every minute.

    The temp-worktree run is a real subprocess whose clock this process cannot
    freeze, so the schedule fires whatever the wall time is and the assertions
    read the ledger rather than a fixed period key.
    """
    coga_os = git_repo.coga_os
    # Gitignored, so the temp worktree only has it because the run copies it —
    # without that copy `load_config` raises on the missing `user` before the
    # inner scan starts.
    (coga_os / "coga.local.toml").write_text(
        'user = "marc"\n[notification.slack]\nenabled = false\n'
    )
    _seed_period_task_context(coga_os)
    _write_recurring(
        coga_os,
        name,
        f"""
        ---
        schedule: "* * * * *"
        title: "Script check"
        owner: marc
        ---

        ## Description

        Run {name}.
        """,
    )
    # The deterministic half completes its own step, exactly as the shipped
    # recipe templates do — otherwise the launch stops at the agent phase and
    # the run is not a clean end-to-end sweep to assert on.
    _write_recurring_script(
        coga_os,
        name,
        """
        import os
        import subprocess
        import sys

        sys.exit(
            subprocess.run(
                [sys.executable, "-m", "coga.cli", "bump",
                 os.environ["COGA_TASK_SLUG"]],
                check=False,
            ).returncode
        )
        """,
    )
    _seed_global_log(git_repo)
    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", "seed recipe template")
    git_repo.git("push", "origin", "main")


def _checkout_state(git_repo) -> tuple[str, str, str, str]:
    """Everything the operator's checkout must not lose during a sweep."""
    return (
        git_repo.git("rev-parse", "HEAD"),
        git_repo.git("rev-parse", "--abbrev-ref", "HEAD"),
        git_repo.git("status", "--porcelain", "--untracked-files=all", "--ignored"),
        git_repo.git("stash", "list"),
    )


def test_recurring_all_scan_services_off_control_checkout_from_worktree(
    git_repo, capsys
) -> None:
    """The headline behavior: a dirty feature-branch checkout still sweeps.

    Nothing is stubbed — `git worktree add`, the recipe subprocess, and the
    control push all run for real against the bare `origin`.
    """
    _seed_recipe_template_on_control(git_repo)
    git_repo.checkout_branch("agent/parked-work")
    (git_repo.root / "uncommitted.md").write_text("work in progress\n")
    before = _checkout_state(git_repo)

    cfg = load_config(git_repo.coga_os)
    assert recurring_cmd.run_recurring_scan(cfg, require_fresh_control=True) == 0

    # The operator's checkout is byte-identical: same branch, same HEAD, same
    # tracked/untracked/ignored status, and no stash entry was ever created.
    assert _checkout_state(git_repo) == before

    # The period task and its ledger line both reached control, which is what
    # stops the next sweep re-firing the period once Dream reaps the task.
    serviced = _control_serviced_period(git_repo, "z-script-check")
    assert serviced is not None
    ledger = git_repo.git("show", "main:coga/log.md", cwd=git_repo.origin)
    assert "recurring/z-script-check" in ledger
    assert "temporary 'main' worktree" in capsys.readouterr().out


def test_control_worktree_services_a_deeply_nested_monorepo_workspace(
    git_repo,
) -> None:
    """The inner child's cwd is the mirrored workspace host, not repo root."""
    _seed_recipe_template_on_control(git_repo)
    original = git_repo.coga_os
    nested = git_repo.root / "tools" / "ops" / "coga"
    nested.parent.mkdir(parents=True)
    shutil.move(str(original), str(nested))
    git_repo.coga_os = nested
    (git_repo.root / ".gitignore").write_text("**/coga.local.toml\n")
    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", "nest coga workspace")
    git_repo.git("push", "origin", "main")
    git_repo.checkout_branch("agent/parked-work")
    before = _checkout_state(git_repo)

    cfg = load_config(nested)
    assert recurring_cmd.run_recurring_scan(cfg, require_fresh_control=True) == 0

    assert _checkout_state(git_repo) == before
    ledger = git_repo.git(
        "show", "main:tools/ops/coga/log.md", cwd=git_repo.origin
    )
    assert "created recurring/z-script-check" in ledger


def test_control_worktree_run_does_not_refire_the_serviced_period(git_repo) -> None:
    """The ledger written from the temp worktree is read by the next sweep."""
    _seed_recipe_template_on_control(git_repo)
    git_repo.checkout_branch("agent/parked-work")

    cfg = load_config(git_repo.coga_os)
    assert recurring_cmd.run_recurring_scan(cfg, require_fresh_control=True) == 0
    first = git_repo.git("show", "main:coga/log.md", cwd=git_repo.origin)

    assert recurring_cmd.run_recurring_scan(cfg, require_fresh_control=True) == 0
    second = git_repo.git("show", "main:coga/log.md", cwd=git_repo.origin)

    created = second.count("created recurring/z-script-check")
    assert created == first.count("created recurring/z-script-check") == 1


def test_recurring_all_scan_services_detached_checkout_from_worktree(
    git_repo, capsys
) -> None:
    """A detached HEAD leaves the control branch free, so it is serviceable.

    This replaced an assertion that a detached checkout returns
    `STALE_CONTROL_EXIT_CODE`: the branch not being checked out anywhere is
    now the trigger for the temp worktree, not a reason to fail the repo.
    """
    _seed_recipe_template_on_control(git_repo)
    git_repo.git("checkout", "--detach")
    before = _checkout_state(git_repo)

    cfg = load_config(git_repo.coga_os)
    assert recurring_cmd.run_recurring_scan(cfg, require_fresh_control=True) == 0

    assert _checkout_state(git_repo) == before
    assert _control_serviced_period(git_repo, "z-script-check") is not None
    assert "detached HEAD" in capsys.readouterr().out


def test_control_worktree_is_removed_and_unregistered_after_the_run(
    git_repo
) -> None:
    """No stranded checkout, and no registration pinning the control branch."""
    _seed_recipe_template_on_control(git_repo)
    git_repo.checkout_branch("agent/parked-work")

    cfg = load_config(git_repo.coga_os)
    assert recurring_cmd.run_recurring_scan(cfg, require_fresh_control=True) == 0

    listing = git_repo.git("worktree", "list", "--porcelain")
    assert recurring_cmd._CONTROL_WORKTREE_PREFIX not in listing
    assert coga_git._worktree_holding_branch(git_repo.root, "main") is None
    leftovers = list(
        Path(tempfile.gettempdir()).glob(
            f"{recurring_cmd._CONTROL_WORKTREE_PREFIX}{git_repo.root.name}-*"
        )
    )
    assert leftovers == []


def test_control_worktree_is_removed_when_the_inner_run_fails(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cleanup is a `finally`, not a success path."""
    _seed_recipe_template_on_control(git_repo)
    git_repo.checkout_branch("agent/parked-work")
    monkeypatch.setattr(
        recurring_cmd, "_run_repo_recurring", lambda *a, **k: 17
    )

    cfg = load_config(git_repo.coga_os)
    assert recurring_cmd.run_recurring_scan(cfg, require_fresh_control=True) == 17

    assert coga_git._worktree_holding_branch(git_repo.root, "main") is None


def test_control_worktree_is_removed_when_the_inner_run_raises(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise KeyboardInterrupt("terminated by signal 15")

    _seed_recipe_template_on_control(git_repo)
    git_repo.checkout_branch("agent/parked-work")
    monkeypatch.setattr(recurring_cmd, "_run_repo_recurring", explode)

    cfg = load_config(git_repo.coga_os)
    with pytest.raises(KeyboardInterrupt):
        recurring_cmd.run_recurring_scan(cfg, require_fresh_control=True)

    assert coga_git._worktree_holding_branch(git_repo.root, "main") is None


def test_control_worktree_reaps_cancelled_child_before_removal(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SIGTERM-style interruption cannot leave the inner scan running."""
    _seed_recipe_template_on_control(git_repo)
    git_repo.checkout_branch("agent/parked-work")

    class InterruptedProcess:
        pid = 4242
        terminated = False
        reaped = False

        def poll(self):  # type: ignore[no-untyped-def]
            return -15 if self.reaped else None

        def wait(self, timeout=None):  # type: ignore[no-untyped-def]
            if not self.terminated:
                raise KeyboardInterrupt("terminated by signal 15")
            assert timeout == recurring_cmd._CONTROL_WORKTREE_STOP_TIMEOUT
            self.reaped = True
            return -15

    process = InterruptedProcess()
    signals: list[tuple[int, int]] = []

    def signal_group(child, signum):  # type: ignore[no-untyped-def]
        assert child is process
        signals.append((child.pid, signum))
        process.terminated = True

    monkeypatch.setattr(
        recurring_cmd,
        "_start_repo_recurring_process",
        lambda *args, **kwargs: process,
    )
    monkeypatch.setattr(
        recurring_cmd,
        "_signal_repo_recurring_process_group",
        signal_group,
    )
    monkeypatch.setattr(
        recurring_cmd,
        "_repo_recurring_process_group_exists",
        lambda child: child is process and child.reaped,
    )
    real_run_git = coga_git._run_git

    def observe_cleanup(root, *args, **kwargs):  # type: ignore[no-untyped-def]
        if args[:3] == ("worktree", "remove", "--force"):
            assert process.reaped
        return real_run_git(root, *args, **kwargs)

    monkeypatch.setattr(coga_git, "_run_git", observe_cleanup)

    cfg = load_config(git_repo.coga_os)
    with pytest.raises(KeyboardInterrupt):
        recurring_cmd.run_recurring_scan(cfg, require_fresh_control=True)

    assert process.terminated
    assert process.reaped
    assert signals == [
        (process.pid, recurring_cmd.signal.SIGTERM),
        (process.pid, recurring_cmd.signal.SIGKILL),
    ]
    assert coga_git._worktree_holding_branch(git_repo.root, "main") is None


def test_control_worktree_reaps_a_present_checkout_stranded_by_sigkill(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dead owned checkout is removed even while its directory still exists."""
    _seed_recipe_template_on_control(git_repo)
    git_repo.checkout_branch("agent/parked-work")
    parent = Path(
        tempfile.mkdtemp(
            prefix=(
                f"{recurring_cmd._CONTROL_WORKTREE_PREFIX}"
                f"{git_repo.root.name}-"
            )
        )
    )
    stranded = parent / "checkout"
    recurring_cmd._write_control_worktree_owner(
        parent, git_repo.root, "main", pid=424242
    )
    git_repo.git("worktree", "add", str(stranded), "main")
    monkeypatch.setattr(recurring_cmd, "_process_is_running", lambda _pid: False)

    cfg = load_config(git_repo.coga_os)
    assert recurring_cmd.run_recurring_scan(cfg, require_fresh_control=True) == 0
    assert _control_serviced_period(git_repo, "z-script-check") is not None
    assert not parent.exists()


def test_control_worktree_does_not_reap_a_live_owned_checkout(
    git_repo, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """The stale-run recovery never tears down a concurrent live sweep."""
    _seed_recipe_template_on_control(git_repo)
    git_repo.checkout_branch("agent/parked-work")
    parent = Path(
        tempfile.mkdtemp(
            prefix=(
                f"{recurring_cmd._CONTROL_WORKTREE_PREFIX}"
                f"{git_repo.root.name}-"
            )
        )
    )
    holder = parent / "checkout"
    recurring_cmd._write_control_worktree_owner(
        parent, git_repo.root, "main", pid=31337
    )
    git_repo.git("worktree", "add", str(holder), "main")
    monkeypatch.setattr(recurring_cmd, "_process_is_running", lambda _pid: True)

    try:
        cfg = load_config(git_repo.coga_os)
        assert recurring_cmd.run_recurring_scan(
            cfg, require_fresh_control=True
        ) == coga_git.STALE_CONTROL_EXIT_CODE

        assert holder.is_dir()
        assert str(holder) in capsys.readouterr().err
    finally:
        git_repo.git("worktree", "remove", "--force", str(holder))
        shutil.rmtree(parent, ignore_errors=True)


def test_control_worktree_refuses_when_another_worktree_holds_control(
    git_repo, tmp_path: Path, capsys
) -> None:
    """Git's one-checkout-per-branch rule *is* the concurrency lock.

    A second sweep over the same repo — or any unrelated worktree already on
    the control branch — loses the race here and keeps today's loud refusal
    rather than racing period state.
    """
    _seed_recipe_template_on_control(git_repo)
    git_repo.checkout_branch("agent/parked-work")
    holder = tmp_path / "other" / "checkout"
    git_repo.git("worktree", "add", str(holder), "main")

    cfg = load_config(git_repo.coga_os)
    assert recurring_cmd.run_recurring_scan(
        cfg, require_fresh_control=True
    ) == coga_git.STALE_CONTROL_EXIT_CODE

    error = capsys.readouterr().err
    assert "temporary control worktree" in error
    assert str(holder) in error
    assert f"git -C {git_repo.root} checkout main" in error
    assert list_tasks(cfg) == []


def test_control_worktree_is_outside_any_plausible_all_scan_root(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A concurrent `--all` must never discover the temp checkout as a repo."""
    _seed_recipe_template_on_control(git_repo)
    git_repo.checkout_branch("agent/parked-work")
    seen: list[Path] = []

    def observe(coga_os: Path, **kwargs):  # type: ignore[no-untyped-def]
        seen.append(coga_os)
        # While the checkout is live, a sweep of the host tree still finds only
        # the operator's own workspace.
        assert discover_coga_repos(git_repo.root.parent) == [git_repo.coga_os]
        return 0

    monkeypatch.setattr(recurring_cmd, "_run_repo_recurring", observe)
    cfg = load_config(git_repo.coga_os)
    assert recurring_cmd.run_recurring_scan(cfg, require_fresh_control=True) == 0

    assert len(seen) == 1
    assert seen[0].is_relative_to(Path(tempfile.gettempdir()))
    assert not seen[0].is_relative_to(git_repo.root.parent)


def test_control_worktree_flag_stops_the_recursion(
    git_repo, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """The inner run refuses exactly as before instead of nesting worktrees."""
    git_repo.checkout_branch("agent/parked-work")
    monkeypatch.setattr(
        recurring_cmd,
        "_service_from_control_worktree",
        lambda *args, **kwargs: pytest.fail("inner run must not recurse"),
    )

    cfg = load_config(git_repo.coga_os)
    assert recurring_cmd.run_recurring_scan(
        cfg, require_fresh_control=True, control_worktree=True
    ) == coga_git.STALE_CONTROL_EXIT_CODE
    assert "Recurring scan skipped" in capsys.readouterr().err


def test_control_worktree_run_names_agent_templates_and_the_real_reason(
    git_repo, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Agent templates are skipped for the true reason, not "requires a TTY".

    They are excluded whether or not a TTY exists, so the run is driven with
    one present — the old message would have been a lie.
    """
    coga_os = git_repo.coga_os
    (coga_os / "coga.local.toml").write_text(
        'user = "marc"\n[notification.slack]\nenabled = false\n'
    )
    _seed_period_task_context(coga_os)
    _seed_agent_workflow(coga_os)
    _write_recurring_agent(
        coga_os, "agent-check", schedule="* * * * *", title="Agent check"
    )
    monkeypatch.setattr(
        "coga.recurring_runner._interactive_stdio_has_tty", lambda: True
    )

    cfg = load_config(coga_os)
    assert recurring_cmd.run_recurring_scan(
        cfg,
        require_fresh_control=True,
        control_worktree=True,
        control_worktree_host="/home/op/project",
    ) == 0

    combined = capsys.readouterr()
    reported = combined.out + combined.err
    assert "agent-check" in reported
    assert "temporary control worktree" in reported
    assert "/home/op/project" in reported
    assert "requires a TTY" not in reported
    assert list_tasks(cfg) == []


def test_off_control_catchup_names_the_checkout_remedy(git_repo) -> None:
    """Independently shippable: the diagnosis now carries its own fix."""
    git_repo.checkout_branch("agent/parked-work")
    cfg = load_config(git_repo.coga_os)

    catchup = recurring_cmd._sync_control_checkout_ahead(
        cfg, announce_failure=False
    )

    assert not catchup.fresh
    assert catchup.off_control_branch
    assert "branch 'agent/parked-work'" in catchup.reason
    assert f"git -C {git_repo.root} checkout main" in catchup.reason


def test_diverged_control_is_not_an_off_control_branch_refusal(
    git_repo, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """The `fetched == True` arm keeps failing loud — it is out of scope."""
    def fail_fetch(*args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        raise coga_git.GitError("simulated rebase conflict")

    monkeypatch.setattr(recurring_cmd, "_fetch_control_branch", fail_fetch)
    monkeypatch.setattr(
        recurring_cmd,
        "_service_from_control_worktree",
        lambda *args, **kwargs: pytest.fail("a held control branch must not recurse"),
    )

    cfg = load_config(git_repo.coga_os)
    assert recurring_cmd.run_recurring_scan(
        cfg, require_fresh_control=True
    ) == coga_git.STALE_CONTROL_EXIT_CODE
    assert "simulated rebase conflict" in capsys.readouterr().err


def test_bare_and_named_sweeps_keep_refusing_off_control(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the `require_fresh_control` child changes; single-repo runs don't."""
    git_repo.checkout_branch("agent/parked-work")
    monkeypatch.setattr(
        recurring_cmd,
        "_service_from_control_worktree",
        lambda *args, **kwargs: pytest.fail("single-repo runs must not recurse"),
    )

    cfg = load_config(git_repo.coga_os)
    assert recurring_cmd.run_recurring_scan(cfg) == 2
    assert recurring_cmd.run_recurring_named(cfg, "z-script-check") == 2


def test_repo_recurring_dispatch_threads_the_control_worktree_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    coga_os = tmp_path / "project" / "coga"
    _write(coga_os / "coga.toml", "version = 1\n")
    captured: dict[str, object] = {}

    class CompletedProcess:
        def wait(self, timeout=None):  # type: ignore[no-untyped-def]
            assert timeout is None
            return 0

    def fake_start(command, cwd, env):  # type: ignore[no-untyped-def]
        captured["command"] = command
        captured["cwd"] = cwd
        captured["env"] = env
        return CompletedProcess()

    monkeypatch.setattr(recurring_cmd, "_start_repo_recurring_process", fake_start)

    assert recurring_cmd._run_repo_recurring(
        coga_os,
        force=False,
        interactive=False,
        agent_override=None,
        control_worktree=True,
        control_worktree_host="/home/op/project",
        cwd=tmp_path / "elsewhere",
    ) == 0

    assert captured["command"] == [
        recurring_cmd.sys.executable,
        "-m",
        "coga.cli",
        "run",
        "recurring-scan",
        "--require-fresh-control",
        "--control-worktree",
        "--control-worktree-host",
        "/home/op/project",
    ]
    assert captured["cwd"] == tmp_path / "elsewhere"


def test_control_worktree_child_starts_in_an_isolated_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cancellation can address the inner scan and all recipe descendants."""
    captured: dict[str, object] = {}
    expected = object()

    def fake_popen(command, **kwargs):  # type: ignore[no-untyped-def]
        captured["command"] = command
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(recurring_cmd.subprocess, "Popen", fake_popen)

    actual = recurring_cmd._start_repo_recurring_process(
        ["coga", "run", "recurring-scan"], tmp_path, {"PATH": "/bin"}
    )

    assert actual is expected
    assert captured["cwd"] == tmp_path
    assert captured["start_new_session"] is True


def test_recurring_all_summary_names_repos_serviced_from_a_control_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The parent distinguishes a temp-worktree service from an ordinary sweep."""
    parked = init_git_repo(tmp_path / "parked")
    ordinary = init_git_repo(tmp_path / "ordinary")
    parked.checkout_branch("agent/parked-work")
    monkeypatch.setattr(recurring_cmd, "_run_repo_recurring", lambda *a, **k: 0)

    result = CliRunner().invoke(app, ["recurring", "--all", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "serviced from a temporary control worktree" in result.output
    assert "recipe templates only" in result.output
    # The on-control repo is an ordinary sweep and must not be listed.
    listed = result.output.split("recipe templates only")[-1]
    assert "parked/repo" in listed
    assert "ordinary/repo" not in listed


def test_recurring_all_summary_omits_a_failed_off_control_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only a zero exit proves the temp worktree actually serviced the repo."""
    parked = init_git_repo(tmp_path / "parked")
    parked.checkout_branch("agent/parked-work")
    monkeypatch.setattr(
        recurring_cmd,
        "_run_repo_recurring",
        lambda *a, **k: coga_git.STALE_CONTROL_EXIT_CODE,
    )

    result = CliRunner().invoke(app, ["recurring", "--all", str(tmp_path)])

    assert result.exit_code == 1
    assert "serviced from a temporary control worktree" not in result.output
