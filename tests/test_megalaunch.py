from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from coga.cli import app
from coga.config import load_config
from coga.create import create_task
from coga.megalaunch import run_megalaunch, trim_megalaunch_blackboard_text
from coga.ticket import Ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    company = tmp_path / "coga"
    _write(
        company / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [git]
        enabled = false
        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        [agents.codex]
        cli = "codex"
        file = "AGENTS.md"
        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')
    _write(
        company / "workflows" / "code.md",
        """
        ---
        name: code
        description: tiny.
        steps:
          - name: implement
            assignee: agent
          - name: review
            assignee: owner
        ---
        """,
    )
    monkeypatch.chdir(company)
    # The engine refuses to run without a TTY (it spawns interactive REPLs);
    # pytest has none, so stub the check for the launch-path tests.
    monkeypatch.setattr(
        "coga.megalaunch._interactive_stdio_has_tty", lambda: True
    )
    return company


def test_megalaunch_runs_active_agent_task(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Run me",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )

    monkeypatch.setattr(
        "coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}"
    )

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(  # type: ignore[no-untyped-def]
        cfg, ref_obj, ticket, agent, **kwargs
    ):
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "done"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg)

    assert run.counts["launched"] == 1
    assert run.counts["completed"] == 1
    assert run.results[0].slug == ref["slug"]
    assert Ticket.read(ref["path"]).status == "done"


def test_megalaunch_skips_task_deleted_mid_sweep(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The queue is snapshotted up front, and a session launched earlier in the
    # sweep may reap a finished task (retire deletes the source directory).
    # The stale ref must be skipped, not crash the sweep or count as failed.
    cfg = load_config(repo)
    first = create_task(
        cfg=cfg,
        title="A run me",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    doomed = create_task(
        cfg=cfg,
        title="B reaped mid-sweep",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )

    monkeypatch.setattr(
        "coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}"
    )

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(  # type: ignore[no-untyped-def]
        cfg, ref_obj, ticket, agent, **kwargs
    ):
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "done"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        # The first session reaps the other task, like retire does.
        doomed_path = Path(doomed["path"])
        doomed_path.unlink()
        if doomed_path.name == "ticket.md":
            doomed_path.parent.rmdir()
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg)

    assert run.counts["launched"] == 1
    assert run.counts["completed"] == 1
    assert run.counts.get("failed", 0) == 0
    assert [r.slug for r in run.results] == [first["slug"]]


def test_megalaunch_chains_agent_owned_steps(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        repo / "workflows" / "two-agent.md",
        """
        ---
        name: two-agent
        description: two agent steps.
        steps:
          - name: implement
            assignee: agent
          - name: verify
            assignee: agent
        ---
        """,
    )
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Run twice",
        workflow_name="two-agent",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    monkeypatch.setattr(
        "coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}"
    )

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    seen_steps: list[str] = []

    def fake_spawn(  # type: ignore[no-untyped-def]
        cfg, ref_obj, ticket, agent, **kwargs
    ):
        updated = Ticket.read(ref_obj.ticket_path)
        seen_steps.append(updated.step or "")
        if updated.step == "1 (implement)":
            updated.frontmatter["step"] = "2 (verify)"
            updated.frontmatter["assignee"] = "claude"
        else:
            updated.frontmatter["status"] = "done"
            updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg)

    assert seen_steps == ["1 (implement)", "2 (verify)"]
    assert run.counts["completed"] == 1
    assert Ticket.read(ref["path"]).status == "done"


def test_megalaunch_agent_override_launches_regardless_of_assignee(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`agent_override` is ephemeral: every swept ticket launches with the
    named agent, whatever its `assignee:` says, and the ticket is never
    rewritten — the same semantics as `coga launch --agent`."""
    cfg = load_config(repo)
    claude_ref = create_task(
        cfg=cfg,
        title="Claude work",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    codex_ref = create_task(
        cfg=cfg,
        title="Codex work",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="codex",
        status="active",
        watchers=[],
    )

    monkeypatch.setattr(
        "coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}"
    )

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    launched: list[tuple[str, str]] = []

    def fake_spawn(cfg, ref_obj, ticket, agent, **kwargs):  # type: ignore[no-untyped-def]
        launched.append((ref_obj.id_slug, agent.cli))
        assignee_on_disk = Ticket.read(ref_obj.ticket_path).assignee
        assert assignee_on_disk == ticket.assignee, "override must not rewrite assignee"
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "done"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg, agent_override="codex")

    assert run.agent_override == "codex"
    # Both tickets launch — the claude-assigned one included — and both as codex.
    assert sorted(launched) == sorted(
        [(claude_ref["slug"], "codex"), (codex_ref["slug"], "codex")]
    )
    assert run.counts["launched"] == 2
    assert run.counts["completed"] == 2
    assert Ticket.read(claude_ref["path"]).status == "done"
    assert Ticket.read(codex_ref["path"]).status == "done"


def test_megalaunch_only_sweeps_current_users_tickets(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The sweep is scoped to the running operator (`cfg.current_user`, here
    `marc`). A ticket owned by someone else is not launched and never enters
    `results`, so it doesn't inflate the summary counts."""
    cfg = load_config(repo)
    mine = create_task(
        cfg=cfg,
        title="My work",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    theirs = create_task(
        cfg=cfg,
        title="Their work",
        workflow_name="code",
        contexts=[],
        owner="dora",
        assignee="claude",
        status="active",
        watchers=[],
    )

    monkeypatch.setattr(
        "coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}"
    )

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    launched: list[str] = []

    def fake_spawn(cfg, ref_obj, ticket, agent, **kwargs):  # type: ignore[no-untyped-def]
        launched.append(ref_obj.id_slug)
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "done"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg)

    assert launched == [mine["slug"]]
    assert [result.slug for result in run.results] == [mine["slug"]]
    assert run.counts["launched"] == 1
    assert run.counts["completed"] == 1
    assert Ticket.read(mine["path"]).status == "done"
    # The other owner's ticket is untouched — not launched, not counted.
    assert Ticket.read(theirs["path"]).status == "active"


def test_megalaunch_agent_override_applies_to_first_step_only(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Like `coga launch --agent`, the override covers only the task's first
    launched step; a chained later step runs the ticket's resolved assignee,
    so `other-agent` rotation keeps its meaning."""
    _write(
        repo / "workflows" / "two-agent.md",
        """
        ---
        name: two-agent
        description: two agent steps.
        steps:
          - name: implement
            assignee: agent
          - name: verify
            assignee: agent
        ---
        """,
    )
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Chained",
        workflow_name="two-agent",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    seen: list[tuple[str, str]] = []

    def fake_spawn(cfg, ref_obj, ticket, agent, **kwargs):  # type: ignore[no-untyped-def]
        updated = Ticket.read(ref_obj.ticket_path)
        seen.append((updated.step or "", agent.cli))
        if updated.step == "1 (implement)":
            updated.frontmatter["step"] = "2 (verify)"
        else:
            updated.frontmatter["status"] = "done"
            updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg, agent_override="codex")

    assert seen == [("1 (implement)", "codex"), ("2 (verify)", "claude")]
    assert run.counts["launched"] == 1
    assert run.counts["completed"] == 1
    assert Ticket.read(ref["path"]).status == "done"


def test_megalaunch_cli_accepts_agent_override(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--agent codex` drains a claude-assigned ticket by running it as codex."""
    from typer.testing import CliRunner

    cfg = load_config(repo)
    claude_ref = create_task(
        cfg=cfg,
        title="Claude CLI work",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )

    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(
        "coga.commands.megalaunch.notification.post", lambda cfg, msg: None
    )

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    launched_cli: list[str] = []

    def fake_spawn(  # type: ignore[no-untyped-def]
        cfg, ref_obj, ticket, agent, **kwargs
    ):
        launched_cli.append(agent.cli)
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "done"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    result = CliRunner().invoke(app, ["megalaunch", "--agent", "codex"])

    assert result.exit_code == 0, result.output
    assert "Agent override: codex" in result.output
    assert claude_ref["slug"] in result.output
    assert launched_cli == ["codex"]
    assert Ticket.read(claude_ref["path"]).status == "done"


def test_megalaunch_agent_override_keeps_human_gate(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The override never converts a human-assigned ticket into an agent step."""
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Parked on a human",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    ticket = Ticket.read(ref["path"])
    ticket.frontmatter["assignee"] = "marc"
    ticket.write(ref["path"])

    def fail_spawn(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("override must not launch a human-assigned ticket")

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fail_spawn)
    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")

    run = run_megalaunch(cfg, agent_override="codex")

    assert run.counts["launched"] == 0
    assert run.counts["skipped-human-gate"] == 1
    assert "marc" in run.results[0].detail


def test_megalaunch_directory_scopes_the_sweep(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`directory` narrows the queue to that tasks/ sub-tree, like `coga status <dir>`."""
    cfg = load_config(repo)
    inside = create_task(
        cfg=cfg,
        title="In scope",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
        directory="marketing",
    )
    outside = create_task(
        cfg=cfg,
        title="Out of scope",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )

    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(  # type: ignore[no-untyped-def]
        cfg, ref_obj, ticket, agent, **kwargs
    ):
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "done"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg, directory="marketing")

    assert run.directory == "marketing"
    assert [result.slug for result in run.results] == [inside["slug"]]
    assert Ticket.read(inside["path"]).status == "done"
    assert Ticket.read(outside["path"]).status == "active"


def test_megalaunch_unknown_directory_fails_loud(repo: Path) -> None:
    """A directory that doesn't exist under tasks/ raises, never sweeps nothing silently."""
    from coga.tasks import UnknownDirectoryError

    cfg = load_config(repo)

    with pytest.raises(UnknownDirectoryError):
        run_megalaunch(cfg, directory="nope")


def test_megalaunch_cli_accepts_directory(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    cfg = load_config(repo)
    inside = create_task(
        cfg=cfg,
        title="Scoped work",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
        directory="marketing",
    )
    outside = create_task(
        cfg=cfg,
        title="Other work",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )

    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(
        "coga.commands.megalaunch.notification.post", lambda cfg, msg: None
    )

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(  # type: ignore[no-untyped-def]
        cfg, ref_obj, ticket, agent, **kwargs
    ):
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "done"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    result = CliRunner().invoke(app, ["megalaunch", "marketing"])

    assert result.exit_code == 0, result.output
    assert "Directory: marketing" in result.output
    assert inside["slug"] in result.output
    assert Ticket.read(inside["path"]).status == "done"
    assert Ticket.read(outside["path"]).status == "active"

    bad = CliRunner().invoke(app, ["megalaunch", "nope"])
    assert bad.exit_code == 2


def test_megalaunch_requires_tty(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Headless runs fail loud — the interactive REPLs need a real terminal."""
    from coga.megalaunch import MegalaunchError

    monkeypatch.setattr(
        "coga.megalaunch._interactive_stdio_has_tty", lambda: False
    )
    cfg = load_config(repo)

    with pytest.raises(MegalaunchError, match="TTY"):
        run_megalaunch(cfg)


def test_megalaunch_spawns_llm_with_liveness_backstop(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each step is a normal Agent launch with the recurring liveness backstop."""
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Watch me",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")

    class _Session:
        exit_code = 0
        termination_kind = "done"

    seen: dict[str, object] = {}

    def fake_spawn(cfg, ref_obj, ticket, agent, **kwargs):  # type: ignore[no-untyped-def]
        seen["idle_timeout"] = kwargs.get("idle_timeout")
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "done"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg)

    assert run.counts["completed"] == 1
    # The recurring sweep's idle backstop is armed so a wedged REPL can't
    # starve the rest of the queue.
    assert seen["idle_timeout"] is not None


def test_megalaunch_timeout_teardown_reports_failed(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A liveness-limit teardown is a distinct failure, not a bare exit code."""
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Wedged",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")

    class _Session:
        exit_code = 124
        termination_kind = "timeout"

    monkeypatch.setattr(
        "coga.megalaunch.spawn_agent_session",
        lambda *args, **kwargs: _Session(),
    )

    run = run_megalaunch(cfg)

    assert run.counts["failed"] == 1
    assert "liveness limit" in run.results[0].detail


def test_megalaunch_skips_open_blocker(repo: Path) -> None:
    from typer.testing import CliRunner

    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Blocked",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    result = CliRunner().invoke(
        app,
        ["block", "--task", ref["slug"], "--reason", "need owner answer"],
    )
    assert result.exit_code == 0, result.output

    run = run_megalaunch(cfg)

    assert run.counts["launched"] == 0
    assert run.counts["skipped-unresolved-blocker"] == 1
    assert "need owner answer" in run.results[0].detail





def test_megalaunch_ignores_non_active_tickets(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """done/draft/paused tickets are ignored — never launched, never `failed`."""
    cfg = load_config(repo)
    for title, status in (
        ("Done", "done"),
        ("Draft", "draft"),
        ("Paused", "paused"),
    ):
        ref = create_task(
            cfg=cfg,
            title=title,
            workflow_name="code",
            contexts=[],
            owner="marc",
            assignee="claude",
            status="active",
            watchers=[],
        )
        ticket = Ticket.read(ref["path"])
        ticket.frontmatter["status"] = status
        if status == "done":
            ticket.frontmatter.pop("step", None)
        ticket.write(ref["path"])

    def fail_spawn(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("megalaunch must not launch a non-active ticket")

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fail_spawn)
    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")

    run = run_megalaunch(cfg)

    assert run.results == []
    assert run.counts["launched"] == 0
    assert run.counts["failed"] == 0


def test_megalaunch_sweep_resumes_in_progress_tickets(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bare sweep resumes an in_progress ticket like `coga launch` would."""
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Crashed mid-step",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    ticket = Ticket.read(ref["path"])
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(ref["path"])

    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(cfg)

    assert launched == [ref["slug"]]
    assert run.counts["launched"] == 1
    assert run.counts["completed"] == 1
    assert Ticket.read(ref["path"]).status == "done"


def test_megalaunch_human_assignee_is_human_gate(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An active ticket parked on a human shows up as skipped-human-gate."""
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="With human",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    ticket = Ticket.read(ref["path"])
    ticket.frontmatter["assignee"] = "marc"
    ticket.write(ref["path"])

    def fail_spawn(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("megalaunch must not launch a human-assigned ticket")

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fail_spawn)
    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")

    run = run_megalaunch(cfg)

    assert run.counts["launched"] == 0
    assert run.counts["skipped-human-gate"] == 1
    assert "marc" in run.results[0].detail



def test_megalaunch_services_tasks_oldest_first(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Drain order is creation order — the first log.md timestamp per ref.

    The log is committed content, so the order survives clone/checkout where
    file mtimes collapse to "all equal".
    """
    from coga.paths import log_path

    cfg = load_config(repo)
    for title in ("Alpha", "Beta"):
        create_task(
            cfg=cfg,
            title=title,
            workflow_name="code",
            contexts=[],
            owner="marc",
            assignee="claude",
            status="active",
            watchers=[],
        )
    # Rewrite the log so beta's create line is a day older than alpha's.
    log_path(cfg).write_text(
        "2026-06-02 10:00 [alpha] [human:marc] created\n"
        "2026-06-01 10:00 [beta] [human:marc] created\n"
    )

    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(cfg_, ref_obj, ticket, agent, **kwargs):  # type: ignore[no-untyped-def]
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "done"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg)

    assert [result.slug for result in run.results] == ["beta", "alpha"]


def test_trim_megalaunch_blackboard_replaces_old_summaries() -> None:
    text = """## Blockers

- [ ] [2026-06-29 10:00] [agent:claude] id=b1 Need answer

## Megalaunch Run Summary

old

## Decisions

Keep this.

## Megalaunch Run Summary

older
"""

    trimmed = trim_megalaunch_blackboard_text(text, "new summary\n")

    assert trimmed.count("## Megalaunch Run Summary") == 1
    assert "new summary" in trimmed
    assert "old" not in trimmed
    assert "older" not in trimmed
    assert "Need answer" in trimmed
    assert "Keep this." in trimmed


# --- explicit selection (picker / slug list / --relaunch) --------------------


def _done_on_spawn(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Stub spawn that marks each launched ticket done; returns launch order."""
    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")
    launched: list[str] = []

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(cfg, ref_obj, ticket, agent, **kwargs):  # type: ignore[no-untyped-def]
        launched.append(ref_obj.id_slug)
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "done"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)
    return launched


def test_megalaunch_selection_resumes_in_progress(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicitly selecting an in_progress ticket is the deliberate resume."""
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Resume me",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    ticket = Ticket.read(ref["path"])
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(ref["path"])

    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(cfg, selection=[ref["slug"]])

    assert launched == [ref["slug"]]
    assert run.counts["completed"] == 1
    assert Ticket.read(ref["path"]).status == "done"


def test_megalaunch_selection_reports_unlaunchable_picks(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A named task that can't launch is reported, never silently dropped."""
    cfg = load_config(repo)
    done = create_task(
        cfg=cfg,
        title="Already finished",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    ticket = Ticket.read(done["path"])
    ticket.frontmatter["status"] = "done"
    ticket.frontmatter.pop("step", None)
    ticket.write(done["path"])
    foreign = create_task(
        cfg=cfg,
        title="Someone else's",
        workflow_name="code",
        contexts=[],
        owner="lea",
        assignee="claude",
        status="active",
        watchers=[],
    )

    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(cfg, selection=[done["slug"], foreign["slug"]])

    assert launched == []
    assert run.counts["skipped-unlaunchable"] == 2
    outcomes = {result.slug: result.detail for result in run.results}
    assert outcomes[done["slug"]] == "status is done"
    assert "owned by lea" in outcomes[foreign["slug"]]


def test_megalaunch_selection_unknown_slug_fails_loud(repo: Path) -> None:
    from coga.megalaunch import MegalaunchError

    cfg = load_config(repo)

    with pytest.raises(MegalaunchError, match="not found"):
        run_megalaunch(cfg, selection=["no-such-task"])


def test_launchable_candidates_lists_active_and_in_progress(repo: Path) -> None:
    """The picker offers the operator's active + in_progress agent tickets."""
    from coga.megalaunch import launchable_candidates

    cfg = load_config(repo)
    active = create_task(
        cfg=cfg,
        title="Active one",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    running = create_task(
        cfg=cfg,
        title="Running one",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    ticket = Ticket.read(running["path"])
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(running["path"])
    create_task(  # draft — never offered
        cfg=cfg,
        title="Still a draft",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )
    create_task(  # someone else's — never offered
        cfg=cfg,
        title="Lea's work",
        workflow_name="code",
        contexts=[],
        owner="lea",
        assignee="claude",
        status="active",
        watchers=[],
    )

    offered = {ref.id_slug for ref, _ in launchable_candidates(cfg)}

    assert offered == {active["slug"], running["slug"]}


def test_save_and_load_selection_roundtrip(repo: Path) -> None:
    from coga.megalaunch import MegalaunchError, load_selection, save_selection

    cfg = load_config(repo)

    with pytest.raises(MegalaunchError, match="No saved selection"):
        load_selection(cfg)

    save_selection(cfg, ["a-task", "dir/another"])

    assert load_selection(cfg) == ["a-task", "dir/another"]
    assert (repo / ".coga" / "megalaunch-selection.json").is_file()


def test_parse_toggle_tokens() -> None:
    from coga.commands.megalaunch import parse_toggle_tokens

    assert parse_toggle_tokens("3", 5) == {2}
    assert parse_toggle_tokens("1 3", 5) == {0, 2}
    assert parse_toggle_tokens("2,4", 5) == {1, 3}
    assert parse_toggle_tokens("0", 5) is None
    assert parse_toggle_tokens("6", 5) is None
    assert parse_toggle_tokens("nope", 5) is None


def test_megalaunch_cli_picker_launches_checked_tasks(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`coga megalaunch --pick` pre-checks everything; toggling excludes a task."""
    from typer.testing import CliRunner

    cfg = load_config(repo)
    first = create_task(
        cfg=cfg,
        title="Keep me checked",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    second = create_task(
        cfg=cfg,
        title="Uncheck me",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )

    monkeypatch.setattr(
        "coga.commands.megalaunch._interactive_stdio_has_tty", lambda: True
    )
    monkeypatch.setattr(
        "coga.commands.megalaunch.notification.post", lambda cfg, msg: None
    )
    launched = _done_on_spawn(monkeypatch)

    # Toggle #2 off, then Enter to launch the remaining selection.
    result = CliRunner().invoke(app, ["megalaunch", "--pick"], input="2\n\n")

    assert result.exit_code == 0, result.output
    assert launched == [first["slug"]]
    assert Ticket.read(first["path"]).status == "done"
    assert Ticket.read(second["path"]).status == "active"
    # The confirmed selection is saved for --relaunch.
    from coga.megalaunch import load_selection

    assert load_selection(cfg) == [first["slug"]]


def test_megalaunch_cli_quit_launches_nothing(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Untouched",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    monkeypatch.setattr(
        "coga.commands.megalaunch._interactive_stdio_has_tty", lambda: True
    )
    launched = _done_on_spawn(monkeypatch)

    result = CliRunner().invoke(app, ["megalaunch", "--pick"], input="q\n")

    assert result.exit_code == 0, result.output
    assert launched == []
    assert "Nothing selected" in result.output
    assert Ticket.read(ref["path"]).status == "active"


def test_megalaunch_cli_pick_scopes_to_directory(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--pick <dir>` only offers tasks under that tasks/ sub-tree."""
    from typer.testing import CliRunner

    cfg = load_config(repo)
    inside = create_task(
        cfg=cfg,
        title="In scope",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
        directory="marketing",
    )
    outside = create_task(
        cfg=cfg,
        title="Out of scope",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    monkeypatch.setattr(
        "coga.commands.megalaunch._interactive_stdio_has_tty", lambda: True
    )
    monkeypatch.setattr(
        "coga.commands.megalaunch.notification.post", lambda cfg, msg: None
    )
    launched = _done_on_spawn(monkeypatch)

    # Enter accepts the pre-checked (dir-scoped) list as-is.
    result = CliRunner().invoke(app, ["megalaunch", "marketing", "--pick"], input="\n")

    assert result.exit_code == 0, result.output
    assert launched == [inside["slug"]]
    assert Ticket.read(outside["path"]).status == "active"


def test_megalaunch_cli_relaunch_replays_saved_selection(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    from coga.megalaunch import save_selection

    cfg = load_config(repo)
    saved = create_task(
        cfg=cfg,
        title="Saved pick",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    other = create_task(
        cfg=cfg,
        title="Never picked",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    save_selection(cfg, [saved["slug"], "since-deleted-task"])
    monkeypatch.setattr(
        "coga.commands.megalaunch.notification.post", lambda cfg, msg: None
    )
    launched = _done_on_spawn(monkeypatch)

    result = CliRunner().invoke(app, ["megalaunch", "--relaunch"])

    assert result.exit_code == 0, result.output
    assert launched == [saved["slug"]]
    assert "since-deleted-task no longer exists" in result.output
    assert Ticket.read(other["path"]).status == "active"


def test_megalaunch_cli_relaunch_without_saved_selection_fails(repo: Path) -> None:
    from typer.testing import CliRunner

    result = CliRunner().invoke(app, ["megalaunch", "--relaunch"])

    assert result.exit_code == 2
    assert "No saved selection" in result.output


def test_megalaunch_cli_flag_conflicts(repo: Path) -> None:
    """--relaunch replays a fixed list — scoping flags alongside it are ambiguous."""
    from typer.testing import CliRunner

    both = CliRunner().invoke(app, ["megalaunch", "--relaunch", "--pick"])
    assert both.exit_code == 2

    scoped = CliRunner().invoke(app, ["megalaunch", "--relaunch", "marketing"])
    assert scoped.exit_code == 2


def test_megalaunch_cli_picker_requires_tty(repo: Path) -> None:
    """--pick without a terminal fails loud instead of hanging on the prompt."""
    from typer.testing import CliRunner

    result = CliRunner().invoke(app, ["megalaunch", "--pick"])

    assert result.exit_code == 2
    assert "TTY" in result.output
