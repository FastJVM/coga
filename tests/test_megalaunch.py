from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from coga.cli import app
from coga.compose import compose_prompt
from coga.config import load_config
from coga.create import create_task
from coga.megalaunch import (
    render_run_summary,
    run_megalaunch,
    trim_megalaunch_blackboard_text,
)
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
        [notification.slack]
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

        ## implement
        Write the code.

        ## review
        Review the code.
        """,
    )
    monkeypatch.chdir(company)
    # The engine refuses to run without a TTY (it spawns interactive REPLs);
    # pytest has none, so stub the check for the launch-path tests.
    monkeypatch.setattr(
        "coga.megalaunch._interactive_stdio_has_tty", lambda: True
    )
    return company


def test_megalaunch_help_describes_drain_order() -> None:
    from typer.testing import CliRunner

    result = CliRunner().invoke(app, ["megalaunch", "--help"])
    help_text = " ".join(result.output.split())

    assert result.exit_code == 0, result.output
    assert "oldest-first" in help_text
    assert "naming convention" in help_text
    assert all(prefix in help_text for prefix in ("1-", "2-", "3-"))


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


def test_megalaunch_spawns_with_materialized_preflight_inputs(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prompt, secret env, and agent are derived only before lifecycle writes."""
    cfg = load_config(repo)
    created = create_task(
        cfg=cfg,
        title="Preflight once",
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
    calls = {"prompt": 0, "env": 0}

    def compose_once(cfg_, ref_, ticket_, **kwargs):  # type: ignore[no-untyped-def]
        calls["prompt"] += 1
        assert ticket_.status == "in_progress"
        return "materialized prompt"

    def env_once(cfg_, secrets):  # type: ignore[no-untyped-def]
        calls["env"] += 1
        return {"SCOPED_SECRET": "materialized value"}

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(  # type: ignore[no-untyped-def]
        _cfg, ref_obj, ticket, agent, **kwargs
    ):
        assert ticket.status == "in_progress"
        assert agent.name == "claude"
        assert kwargs["composed_prompt"] == "materialized prompt"
        assert kwargs["env"]["SCOPED_SECRET"] == "materialized value"
        assert kwargs["env"]["COGA_SUPERVISED"] == "1"
        completed = Ticket.read(ref_obj.ticket_path)
        completed.frontmatter["status"] = "done"
        completed.frontmatter.pop("step", None)
        completed.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.compose_prompt", compose_once)
    monkeypatch.setattr("coga.megalaunch.build_launch_env", env_once)
    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg)

    assert run.results[0].slug == created["slug"]
    assert run.results[0].outcome == "completed"
    assert calls == {"prompt": 1, "env": 1}


def test_megalaunch_step_env_proves_single_checkout_owns_live_ticket(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The expected-task witness admits the supported single-checkout path."""
    from coga.open_pr import _checkout_mode
    from coga.repl_supervisor import EXPECTED_STEP_ENV, EXPECTED_TASK_ENV

    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Publish me",
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
    monkeypatch.setattr("coga.open_pr.same_git_checkout", lambda *args: True)
    monkeypatch.setattr("coga.open_pr.is_linked_worktree", lambda *args: False)

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    captured_env: dict[str, str] = {}
    ownership: tuple[bool, str | None] | None = None

    def fake_spawn(cfg_, ref_obj, ticket, agent, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal ownership
        captured_env.update(kwargs["env"])
        with monkeypatch.context() as child:
            for key, value in captured_env.items():
                child.setenv(key, value)
            ownership = _checkout_mode(
                cfg_,
                recorded_worktree=str(cfg_.repo_root),
                task_path=ref_obj.path,
            )
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "done"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg)

    assert run.counts["completed"] == 1
    assert captured_env[EXPECTED_TASK_ENV] == str(Path(ref["path"]).resolve())
    assert captured_env[EXPECTED_STEP_ENV] == "1 (implement)"
    assert ownership == (True, None)


def test_megalaunch_step_env_refuses_stale_step_bump(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A child cannot advance again after another session moves its step."""
    from typer.testing import CliRunner

    from coga.repl_supervisor import EXPECTED_STEP_ENV, EXPECTED_TASK_ENV

    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Do not double bump",
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
        termination_kind = "natural"

        def __init__(self, exit_code: int) -> None:
            self.exit_code = exit_code

    captured_env: dict[str, str] = {}
    bump_results = []

    def fake_spawn(cfg_, ref_obj, ticket, agent, **kwargs):  # type: ignore[no-untyped-def]
        captured_env.update(kwargs["env"])
        advanced = Ticket.read(ref_obj.ticket_path)
        advanced.frontmatter["step"] = "2 (review)"
        advanced.write(ref_obj.ticket_path)
        result = CliRunner().invoke(
            app,
            ["bump", ref_obj.id_slug],
            env=captured_env,
        )
        bump_results.append(result)
        return _Session(result.exit_code)

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg)

    assert captured_env[EXPECTED_TASK_ENV] == str(Path(ref["path"]).resolve())
    assert captured_env[EXPECTED_STEP_ENV] == "1 (implement)"
    assert len(bump_results) == 1
    assert bump_results[0].exit_code == 2, bump_results[0].output
    assert "Refusing to bump" in bump_results[0].output
    assert "composed for step '1 (implement)'" in bump_results[0].output
    assert "now on step '2 (review)'" in bump_results[0].output
    assert Ticket.read(ref["path"]).step == "2 (review)"
    assert run.counts["failed"] == 1


def test_megalaunch_records_cancellation_as_distinct_outcome(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Decline during run",
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
        updated.frontmatter["status"] = "canceled"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg)

    assert run.counts["launched"] == 1
    assert run.counts["canceled"] == 1
    assert run.counts["completed"] == 0
    assert run.results[0].outcome == "canceled"
    assert run.results[0].detail == "task canceled"
    assert Ticket.read(ref["path"]).status == "canceled"


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

        ## implement
        Write the code.

        ## verify
        Verify the code.
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
            updated.frontmatter.pop("launch_generation", None)
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
    rewritten. Megalaunch separately gates human-owned steps."""
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

        ## implement
        Write the code.

        ## verify
        Verify the code.
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
            updated.frontmatter.pop("launch_generation", None)
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
        seen["prompt_suffix"] = kwargs.get("prompt_suffix", "")
        seen["launch_context"] = kwargs.get("launch_context")
        seen["prompt"] = compose_prompt(
            cfg, ref_obj, ticket, launch_context=kwargs["launch_context"]
        )
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
    # Conduct is the selected composition layer, not an appended suffix.
    assert seen["launch_context"] == "megalaunch"
    assert seen["prompt_suffix"] == ""
    prompt = " ".join(str(seen["prompt"]).split())
    assert "Session conduct — megalaunch queue" in prompt
    assert "Do not ask for plan" in prompt
    assert "Do not ask-and-wait for missing input here" in prompt
    # Unavailable input must end in a terminal `coga block`.
    assert (
        'run `coga block --task <slug> --reason "<specific ask>"` as the'
        " terminal action" in prompt
    )
    assert "include that task's exact path-qualified slug" in prompt
    # ...and the attended contract is simply not composed, so nothing has to
    # rank one against the other.
    assert "A human launched this session and is present in the REPL." not in prompt


@pytest.mark.parametrize(
    "termination_reason",
    [
        "idle-timeout (no REPL activity for 900s)",
        "max-session (wall-clock exceeded 1200s)",
    ],
)
def test_megalaunch_timeout_teardown_names_exact_limit(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    termination_reason: str,
) -> None:
    """A liveness teardown reports the exact trigger, not a generic timeout."""
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

        def __init__(self, reason: str) -> None:
            self.termination_reason = reason

    monkeypatch.setattr(
        "coga.megalaunch.spawn_agent_session",
        lambda *args, **kwargs: _Session(termination_reason),
    )

    run = run_megalaunch(cfg)

    assert run.counts["failed"] == 1
    assert run.results[0].detail == (
        f"agent hit {termination_reason} without signalling done"
    )


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


@pytest.mark.parametrize(
    ("late_change", "expected_outcome", "expected_detail"),
    [
        ("owner", "skipped-human-gate", "is not current operator marc"),
        ("blocker", "skipped-unresolved-blocker", "Late blocker"),
        ("step", "skipped-human-gate", "no current workflow step"),
        ("paused", "skipped-unlaunchable", "status is paused"),
        ("draft", "skipped-unlaunchable", "status is draft"),
    ],
)
def test_megalaunch_reapplies_sweep_gates_to_exact_ticket_bytes(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    late_change: str,
    expected_outcome: str,
    expected_detail: str,
) -> None:
    """A queue candidate cannot outrun a later owner/blocker/step edit."""
    from coga import megalaunch as megalaunch_module
    from coga.blackboard import append_blocker

    cfg = load_config(repo)
    created = create_task(
        cfg=cfg,
        title=f"Late {late_change} gate",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    ticket_path = Path(created["path"])
    real_candidate = megalaunch_module._candidate_result
    changed = False

    def candidate_then_peer_edit(
        cfg_, ref_, ticket_, **kwargs
    ):  # type: ignore[no-untyped-def]
        nonlocal changed
        result = real_candidate(cfg_, ref_, ticket_, **kwargs)
        if ref_.id_slug != created["slug"] or changed:
            return result
        assert kwargs["explicit"] is False
        assert result is None
        changed = True
        if late_change == "blocker":
            append_blocker(
                ticket_path,
                actor="claude",
                reason="Late blocker",
            )
        elif late_change in {"owner", "step"}:
            peer = Ticket.read(ticket_path)
            if late_change == "owner":
                peer.frontmatter["owner"] = "lea"
            else:
                peer.frontmatter.pop("step", None)
            peer.write(ticket_path)
        else:
            peer = Ticket.read(ticket_path)
            peer.frontmatter["status"] = late_change
            peer.write(ticket_path)
        return result

    def fail_spawn(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("an exact-ticket gate refusal must not spawn")

    monkeypatch.setattr(
        "coga.megalaunch._candidate_result", candidate_then_peer_edit
    )
    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fail_spawn)
    monkeypatch.setattr(
        "coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}"
    )

    run = run_megalaunch(cfg)

    assert changed
    assert len(run.results) == 1
    assert run.results[0].outcome == expected_outcome
    assert expected_detail in run.results[0].detail
    assert not run.results[0].launched


def test_megalaunch_late_park_does_not_consume_attempt_budget(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A candidate paused before exact reread leaves max-tasks for real work."""
    from coga import megalaunch as megalaunch_module

    cfg = load_config(repo)
    first = create_task(
        cfg=cfg,
        title="A first candidate",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    second = create_task(
        cfg=cfg,
        title="B actual launch",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    real_candidate = megalaunch_module._candidate_result
    parked = False

    def park_after_queue_check(
        cfg_, ref_, ticket_, **kwargs
    ):  # type: ignore[no-untyped-def]
        nonlocal parked
        result = real_candidate(cfg_, ref_, ticket_, **kwargs)
        if ref_.id_slug == first["slug"] and not parked:
            assert result is None
            parked = True
            peer = Ticket.read(first["path"])
            peer.frontmatter["status"] = "paused"
            peer.write(first["path"])
        return result

    monkeypatch.setattr("coga.megalaunch._candidate_result", park_after_queue_check)
    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(cfg, max_tasks=1)

    assert parked
    assert launched == [second["slug"]]
    assert [result.outcome for result in run.results] == [
        "skipped-unlaunchable",
        "completed",
    ]


def test_megalaunch_drains_blocker_after_dependency_finishes(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A blocker skipped early in the sweep relaunches after its dependency."""
    from coga import megalaunch as megalaunch_module
    from coga.blackboard import append_blocker, open_blockers, read_blockers

    cfg = load_config(repo)
    blocked = create_task(
        cfg=cfg,
        title="Blocked first",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    dependency = create_task(
        cfg=cfg,
        title="Dependency",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    append_blocker(
        Path(blocked["path"]),
        actor="claude",
        reason=f"Waiting for {dependency['slug']} to land",
    )
    ticket = Ticket.read(blocked["path"])
    ticket.frontmatter["status"] = "blocked"
    ticket.write(blocked["path"])

    launched = _done_on_spawn(monkeypatch)
    unresolved_at_launch: dict[str, int] = {}
    original_spawn = megalaunch_module.spawn_agent_session

    def record_spawn(cfg_, ref_obj, ticket_, agent, **kwargs):  # type: ignore[no-untyped-def]
        unresolved_at_launch[ref_obj.id_slug] = len(open_blockers(ref_obj.ticket_path))
        return original_spawn(cfg_, ref_obj, ticket_, agent, **kwargs)

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", record_spawn)

    run = run_megalaunch(cfg)

    assert launched == [dependency["slug"], blocked["slug"]]
    assert unresolved_at_launch[blocked["slug"]] == 0
    assert run.counts["launched"] == 2
    assert run.counts["drained"] == 1
    assert run.counts["completed"] == 2
    assert len({result.slug for result in run.results}) == len(run.results)
    blocked_result = next(result for result in run.results if result.slug == blocked["slug"])
    assert blocked_result.drained is True
    assert dependency["slug"] in blocked_result.detail
    summary = render_run_summary(run)
    assert "- drained: 1" in summary
    assert summary.count(f"- {blocked['slug']}:") == 1
    blocker = read_blockers(Path(blocked["path"]))[0]
    assert blocker.resolved is True
    assert "Coga megalaunch automatically resolved" in (blocker.answer or "")
    assert dependency["slug"] in (blocker.answer or "")


def test_megalaunch_drain_keeps_ask_open_when_activation_refuses(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A drained ticket that cannot activate keeps its ask and stays reportable."""
    from coga.blackboard import append_blocker, open_blockers
    from coga.blocker_reminders import scan_blocker_reminders

    cfg = load_config(repo)
    blocked = create_task(
        cfg=cfg,
        title="Blocked first",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    dependency = create_task(
        cfg=cfg,
        title="Dependency",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    append_blocker(
        Path(blocked["path"]),
        actor="claude",
        reason=f"Waiting for {dependency['slug']} to land",
    )
    ticket = Ticket.read(blocked["path"])
    ticket.frontmatter["status"] = "blocked"
    # No `workflow:` — activation refuses, so the drain must not resolve.
    ticket.frontmatter.pop("workflow", None)
    ticket.frontmatter.pop("step", None)
    ticket.write(blocked["path"])

    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(cfg)

    assert launched == [dependency["slug"]]
    assert run.counts["drained"] == 1
    assert run.counts["skipped-unlaunchable"] == 1
    blocked_result = next(result for result in run.results if result.slug == blocked["slug"])
    assert blocked_result.outcome == "skipped-unlaunchable"
    assert blocked_result.drained is True
    assert "no workflow" in blocked_result.detail

    # The ask survives the failed drain: still blocked, still open, still the
    # actionable state `coga unblock` and the blocker reminders work from.
    after = Ticket.read(blocked["path"])
    assert after.status == "blocked"
    still_open = open_blockers(Path(blocked["path"]))
    assert [b.reason for b in still_open] == [
        f"Waiting for {dependency['slug']} to land"
    ]
    reminded = [r.slug for r in scan_blocker_reminders(cfg)]
    assert reminded == [blocked["slug"]]


def test_megalaunch_redrains_ticket_that_blocked_during_main_sweep(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ticket can block, see its dependency finish, and resume in one run."""
    from coga.blackboard import append_blocker

    cfg = load_config(repo)
    dependent = create_task(
        cfg=cfg,
        title="A dependent",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    dependency = create_task(
        cfg=cfg,
        title="B dependency",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")
    launched: list[str] = []

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(cfg_, ref_obj, ticket_, agent, **kwargs):  # type: ignore[no-untyped-def]
        launched.append(ref_obj.id_slug)
        updated = Ticket.read(ref_obj.ticket_path)
        if ref_obj.id_slug == dependent["slug"] and launched.count(ref_obj.id_slug) == 1:
            append_blocker(
                ref_obj.ticket_path,
                actor="claude",
                reason=f"Waiting for {dependency['slug']}",
            )
            updated = Ticket.read(ref_obj.ticket_path)
            updated.frontmatter["status"] = "blocked"
        else:
            updated.frontmatter["status"] = "done"
            updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg)

    assert launched == [dependent["slug"], dependency["slug"], dependent["slug"]]
    assert run.counts["launched"] == 2
    assert run.counts["drained"] == 1
    assert run.counts["completed"] == 2
    assert len(run.results) == 2
    assert Ticket.read(dependent["path"]).status == "done"


def test_megalaunch_drain_preserves_prior_launch_on_pre_spawn_retry_skip(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed retry cannot erase that the task ran in the main sweep."""
    from coga.blackboard import append_blocker

    cfg = load_config(repo)
    dependent = create_task(
        cfg=cfg,
        title="A dependent",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    dependency = create_task(
        cfg=cfg,
        title="B dependency",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")
    launched: list[str] = []

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(cfg_, ref_obj, ticket_, agent, **kwargs):  # type: ignore[no-untyped-def]
        launched.append(ref_obj.id_slug)
        updated = Ticket.read(ref_obj.ticket_path)
        if ref_obj.id_slug == dependent["slug"]:
            append_blocker(
                ref_obj.ticket_path,
                actor="claude",
                reason=f"Waiting for {dependency['slug']}",
            )
            updated = Ticket.read(ref_obj.ticket_path)
            updated.frontmatter["status"] = "blocked"
            # Make the satisfied retry fail the candidate check before another
            # session starts, after the task already launched once.
            updated.frontmatter["assignee"] = "marc"
        else:
            updated.frontmatter["status"] = "done"
            updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg)

    assert launched == [dependent["slug"], dependency["slug"]]
    assert run.counts["launched"] == 2
    dependent_result = next(
        result for result in run.results if result.slug == dependent["slug"]
    )
    assert dependent_result.drained is True
    assert dependent_result.launched is True
    assert dependent_result.outcome == "skipped-human-gate"


def test_megalaunch_dependency_drain_reaches_fixed_point(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A drain launch can satisfy an earlier blocked ticket on the next pass."""
    from coga.blackboard import append_blocker

    cfg = load_config(repo)
    last = create_task(
        cfg=cfg,
        title="Last",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    middle = create_task(
        cfg=cfg,
        title="Middle",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    first = create_task(
        cfg=cfg,
        title="First",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    for ref, dependency in ((last, middle), (middle, first)):
        append_blocker(
            Path(ref["path"]),
            actor="claude",
            reason=f"Waiting for {dependency['slug']}",
        )
        ticket = Ticket.read(ref["path"])
        ticket.frontmatter["status"] = "blocked"
        ticket.write(ref["path"])

    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(cfg)

    assert launched == [first["slug"], middle["slug"], last["slug"]]
    assert run.counts["drained"] == 2
    assert run.counts["completed"] == 3
    assert len({result.slug for result in run.results}) == 3


def test_megalaunch_drain_treats_dependency_deleted_mid_sweep_as_finished(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A known dependency reaped by earlier work satisfies its blocker."""
    from coga.blackboard import append_blocker

    cfg = load_config(repo)
    blocked = create_task(
        cfg=cfg,
        title="A blocked on reaped task",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    reaper = create_task(
        cfg=cfg,
        title="B reaper",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    dependency = create_task(
        cfg=cfg,
        title="C reaped dependency",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    append_blocker(
        Path(blocked["path"]),
        actor="claude",
        reason=f"Waiting for {dependency['slug']}",
    )
    ticket = Ticket.read(blocked["path"])
    ticket.frontmatter["status"] = "blocked"
    ticket.write(blocked["path"])

    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")
    launched: list[str] = []

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(cfg_, ref_obj, ticket_, agent, **kwargs):  # type: ignore[no-untyped-def]
        launched.append(ref_obj.id_slug)
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "done"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        if ref_obj.id_slug == reaper["slug"]:
            dependency_path = Path(dependency["path"])
            dependency_path.unlink()
            if dependency_path.name == "ticket.md":
                dependency_path.parent.rmdir()
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg)

    assert launched == [reaper["slug"], blocked["slug"]]
    assert run.counts["drained"] == 1
    assert run.counts["completed"] == 2
    assert not Path(dependency["path"]).exists()


def test_megalaunch_drain_relists_blocked_tickets_created_mid_run(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The terminal drain sees blocked tasks absent from the initial snapshot."""
    from coga.blackboard import append_blocker

    cfg = load_config(repo)
    dependency = create_task(
        cfg=cfg,
        title="Creates blocked followup",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")
    launched: list[str] = []
    created: dict[str, str] = {}

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(cfg_, ref_obj, ticket_, agent, **kwargs):  # type: ignore[no-untyped-def]
        launched.append(ref_obj.id_slug)
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "done"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        if ref_obj.id_slug == dependency["slug"]:
            late = create_task(
                cfg=cfg,
                title="Late blocked task",
                workflow_name="code",
                contexts=[],
                owner="marc",
                assignee="claude",
                status="active",
                watchers=[],
            )
            created.update(late)
            append_blocker(
                Path(late["path"]),
                actor="claude",
                reason=f"Waiting for {dependency['slug']}",
            )
            late_ticket = Ticket.read(late["path"])
            late_ticket.frontmatter["status"] = "blocked"
            late_ticket.write(late["path"])
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg)

    assert launched == [dependency["slug"], created["slug"]]
    assert run.counts["drained"] == 1
    assert Ticket.read(created["path"]).status == "done"


def test_megalaunch_drain_shares_max_tasks_budget(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A main-sweep launch can exhaust the budget before a dependency drain."""
    from coga.blackboard import append_blocker, open_blockers

    cfg = load_config(repo)
    blocked = create_task(
        cfg=cfg,
        title="Budget blocked",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    dependency = create_task(
        cfg=cfg,
        title="Budget dependency",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    append_blocker(
        Path(blocked["path"]),
        actor="claude",
        reason=f"Waiting for {dependency['slug']}",
    )
    ticket = Ticket.read(blocked["path"])
    ticket.frontmatter["status"] = "blocked"
    ticket.write(blocked["path"])
    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(cfg, max_tasks=1)

    assert launched == [dependency["slug"]]
    assert run.counts["launched"] == 1
    assert run.counts["drained"] == 0
    assert Ticket.read(blocked["path"]).status == "blocked"
    assert len(open_blockers(Path(blocked["path"]))) == 1


def test_megalaunch_drain_late_park_does_not_consume_attempt_budget(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late gate skip in the drain leaves its budget for another dependency."""
    from coga import megalaunch as megalaunch_module
    from coga.blackboard import append_blocker

    cfg = load_config(repo)
    dependency = create_task(
        cfg=cfg,
        title="A finished dependency",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    dependency_ticket = Ticket.read(dependency["path"])
    dependency_ticket.frontmatter["status"] = "done"
    dependency_ticket.frontmatter.pop("step", None)
    dependency_ticket.write(dependency["path"])

    blocked = []
    for title in ("B first dependency retry", "C actual dependency retry"):
        created = create_task(
            cfg=cfg,
            title=title,
            workflow_name="code",
            contexts=[],
            owner="marc",
            assignee="claude",
            status="active",
            watchers=[],
        )
        append_blocker(
            Path(created["path"]),
            actor="claude",
            reason=f"Waiting for {dependency['slug']}",
        )
        ticket = Ticket.read(created["path"])
        ticket.frontmatter["status"] = "blocked"
        ticket.write(created["path"])
        blocked.append(created)

    real_candidate = megalaunch_module._candidate_result
    parked = False

    def park_after_dependency_activation(
        cfg_, ref_, ticket_, **kwargs
    ):  # type: ignore[no-untyped-def]
        nonlocal parked
        result = real_candidate(cfg_, ref_, ticket_, **kwargs)
        if (
            ref_.id_slug == blocked[0]["slug"]
            and ticket_.status == "active"
            and result is None
            and not parked
        ):
            parked = True
            peer = Ticket.read(ref_.ticket_path)
            peer.frontmatter["status"] = "paused"
            peer.write(ref_.ticket_path)
        return result

    monkeypatch.setattr(
        "coga.megalaunch._candidate_result", park_after_dependency_activation
    )
    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(cfg, max_tasks=1)

    assert parked
    assert launched == [blocked[1]["slug"]]
    first = next(result for result in run.results if result.slug == blocked[0]["slug"])
    assert (first.outcome, first.launched, first.drained) == (
        "skipped-unlaunchable",
        False,
        True,
    )


def test_megalaunch_drain_matches_complete_task_slug_not_substring(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A short finished slug inside an unrelated word does not satisfy."""
    from coga.blackboard import append_blocker, open_blockers

    cfg = load_config(repo)
    dependency = create_task(
        cfg=cfg,
        title="API",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    dependency_ticket = Ticket.read(dependency["path"])
    dependency_ticket.frontmatter["status"] = "done"
    dependency_ticket.frontmatter.pop("step", None)
    dependency_ticket.write(dependency["path"])
    blocked = create_task(
        cfg=cfg,
        title="Substring blocker",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    append_blocker(
        Path(blocked["path"]),
        actor="claude",
        reason="Waiting for rapid rollout approval",
    )
    ticket = Ticket.read(blocked["path"])
    ticket.frontmatter["status"] = "blocked"
    ticket.write(blocked["path"])

    def fail_spawn(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("a slug substring must not trigger a drain")

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fail_spawn)
    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")

    run = run_megalaunch(cfg)

    assert run.counts["drained"] == 0
    assert run.counts["skipped-unresolved-blocker"] == 1
    assert len(open_blockers(Path(blocked["path"]))) == 1


def test_megalaunch_drain_does_not_match_short_slug_inside_dotted_ref(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A done `v1` cannot satisfy a blocker naming unfinished `v1.2/api`."""
    from coga.blackboard import append_blocker, open_blockers

    cfg = load_config(repo)
    short = create_task(
        cfg=cfg,
        title="V1",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    short_ticket = Ticket.read(short["path"])
    short_ticket.frontmatter["status"] = "done"
    short_ticket.frontmatter.pop("step", None)
    short_ticket.write(short["path"])
    actual = create_task(
        cfg=cfg,
        title="API",
        directory="v1.2",
        workflow_name="code",
        contexts=[],
        owner="lea",
        assignee="claude",
        status="active",
        watchers=[],
    )
    blocked = create_task(
        cfg=cfg,
        title="Dotted ref blocker",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    append_blocker(
        Path(blocked["path"]),
        actor="claude",
        reason=f"Waiting for {actual['slug']}",
    )
    ticket = Ticket.read(blocked["path"])
    ticket.frontmatter["status"] = "blocked"
    ticket.write(blocked["path"])

    def fail_spawn(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("unfinished dotted dependency must not trigger a drain")

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fail_spawn)
    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")

    run = run_megalaunch(cfg)

    assert run.counts["drained"] == 0
    assert run.counts["skipped-unresolved-blocker"] == 1
    assert len(open_blockers(Path(blocked["path"]))) == 1


def test_megalaunch_drain_normalizes_trailing_slash_directory_scope(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The drain uses the same normalized directory scope as the main sweep."""
    from coga.blackboard import append_blocker

    cfg = load_config(repo)
    dependency = create_task(
        cfg=cfg,
        title="Dependency",
        directory="marketing",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    dependency_ticket = Ticket.read(dependency["path"])
    dependency_ticket.frontmatter["status"] = "done"
    dependency_ticket.frontmatter.pop("step", None)
    dependency_ticket.write(dependency["path"])
    blocked = create_task(
        cfg=cfg,
        title="Blocked",
        directory="marketing",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    append_blocker(
        Path(blocked["path"]),
        actor="claude",
        reason=f"Waiting for {dependency['slug']}",
    )
    ticket = Ticket.read(blocked["path"])
    ticket.frontmatter["status"] = "blocked"
    ticket.write(blocked["path"])
    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(cfg, directory="marketing/")

    assert launched == [blocked["slug"]]
    assert run.counts["drained"] == 1
    assert Ticket.read(blocked["path"]).status == "done"


def test_megalaunch_explicit_selection_does_not_expand_into_dependency_drain(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Completing a pick never launches an unpicked blocked ticket."""
    from coga.blackboard import append_blocker, open_blockers

    cfg = load_config(repo)
    blocked = create_task(
        cfg=cfg,
        title="Unpicked blocked",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    dependency = create_task(
        cfg=cfg,
        title="Picked dependency",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    append_blocker(
        Path(blocked["path"]),
        actor="claude",
        reason=f"Waiting for {dependency['slug']}",
    )
    ticket = Ticket.read(blocked["path"])
    ticket.frontmatter["status"] = "blocked"
    ticket.write(blocked["path"])
    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(cfg, selection=[dependency["slug"]])

    assert launched == [dependency["slug"]]
    assert run.counts["drained"] == 0
    assert Ticket.read(blocked["path"]).status == "blocked"
    assert len(open_blockers(Path(blocked["path"]))) == 1


def test_megalaunch_drain_never_relaunches_same_ticket_twice(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A new blocker after a drain cannot make the fixed-point loop repeat it."""
    from coga.blackboard import append_blocker, open_blockers

    cfg = load_config(repo)
    dependency = create_task(
        cfg=cfg,
        title="Already done dependency",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    dependency_ticket = Ticket.read(dependency["path"])
    dependency_ticket.frontmatter["status"] = "done"
    dependency_ticket.frontmatter.pop("step", None)
    dependency_ticket.write(dependency["path"])
    blocked = create_task(
        cfg=cfg,
        title="Blocks again",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    append_blocker(
        Path(blocked["path"]),
        actor="claude",
        reason=f"Waiting for {dependency['slug']}",
    )
    ticket = Ticket.read(blocked["path"])
    ticket.frontmatter["status"] = "blocked"
    ticket.write(blocked["path"])
    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")
    launched: list[str] = []

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(cfg_, ref_obj, ticket_, agent, **kwargs):  # type: ignore[no-untyped-def]
        launched.append(ref_obj.id_slug)
        append_blocker(
            ref_obj.ticket_path,
            actor="claude",
            reason=f"Still waiting for {dependency['slug']}",
        )
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "blocked"
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg)

    assert launched == [blocked["slug"]]
    assert run.counts["drained"] == 1
    assert run.counts["blocked"] == 1
    assert len(open_blockers(Path(blocked["path"]))) == 1





def test_megalaunch_ignores_non_active_tickets(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Terminal/draft/paused tickets are ignored — never launched or failed."""
    cfg = load_config(repo)
    for title, status in (
        ("Done", "done"),
        ("Canceled", "canceled"),
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
        if status in {"done", "canceled"}:
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


def test_megalaunch_services_numbered_subdir_in_number_order(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A `1-`/`2-`/`3-` named sub-tree drains in number order, not age order.

    The numbering is a plain naming convention on the task directory — no
    flag — and only reorders *within* the sub-directory: the top-level `alpha`
    still runs first because the `v2` block is anchored at its oldest task.
    """
    from coga.paths import log_path

    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Alpha",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    for slug in ("1-schema", "2-migrate", "3-cutover"):
        create_task(
            cfg=cfg,
            title=slug,
            slug_override=slug,
            directory="v2",
            workflow_name="code",
            contexts=[],
            owner="marc",
            assignee="claude",
            status="active",
            watchers=[],
        )
    # Created newest-number-first, so age ordering alone would drain 3, 2, 1.
    log_path(cfg).write_text(
        "2026-06-01 10:00 [alpha] [human:marc] created\n"
        "2026-06-02 10:00 [v2/3-cutover] [human:marc] created\n"
        "2026-06-03 10:00 [v2/2-migrate] [human:marc] created\n"
        "2026-06-04 10:00 [v2/1-schema] [human:marc] created\n"
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

    assert [result.slug for result in run.results] == [
        "alpha",
        "v2/1-schema",
        "v2/2-migrate",
        "v2/3-cutover",
    ]


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
    canceled = create_task(
        cfg=cfg,
        title="Intentionally declined",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="canceled",
        watchers=[],
    )
    workflowless = create_task(
        cfg=cfg,
        title="Shapeless draft",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )
    ticket = Ticket.read(workflowless["path"])
    ticket.frontmatter["workflow"] = None
    ticket.write(workflowless["path"])

    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(
        cfg,
        selection=[done["slug"], canceled["slug"], workflowless["slug"]],
    )

    assert launched == []
    assert run.counts["skipped-unlaunchable"] == 3
    outcomes = {result.slug: result.detail for result in run.results}
    assert outcomes[done["slug"]] == "status is done"
    assert outcomes[canceled["slug"]] == "status is canceled"
    assert "no workflow" in outcomes[workflowless["slug"]]


def test_megalaunch_selection_launches_other_owners_ticket(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicitly picking someone else's ticket is the deliberate act of
    starting it — the sweep-only owner filter does not apply."""
    cfg = load_config(repo)
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

    run = run_megalaunch(cfg, selection=[foreign["slug"]])

    assert launched == [foreign["slug"]]
    assert run.counts["completed"] == 1


def test_megalaunch_selection_activates_draft_and_paused(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A picked draft / paused ticket activates inline, like `coga launch`."""
    cfg = load_config(repo)
    draft = create_task(
        cfg=cfg,
        title="Draft pick",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )
    paused = create_task(
        cfg=cfg,
        title="Paused pick",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    ticket = Ticket.read(paused["path"])
    ticket.frontmatter["status"] = "paused"
    ticket.write(paused["path"])

    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(cfg, selection=[draft["slug"], paused["slug"]])

    assert sorted(launched) == sorted([draft["slug"], paused["slug"]])
    assert run.counts["completed"] == 2
    assert Ticket.read(draft["path"]).status == "done"
    assert Ticket.read(paused["path"]).status == "done"


def _log_lines_for(cfg, slug: str, needle: str) -> list[str]:
    """Audit-log lines tagged with `slug` that mention `needle`."""
    from coga.paths import log_path

    return [
        line
        for line in log_path(cfg).read_text().splitlines()
        if f"[{slug}]" in line and needle in line
    ]


def test_megalaunch_selection_does_not_activate_pick_refused_by_preflight(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pick the launch preflights refuse is never written as `active`.

    `active` on disk means a session began. The refusal now lands before the
    durable flip, so the ticket stays a draft with no `activated` log line —
    and one bad pick does not end the sweep.
    """
    cfg = load_config(repo)
    refused = create_task(
        cfg=cfg,
        title="Bad secrets pick",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )
    healthy = create_task(
        cfg=cfg,
        title="Good pick",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )
    ticket = Ticket.read(refused["path"])
    # Mapping-form `secrets:` is malformed — `build_launch_env` refuses it in
    # the preflight, which the old code only reached after activating.
    ticket.frontmatter["secrets"] = {"stripe_key": "env:STRIPE_SECRET_KEY"}
    ticket.write(refused["path"])
    before = Path(refused["path"]).read_bytes()

    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(cfg, selection=[refused["slug"], healthy["slug"]])

    result = next(r for r in run.results if r.slug == refused["slug"])
    assert result.outcome == "failed"
    assert "secrets" in result.detail
    assert result.launched is False
    # Nothing durable happened: same bytes, same status, no activation logged.
    assert Path(refused["path"]).read_bytes() == before
    assert Ticket.read(refused["path"]).status == "draft"
    assert _log_lines_for(cfg, refused["slug"], "activated") == []
    # The sweep carried on, and the healthy pick activated as it launched.
    assert launched == [healthy["slug"]]
    assert len(_log_lines_for(cfg, healthy["slug"], "activated")) == 1


def test_megalaunch_selection_does_not_activate_pick_without_agent_cli(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The missing-CLI refusal is upstream of activation too."""
    cfg = load_config(repo)
    draft = create_task(
        cfg=cfg,
        title="No CLI pick",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )
    before = Path(draft["path"]).read_bytes()
    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: None)

    run = run_megalaunch(cfg, selection=[draft["slug"]])

    result = next(r for r in run.results if r.slug == draft["slug"])
    assert result.outcome == "failed"
    assert "claude" in result.detail
    assert Path(draft["path"]).read_bytes() == before
    assert Ticket.read(draft["path"]).status == "draft"
    assert _log_lines_for(cfg, draft["slug"], "activated") == []


def test_megalaunch_selection_preserves_peer_edit_during_preflight(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The deferred write is a CAS against the ticket its preflight saw."""
    cfg = load_config(repo)
    draft = create_task(
        cfg=cfg,
        title="Racing draft",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )
    launched = _done_on_spawn(monkeypatch)
    peer_bytes: bytes | None = None

    from coga import megalaunch as megalaunch_module

    original_preflight = megalaunch_module._preflight_agent_launch

    def racing_preflight(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal peer_bytes
        peer = Ticket.read(draft["path"])
        peer.frontmatter["status"] = "done"
        peer.frontmatter.pop("step", None)
        peer.body = f"{peer.body.rstrip()}\n\nPeer completed this ticket.\n"
        peer.write(draft["path"])
        peer_bytes = Path(draft["path"]).read_bytes()
        return original_preflight(*args, **kwargs)

    monkeypatch.setattr(
        "coga.megalaunch._preflight_agent_launch", racing_preflight
    )

    run = run_megalaunch(cfg, selection=[draft["slug"]])

    assert launched == []
    assert run.results[0].outcome == "failed"
    assert "changed before writing" in run.results[0].detail
    assert peer_bytes is not None
    assert Path(draft["path"]).read_bytes() == peer_bytes
    assert Ticket.read(draft["path"]).status == "done"
    assert _log_lines_for(cfg, draft["slug"], "activated") == []


def test_megalaunch_selection_commits_the_preflighted_workflow_snapshot(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A workflow edit during preflight cannot change the activation snapshot."""
    cfg = load_config(repo)
    draft = create_task(
        cfg=cfg,
        title="Bare workflow draft",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )
    ticket = Ticket.read(draft["path"])
    ticket.frontmatter["workflow"] = "code"
    ticket.frontmatter.pop("step", None)
    ticket.write(draft["path"])

    from coga import megalaunch as megalaunch_module

    original_preflight = megalaunch_module._preflight_agent_launch

    def changing_preflight(*args, **kwargs):  # type: ignore[no-untyped-def]
        _write(
            repo / "workflows" / "code.md",
            """
            ---
            name: code
            description: changed while the launch preflight ran.
            steps:
              - name: implement
                assignee: owner
              - name: review
                assignee: owner
            ---

            ## implement
            Write the code.

            ## review
            Review the code.
            """,
        )
        return original_preflight(*args, **kwargs)

    class _Session:
        exit_code = 1
        termination_kind = "natural"

    seen_workflow: dict[str, object] = {}

    def fake_spawn(  # type: ignore[no-untyped-def]
        _cfg, _ref, launched, _agent, **_kwargs
    ):
        seen_workflow.update(launched.workflow or {})
        return _Session()

    monkeypatch.setattr(
        "coga.megalaunch._preflight_agent_launch", changing_preflight
    )
    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg, selection=[draft["slug"]])

    assert run.results[0].outcome == "failed"
    steps = seen_workflow["steps"]
    assert isinstance(steps, list)
    assert steps[0]["assignee"] == "agent"
    persisted = Ticket.read(draft["path"])
    assert persisted.workflow is not None
    assert persisted.workflow["steps"][0]["assignee"] == "agent"


def test_megalaunch_selection_preserves_peer_edit_during_activation_sync(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The active-to-start write cannot overlay a peer edit made during sync."""
    cfg = load_config(repo)
    draft = create_task(
        cfg=cfg,
        title="Activation sync race",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )
    monkeypatch.setattr(
        "coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}"
    )
    peer_bytes: bytes | None = None
    sync_calls = 0

    def racing_sync(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        nonlocal peer_bytes, sync_calls
        sync_calls += 1
        if sync_calls != 1:
            return
        peer = Ticket.read(draft["path"])
        assert peer.status == "active"
        peer.frontmatter["status"] = "done"
        peer.frontmatter.pop("step", None)
        peer.body = f"{peer.body.rstrip()}\n\nPeer completed during sync.\n"
        peer.write(draft["path"])
        peer_bytes = Path(draft["path"]).read_bytes()

    def fail_spawn(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("a peer-changed ticket must not spawn")

    monkeypatch.setattr("coga.mark.git.sync_task_state", racing_sync)
    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fail_spawn)

    run = run_megalaunch(cfg, selection=[draft["slug"]])

    assert run.results[0].outcome == "failed"
    assert "changed after launch preflight" in run.results[0].detail
    assert peer_bytes is not None
    assert Path(draft["path"]).read_bytes() == peer_bytes
    assert Ticket.read(draft["path"]).status == "done"
    assert _log_lines_for(cfg, draft["slug"], "started (") == []


def test_megalaunch_refuses_peer_edit_during_start_sync(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The spawned prompt remains bound after start publication returns."""
    cfg = load_config(repo)
    active = create_task(
        cfg=cfg,
        title="Start sync race",
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
    peer_bytes: bytes | None = None

    def racing_sync(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        nonlocal peer_bytes
        peer = Ticket.read(active["path"])
        assert peer.status == "in_progress"
        peer.frontmatter["status"] = "done"
        peer.frontmatter.pop("step", None)
        peer.body = f"{peer.body.rstrip()}\n\nPeer completed during start sync.\n"
        peer.write(active["path"])
        peer_bytes = Path(active["path"]).read_bytes()

    def fail_spawn(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("a ticket changed during start sync must not spawn")

    monkeypatch.setattr("coga.mark.git.sync_task_state", racing_sync)
    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fail_spawn)

    run = run_megalaunch(cfg, selection=[active["slug"]])

    assert run.results[0].outcome == "failed"
    assert (
        run.results[0].detail
        == "ticket changed during start publication; current state retained "
        "for safe resume; retry"
    )
    assert peer_bytes is not None
    assert Path(active["path"]).read_bytes() == peer_bytes
    assert Ticket.read(active["path"]).status == "done"
    assert len(_log_lines_for(cfg, active["slug"], "started (")) == 1


def test_megalaunch_does_not_compensate_over_an_ordinary_resume(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An ordinary resume may own same-generation ``in_progress`` bytes."""
    cfg = load_config(repo)
    active = create_task(
        cfg=cfg,
        title="Start body race",
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
    sync_calls = 0
    claimed_generation: str | None = None

    def racing_sync(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        nonlocal claimed_generation, sync_calls
        sync_calls += 1
        if sync_calls != 1:
            return
        peer = Ticket.read(active["path"])
        assert peer.status == "in_progress"
        claimed_generation = peer.launch_generation
        assert claimed_generation is not None
        # An ordinary `coga launch` resume does not rotate megalaunch's
        # generation before its child starts. Its in-session blackboard write
        # therefore cannot be distinguished from an unlaunched peer edit by
        # generation alone.
        peer.body = (
            f"{peer.body.rstrip()}\n\n"
            "Ordinary coga launch session is running.\n"
        )
        peer.write(active["path"])

    def fail_spawn(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("a ticket changed during start sync must not spawn")

    monkeypatch.setattr("coga.mark.git.sync_task_state", racing_sync)
    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fail_spawn)

    run = run_megalaunch(cfg, selection=[active["slug"]])

    assert sync_calls == 1
    assert run.results[0].outcome == "failed"
    assert (
        run.results[0].detail
        == "ticket changed during start publication; current state retained "
        "for safe resume; retry"
    )
    retained = Ticket.read(active["path"])
    assert retained.status == "in_progress"
    assert retained.launch_generation == claimed_generation
    assert "Ordinary coga launch session is running." in retained.body
    assert len(_log_lines_for(cfg, active["slug"], "started (")) == 1
    assert _log_lines_for(cfg, active["slug"], "restored (") == []


def test_megalaunch_does_not_reclaim_a_published_session_claim(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A published generation cannot be rotated by another megalaunch."""
    cfg = load_config(repo)
    active = create_task(
        cfg=cfg,
        title="Start claim race",
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
    sync_calls = 0
    outer_generation: str | None = None
    peer_result = None

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def outer_spawn(
        _cfg, _ref, claimed: Ticket, _agent, **kwargs
    ):  # type: ignore[no-untyped-def]
        assert claimed.launch_generation == outer_generation
        kwargs["validate_before_spawn"]()
        kwargs["validate_after_spawn"]()
        finished = Ticket.read(active["path"])
        finished.frontmatter["status"] = "done"
        finished.frontmatter.pop("step", None)
        finished.frontmatter.pop("launch_generation", None)
        finished.write(active["path"])
        return _Session()

    def racing_sync(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        nonlocal outer_generation, peer_result, sync_calls
        sync_calls += 1
        if sync_calls != 1:
            return
        outer_generation = Ticket.read(active["path"]).launch_generation
        assert outer_generation is not None
        peer_run = run_megalaunch(cfg, selection=[active["slug"]])
        peer_result = peer_run.results[0]

    monkeypatch.setattr("coga.mark.git.sync_task_state", racing_sync)
    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", outer_spawn)

    run = run_megalaunch(cfg, selection=[active["slug"]])

    assert sync_calls == 1
    assert run.results[0].outcome == "completed"
    assert run.results[0].launched
    assert peer_result is not None
    assert peer_result.outcome == "failed"
    assert not peer_result.launched
    assert "already carries a published megalaunch claim" in peer_result.detail
    retained = Ticket.read(active["path"])
    assert retained.status == "done"
    assert retained.launch_generation is None
    assert _log_lines_for(cfg, active["slug"], "restored (") == []


def test_megalaunch_dependency_drain_publishes_resolution_before_claim(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The strict start claim leases the resolved control-ticket bytes."""
    from coga import git as git_module
    from coga.blackboard import (
        append_blocker,
        open_blockers,
        parse_blockers_text,
    )

    cfg = load_config(git_repo.coga_os)
    blocked = create_task(
        cfg=cfg,
        title="Blocked behind finished dependency",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    dependency = create_task(
        cfg=cfg,
        title="Finished dependency",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    append_blocker(
        Path(blocked["path"]),
        actor="claude",
        reason=f"Waiting for {dependency['slug']} to land",
    )
    blocked_ticket = Ticket.read(blocked["path"])
    blocked_ticket.frontmatter["status"] = "blocked"
    blocked_ticket.write(blocked["path"])
    dependency_ticket = Ticket.read(dependency["path"])
    dependency_ticket.frontmatter["status"] = "done"
    dependency_ticket.frontmatter.pop("step", None)
    dependency_ticket.write(dependency["path"])
    git_module.sync_task_state(
        cfg,
        Path(dependency["path"]),
        message="Seed finished dependency",
    )
    git_module.sync_task_state(
        cfg,
        Path(blocked["path"]),
        message="Seed blocked dependent",
    )
    monkeypatch.setattr(
        "coga.megalaunch._interactive_stdio_has_tty", lambda: True
    )
    monkeypatch.setattr(
        "coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}"
    )
    ticket_rel = str(Path(blocked["path"]).relative_to(git_repo.root))
    spawned: list[str] = []

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(
        _cfg, ref_obj, claimed, _agent, **_kwargs
    ):  # type: ignore[no-untyped-def]
        spawned.append(ref_obj.id_slug)
        assert claimed.status == "in_progress"
        assert open_blockers(ref_obj.ticket_path) == []
        remote = Ticket.parse(
            git_repo.git("show", f"main:{ticket_rel}", cwd=git_repo.origin)
        )
        assert remote.status == "in_progress"
        assert [
            blocker
            for blocker in parse_blockers_text(remote.body)
            if not blocker.resolved
        ] == []
        assert "Coga megalaunch automatically resolved" in remote.body
        finished = Ticket.read(ref_obj.ticket_path)
        finished.frontmatter["status"] = "done"
        finished.frontmatter.pop("step", None)
        finished.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg)

    assert spawned == [blocked["slug"]]
    assert run.counts["drained"] == 1
    assert run.counts["completed"] == 1


def test_megalaunch_deferred_activation_cas_uses_exact_control_ticket(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A control-side prose edit defeats the draft-to-active publication."""
    cfg = load_config(git_repo.coga_os)
    draft = create_task(
        cfg=cfg,
        title="Exact activation claim",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )
    monkeypatch.setattr("coga.megalaunch._interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr(
        "coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}"
    )

    from coga import git as git_module

    git_module.sync_task_state(
        cfg, Path(draft["path"]), message="Seed exact activation claim"
    )
    real_sync = git_module.sync_task_state
    ticket_path = Path(draft["path"])
    ticket_rel = str(ticket_path.relative_to(git_repo.root))
    raced = False

    def racing_sync(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal raced
        if not raced:
            raced = True
            assert kwargs["raise_state_regression"] is True
            assert kwargs["raise_git_error"] is True
            peer = Ticket.parse(
                git_repo.git(
                    "show", f"main:{ticket_rel}", cwd=git_repo.origin
                )
            )
            peer.body = f"{peer.body.rstrip()}\n\nPeer clarified control.\n"
            git_repo.push_competing_commit(ticket_rel, peer.render())
        return real_sync(*args, **kwargs)

    def fail_spawn(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("a launch with a lost activation lease must not spawn")

    monkeypatch.setattr(git_module, "sync_task_state", racing_sync)
    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fail_spawn)

    run = run_megalaunch(cfg, selection=[draft["slug"]])

    assert raced
    assert run.results[0].outcome == "failed"
    assert "exact control ticket changed" in run.results[0].detail
    local = Ticket.read(ticket_path)
    assert local.status == "draft"
    assert local.launch_generation is None
    remote = Ticket.parse(
        git_repo.git("show", f"main:{ticket_rel}", cwd=git_repo.origin)
    )
    assert remote.status == "draft"
    assert "Peer clarified control." in remote.body
    assert _log_lines_for(cfg, draft["slug"], "activated (") == []


def test_megalaunch_launch_claim_cas_excludes_a_second_checkout(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only one checkout may publish and spawn from the same active revision."""
    cfg = load_config(git_repo.coga_os)
    active = create_task(
        cfg=cfg,
        title="Exclusive launch claim",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    from coga import git as git_module

    git_module.sync_task_state(
        cfg, Path(active["path"]), message="Seed exclusive launch claim"
    )
    peer_root = git_repo.root.parent / "peer-checkout"
    git_repo.git(
        "clone", str(git_repo.origin), str(peer_root), cwd=git_repo.root.parent
    )
    git_repo.git("config", "user.email", "peer@example.com", cwd=peer_root)
    git_repo.git("config", "user.name", "Peer", cwd=peer_root)
    git_repo.git("config", "commit.gpgsign", "false", cwd=peer_root)
    git_repo.git("checkout", "-B", "main", "origin/main", cwd=peer_root)
    (peer_root / "coga" / "coga.local.toml").write_text(
        'user = "marc"\n', encoding="utf-8"
    )
    peer_cfg = load_config(peer_root / "coga")

    monkeypatch.setattr("coga.megalaunch._interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr(
        "coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}"
    )

    real_sync = git_module.sync_task_state
    peer_started = False
    peer_generation: str | None = None
    spawned_paths: list[Path] = []

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def one_peer_spawn(
        _cfg, ref, claimed: Ticket, _agent, **_kwargs
    ):  # type: ignore[no-untyped-def]
        nonlocal peer_generation
        spawned_paths.append(ref.ticket_path)
        assert ref.ticket_path.is_relative_to(peer_root)
        peer_generation = claimed.launch_generation
        assert peer_generation is not None
        return _Session()

    def racing_sync(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal peer_started
        if not peer_started:
            peer_started = True
            peer_run = run_megalaunch(peer_cfg, selection=[active["slug"]])
            assert peer_run.results[0].launched
        return real_sync(*args, **kwargs)

    monkeypatch.setattr(git_module, "sync_task_state", racing_sync)
    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", one_peer_spawn)

    run = run_megalaunch(cfg, selection=[active["slug"]])

    assert run.results[0].outcome == "failed"
    assert not run.results[0].launched
    assert "exact control ticket changed" in run.results[0].detail
    assert len(spawned_paths) == 1
    assert peer_generation is not None
    local = Ticket.read(active["path"])
    assert local.status == "active"
    assert local.launch_generation is None
    ticket_rel = str(Path(active["path"]).relative_to(git_repo.root))
    remote = Ticket.parse(
        git_repo.git("show", f"main:{ticket_rel}", cwd=git_repo.origin)
    )
    assert remote.status == "in_progress"
    assert remote.launch_generation == peer_generation


def test_megalaunch_revalidates_control_claim_at_final_spawn_boundary(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A claim rotated after prompt setup cannot reach the PTY supervisor."""
    from coga import git as git_module
    import coga.megalaunch as megalaunch_module

    cfg = load_config(git_repo.coga_os)
    active = create_task(
        cfg=cfg,
        title="Final spawn claim",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    git_module.sync_task_state(
        cfg, Path(active["path"]), message="Seed final spawn claim"
    )
    monkeypatch.setattr("coga.megalaunch._interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr(
        "coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}"
    )
    ticket_path = Path(active["path"])
    ticket_rel = str(ticket_path.relative_to(git_repo.root))
    outer_generation: str | None = None
    peer_generation = "peer-final-spawn-claim"
    reached_spawn_boundary = False
    real_spawn = megalaunch_module.spawn_agent_session

    def hold_child_for_final_guard(
        _cmd, _env, *, after_spawn, **_kwargs
    ):  # type: ignore[no-untyped-def]
        assert after_spawn is not None
        after_spawn()
        raise AssertionError("a refused final claim must not release the child")

    monkeypatch.setattr(
        "coga.commands.launch.run_with_done_marker", hold_child_for_final_guard
    )

    def rotate_before_pty(
        cfg_,
        ref_,
        claimed: Ticket,
        agent_,
        *,
        validate_before_spawn,
        validate_after_spawn,
        **kwargs,
    ):  # type: ignore[no-untyped-def]
        nonlocal outer_generation, reached_spawn_boundary
        outer_generation = claimed.launch_generation
        assert outer_generation is not None
        assert outer_generation != peer_generation

        def rotate_at_final_boundary() -> None:
            nonlocal reached_spawn_boundary
            peer = Ticket.parse(
                git_repo.git("show", f"main:{ticket_rel}", cwd=git_repo.origin)
            )
            assert peer.launch_generation == outer_generation
            peer.frontmatter["launch_generation"] = peer_generation
            peer.body = f"{peer.body.rstrip()}\n\nPeer claimant is running.\n"
            git_repo.push_competing_commit(ticket_rel, peer.render())
            reached_spawn_boundary = True
            validate_after_spawn()

        return real_spawn(
            cfg_,
            ref_,
            claimed,
            agent_,
            validate_before_spawn=validate_before_spawn,
            validate_after_spawn=rotate_at_final_boundary,
            **kwargs,
        )

    monkeypatch.setattr(
        "coga.megalaunch.spawn_agent_session", rotate_before_pty
    )

    run = run_megalaunch(cfg, selection=[active["slug"]])

    assert reached_spawn_boundary
    assert run.results[0].outcome == "failed"
    assert not run.results[0].launched
    assert "launch claim changed on control before agent spawn" in (
        run.results[0].detail
    )
    local = Ticket.read(ticket_path)
    assert local.status == "in_progress"
    assert local.launch_generation == outer_generation
    remote = Ticket.parse(
        git_repo.git("show", f"main:{ticket_rel}", cwd=git_repo.origin)
    )
    assert remote.status == "in_progress"
    assert remote.launch_generation == peer_generation
    assert "Peer claimant is running." in remote.body
    assert _log_lines_for(
        cfg, active["slug"], "launched via coga megalaunch"
    ) == []
    assert _log_lines_for(cfg, active["slug"], "restored (") == []


def test_megalaunch_final_refusal_keeps_audit_out_of_peer_state_commit(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A same-checkout peer cannot publish a pre-spawn launch record."""
    from coga import git as git_module
    import coga.megalaunch as megalaunch_module

    cfg = load_config(git_repo.coga_os)
    active = create_task(
        cfg=cfg,
        title="No false committed launch",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    ticket_path = Path(active["path"])
    ticket_rel = str(ticket_path.relative_to(git_repo.root))
    git_module.sync_task_state(
        cfg, ticket_path, message="Seed committed-audit race"
    )
    monkeypatch.setattr("coga.megalaunch._interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr(
        "coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}"
    )
    real_spawn = megalaunch_module.spawn_agent_session
    peer_generation = "same-checkout-peer-claim"
    reached_final_boundary = False

    def hold_child_for_final_guard(
        _cmd, _env, *, after_spawn, **_kwargs
    ):  # type: ignore[no-untyped-def]
        assert after_spawn is not None
        after_spawn()
        raise AssertionError("a changed claim must not release the child")

    monkeypatch.setattr(
        "coga.commands.launch.run_with_done_marker", hold_child_for_final_guard
    )

    def commit_peer_edit_before_final_proof(
        cfg_,
        ref_,
        claimed: Ticket,
        agent_,
        *,
        validate_before_spawn,
        validate_after_spawn,
        **kwargs,
    ):  # type: ignore[no-untyped-def]
        assert kwargs["record_launch_on_spawn"] is True

        def publish_peer_then_refuse() -> None:
            nonlocal reached_final_boundary
            peer = Ticket.read(ticket_path)
            assert peer.launch_generation == claimed.launch_generation
            peer.frontmatter["launch_generation"] = peer_generation
            peer.body = f"{peer.body.rstrip()}\n\nPeer session is running.\n"
            peer.write(ticket_path)
            git_module.sync_task_state(
                cfg,
                ref_.path,
                message="Peer changes claim at final boundary",
            )
            reached_final_boundary = True
            validate_after_spawn()

        return real_spawn(
            cfg_,
            ref_,
            claimed,
            agent_,
            validate_before_spawn=validate_before_spawn,
            validate_after_spawn=publish_peer_then_refuse,
            **kwargs,
        )

    monkeypatch.setattr(
        "coga.megalaunch.spawn_agent_session",
        commit_peer_edit_before_final_proof,
    )

    run = run_megalaunch(cfg, selection=[active["slug"]])

    assert reached_final_boundary
    assert run.results[0].outcome == "failed"
    assert not run.results[0].launched
    assert "launch claim changed locally before agent spawn" in (
        run.results[0].detail
    )
    assert Ticket.read(ticket_path).launch_generation == peer_generation
    remote = Ticket.parse(
        git_repo.git("show", f"main:{ticket_rel}", cwd=git_repo.origin)
    )
    assert remote.launch_generation == peer_generation
    assert _log_lines_for(
        cfg, active["slug"], "launched via coga megalaunch"
    ) == []
    remote_log = git_repo.git(
        "show", "main:coga/log.md", cwd=git_repo.origin
    )
    assert "launched via coga megalaunch" not in remote_log


def test_megalaunch_revalidates_after_the_deferred_audit_append(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An edit during the audit append refuses exec and removes that line."""
    from coga.commands import launch as launch_module
    from coga import git as git_module

    cfg = load_config(git_repo.coga_os)
    active = create_task(
        cfg=cfg,
        title="Post-audit claim proof",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    ticket_path = Path(active["path"])
    git_module.sync_task_state(
        cfg, ticket_path, message="Seed post-audit claim race"
    )
    monkeypatch.setattr("coga.megalaunch._interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr(
        "coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}"
    )
    child_released = False
    audit_changed_ticket = False

    def hold_child_for_admission(
        _cmd, _env, *, after_spawn, **_kwargs
    ):  # type: ignore[no-untyped-def]
        nonlocal child_released
        assert after_spawn is not None
        after_spawn()
        child_released = True
        raise AssertionError("a post-audit claim mismatch must refuse exec")

    monkeypatch.setattr(
        "coga.commands.launch.run_with_done_marker", hold_child_for_admission
    )
    real_append_log = launch_module.append_log

    def append_audit_then_edit_ticket(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal audit_changed_ticket
        appended = real_append_log(*args, **kwargs)
        if args[2] == "megalaunch" and args[3] == "launched via coga megalaunch":
            peer = Ticket.read(ticket_path)
            peer.body = f"{peer.body.rstrip()}\n\nEdited during audit append.\n"
            peer.write(ticket_path)
            audit_changed_ticket = True
        return appended

    monkeypatch.setattr(
        "coga.commands.launch.append_log", append_audit_then_edit_ticket
    )

    run = run_megalaunch(cfg, selection=[active["slug"]])

    assert audit_changed_ticket
    assert child_released is False
    assert run.results[0].outcome == "failed"
    assert not run.results[0].launched
    assert "launch claim changed locally before agent spawn" in (
        run.results[0].detail
    )
    assert "Edited during audit append." in Ticket.read(ticket_path).body
    assert _log_lines_for(
        cfg, active["slug"], "launched via coga megalaunch"
    ) == []


def test_megalaunch_claim_cannot_be_replaced_after_final_control_check(
    git_repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A published claim stays exclusive between final proof and PTY spawn."""
    from coga import git as git_module

    cfg = load_config(git_repo.coga_os)
    active = create_task(
        cfg=cfg,
        title="Non-reclaimable final claim",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    ticket_path = Path(active["path"])
    ticket_rel = str(ticket_path.relative_to(git_repo.root))
    git_module.sync_task_state(
        cfg, ticket_path, message="Seed non-reclaimable final claim"
    )
    peer_root = git_repo.root.parent / "post-check-peer"
    git_repo.git(
        "clone", str(git_repo.origin), str(peer_root), cwd=git_repo.root.parent
    )
    git_repo.git("config", "user.email", "peer@example.com", cwd=peer_root)
    git_repo.git("config", "user.name", "Peer", cwd=peer_root)
    git_repo.git("config", "commit.gpgsign", "false", cwd=peer_root)
    git_repo.git("checkout", "-B", "main", "origin/main", cwd=peer_root)
    (peer_root / "coga" / "coga.local.toml").write_text(
        'user = "marc"\n', encoding="utf-8"
    )
    peer_cfg = load_config(peer_root / "coga")
    monkeypatch.setattr("coga.megalaunch._interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr(
        "coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}"
    )
    outer_generation: str | None = None
    peer_result = None
    spawned_paths: list[Path] = []

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def spawn_after_peer_attempt(
        _cfg,
        ref_obj,
        claimed: Ticket,
        _agent,
        *,
        validate_before_spawn,
        validate_after_spawn,
        **_kwargs,
    ):  # type: ignore[no-untyped-def]
        nonlocal outer_generation, peer_result
        if ref_obj.ticket_path.is_relative_to(peer_root):
            raise AssertionError("a peer must not replace a published claim")
        spawned_paths.append(ref_obj.ticket_path)
        outer_generation = claimed.launch_generation
        assert outer_generation is not None
        # Start the competing megalaunch after A's pre-audit proof, then run
        # the held-child proof that guards the executable boundary.
        validate_before_spawn()
        git_repo.git("pull", "--ff-only", "origin", "main", cwd=peer_root)
        peer_run = run_megalaunch(peer_cfg, selection=[active["slug"]])
        peer_result = peer_run.results[0]
        validate_after_spawn()
        finished = Ticket.read(ref_obj.ticket_path)
        finished.frontmatter["status"] = "done"
        finished.frontmatter.pop("step", None)
        finished.frontmatter.pop("launch_generation", None)
        finished.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr(
        "coga.megalaunch.spawn_agent_session", spawn_after_peer_attempt
    )

    run = run_megalaunch(cfg, selection=[active["slug"]])

    assert run.results[0].outcome == "completed"
    assert run.results[0].launched
    assert spawned_paths == [ticket_path]
    assert peer_result is not None
    assert peer_result.outcome == "failed"
    assert not peer_result.launched
    assert "already carries a published megalaunch claim" in peer_result.detail
    remote = Ticket.parse(
        git_repo.git("show", f"main:{ticket_rel}", cwd=git_repo.origin)
    )
    assert remote.status == "in_progress"
    assert remote.launch_generation == outer_generation


def test_megalaunch_selection_does_not_reactivate_pick_started_during_earlier_launch(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase 3 reclassifies each fresh ticket instead of replaying phase-2 state."""
    cfg = load_config(repo)
    first = create_task(
        cfg=cfg,
        title="Aaa first pick",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )
    started_elsewhere = create_task(
        cfg=cfg,
        title="Bbb concurrently started pick",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )
    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")
    launched: list[str] = []

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(cfg_, ref_obj, ticket_, agent, **kwargs):  # type: ignore[no-untyped-def]
        launched.append(ref_obj.id_slug)
        if ref_obj.id_slug == first["slug"]:
            concurrent = Ticket.read(started_elsewhere["path"])
            concurrent.frontmatter["status"] = "in_progress"
            concurrent.frontmatter["step"] = "1 (implement)"
            concurrent.write(started_elsewhere["path"])
        completed = Ticket.read(ref_obj.ticket_path)
        completed.frontmatter["status"] = "done"
        completed.frontmatter.pop("step", None)
        completed.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(
        cfg,
        selection=[first["slug"], started_elsewhere["slug"]],
    )

    assert launched == [first["slug"], started_elsewhere["slug"]]
    assert run.counts["completed"] == 2
    assert _log_lines_for(cfg, started_elsewhere["slug"], "activated") == []
    assert _log_lines_for(cfg, started_elsewhere["slug"], "started (") == []


def test_megalaunch_selection_recomputes_blocked_resume_after_earlier_launch(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A newly blocked pick launches as a resume and is re-blocked on exit."""
    from coga.blackboard import append_blocker, open_blockers

    cfg = load_config(repo)
    first = create_task(
        cfg=cfg,
        title="Aaa first pick",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )
    newly_blocked = create_task(
        cfg=cfg,
        title="Bbb newly blocked pick",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    ticket = Ticket.read(newly_blocked["path"])
    ticket.frontmatter["status"] = "paused"
    ticket.write(newly_blocked["path"])
    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")
    launched: list[str] = []

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(cfg_, ref_obj, ticket_, agent, **kwargs):  # type: ignore[no-untyped-def]
        launched.append(ref_obj.id_slug)
        if ref_obj.id_slug == first["slug"]:
            append_blocker(
                Path(newly_blocked["path"]),
                actor="claude",
                reason="Need a decision made during the earlier launch",
            )
            concurrent = Ticket.read(newly_blocked["path"])
            concurrent.frontmatter["status"] = "blocked"
            concurrent.write(newly_blocked["path"])
            completed = Ticket.read(ref_obj.ticket_path)
            completed.frontmatter["status"] = "done"
            completed.frontmatter.pop("step", None)
            completed.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(
        cfg,
        selection=[first["slug"], newly_blocked["slug"]],
    )

    result = next(r for r in run.results if r.slug == newly_blocked["slug"])
    assert launched == [first["slug"], newly_blocked["slug"]]
    assert result.outcome == "blocked"
    assert Ticket.read(newly_blocked["path"]).status == "blocked"
    assert len(open_blockers(Path(newly_blocked["path"]))) == 1


def test_megalaunch_selection_reclassifies_captured_blocker_state(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A blocker resolved just before capture cannot bypass the ask gate."""
    from coga.blackboard import (
        append_blocker,
        open_blockers as read_open_blockers,
        resolve_open_blockers,
    )

    cfg = load_config(repo)
    blocked = create_task(
        cfg=cfg,
        title="Blocker resolved during selection",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    ticket_path = Path(blocked["path"])
    append_blocker(ticket_path, actor="claude", reason="Which region?")
    ticket = Ticket.read(ticket_path)
    ticket.frontmatter["status"] = "blocked"
    ticket.write(ticket_path)
    blocker_reads = 0

    def resolve_after_phase_three_classification(path: Path):
        nonlocal blocker_reads
        blocker_reads += 1
        blockers = read_open_blockers(path)
        if blocker_reads == 2:
            assert resolve_open_blockers(
                path,
                actor="marc",
                answer="Resolved independently before activation.",
            )
        return blockers

    def fail_spawn(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("an ask-less blocked ticket must not spawn")

    monkeypatch.setattr(
        "coga.megalaunch.open_blockers",
        resolve_after_phase_three_classification,
    )
    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fail_spawn)

    run = run_megalaunch(cfg, selection=[blocked["slug"]])

    assert blocker_reads == 2
    assert run.counts["skipped-unlaunchable"] == 1
    assert run.results[0].detail == (
        "blocked but has no open blocker asks to resolve"
    )
    retained = Ticket.read(ticket_path)
    assert retained.status == "blocked"
    assert read_open_blockers(ticket_path) == []
    assert _log_lines_for(cfg, blocked["slug"], "activated") == []
    assert _log_lines_for(cfg, blocked["slug"], "started (") == []


def test_megalaunch_selection_refuses_invalid_status_before_spawn(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Narrowing for prospective activation must not admit malformed state."""
    cfg = load_config(repo)
    malformed = create_task(
        cfg=cfg,
        title="Malformed lifecycle",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    ticket = Ticket.read(malformed["path"])
    ticket.frontmatter["status"] = "unexpected"
    ticket.write(malformed["path"])
    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(cfg, selection=[malformed["slug"]])

    result = next(r for r in run.results if r.slug == malformed["slug"])
    assert launched == []
    assert result.outcome == "failed"
    assert result.detail == "status is unexpected; expected active or in_progress"
    assert Ticket.read(malformed["path"]).status == "unexpected"


def test_megalaunch_selection_leaves_picks_beyond_max_tasks_unactivated(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--max-tasks` stops before the second pick, so it is never activated.

    Activation is deferred into each ticket's own launch, so a pick the run
    never reaches keeps its draft status. Deliberate: nothing on disk should
    claim work began on a session that never started.
    """
    cfg = load_config(repo)
    first = create_task(
        cfg=cfg,
        title="Aaa reached pick",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )
    second = create_task(
        cfg=cfg,
        title="Bbb unreached pick",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )
    before = Path(second["path"]).read_bytes()

    launched = _done_on_spawn(monkeypatch)

    run_megalaunch(
        cfg,
        selection=[first["slug"], second["slug"]],
        max_tasks=1,
    )

    assert launched == [first["slug"]]
    assert Path(second["path"]).read_bytes() == before
    assert Ticket.read(second["path"]).status == "draft"
    assert _log_lines_for(cfg, second["slug"], "activated") == []


def test_megalaunch_selection_late_gate_does_not_consume_attempt_budget(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An exact-reread selection skip leaves max-tasks for the next pick."""
    from coga import megalaunch as megalaunch_module

    cfg = load_config(repo)
    first = create_task(
        cfg=cfg,
        title="A selected late gate",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    second = create_task(
        cfg=cfg,
        title="B selected launch",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    real_candidate = megalaunch_module._candidate_result
    changed = False

    def remove_step_after_selection_check(
        cfg_, ref_, ticket_, **kwargs
    ):  # type: ignore[no-untyped-def]
        nonlocal changed
        result = real_candidate(cfg_, ref_, ticket_, **kwargs)
        if ref_.id_slug == first["slug"] and not changed:
            assert kwargs["explicit"] is True
            assert result is None
            changed = True
            peer = Ticket.read(first["path"])
            peer.frontmatter.pop("step", None)
            peer.write(first["path"])
        return result

    monkeypatch.setattr(
        "coga.megalaunch._candidate_result", remove_step_after_selection_check
    )
    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(
        cfg,
        selection=[first["slug"], second["slug"]],
        max_tasks=1,
    )

    assert changed
    assert launched == [second["slug"]]
    assert [result.outcome for result in run.results] == [
        "skipped-human-gate",
        "completed",
    ]


def test_megalaunch_selection_logs_activation_before_start(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A working pick is unchanged: activated first, then started."""
    from coga.paths import log_path

    cfg = load_config(repo)
    draft = create_task(
        cfg=cfg,
        title="Ordinary pick",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )

    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(cfg, selection=[draft["slug"]])

    assert launched == [draft["slug"]]
    assert run.counts["completed"] == 1
    lines = [
        line
        for line in log_path(cfg).read_text().splitlines()
        if f"[{draft['slug']}]" in line
    ]
    activated = next(i for i, line in enumerate(lines) if "activated" in line)
    started = next(i for i, line in enumerate(lines) if "started" in line)
    assert activated < started


def test_megalaunch_selection_authors_drafts_before_any_launch(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every picked draft runs the authoring interview in the prepare phase,
    and all authoring happens before any working launch starts."""
    cfg = load_config(repo)
    first = create_task(
        cfg=cfg,
        title="Aaa draft one",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )
    second = create_task(
        cfg=cfg,
        title="Bbb draft two",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )
    # Strip both workflows so they are genuinely not-ready; the stubbed
    # interview writes one back, standing in for a real authoring session.
    for created in (first, second):
        t = Ticket.read(created["path"])
        t.frontmatter["workflow"] = None
        t.write(created["path"])

    events: list[tuple[str, str]] = []

    def fake_author(  # type: ignore[no-untyped-def]
        cfg_, ref, ticket, *, agent_override=None
    ):
        events.append(("author", ref.id_slug))
        assert agent_override == "codex"
        t = Ticket.read(ref.ticket_path)
        t.frontmatter["workflow"] = "code"
        t.write(ref.ticket_path)

    monkeypatch.setattr("coga.megalaunch._author_draft", fake_author)
    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(cfg_, ref_obj, ticket_, agent, **kwargs):  # type: ignore[no-untyped-def]
        events.append(("launch", ref_obj.id_slug))
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "done"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(
        cfg,
        selection=[first["slug"], second["slug"]],
        author_drafts=True,
        agent_override="codex",
    )

    assert run.counts["completed"] == 2
    # Both drafts were authored, and every author preceded every launch.
    kinds = [kind for kind, _ in events]
    assert kinds == ["author", "author", "launch", "launch"]
    assert {slug for kind, slug in events if kind == "author"} == {
        first["slug"],
        second["slug"],
    }


def test_megalaunch_selection_without_opt_in_skips_authoring(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A draft with `author_drafts=False` (the default) is never authored — it
    activates and launches on the workflow it already has."""
    cfg = load_config(repo)
    draft = create_task(
        cfg=cfg,
        title="Ready draft",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )

    def boom(  # type: ignore[no-untyped-def]
        cfg_, ref, ticket, *, agent_override=None
    ):
        raise AssertionError("authoring must not run without opt-in")

    monkeypatch.setattr("coga.megalaunch._author_draft", boom)
    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(cfg, selection=[draft["slug"]])  # author_drafts defaults off

    assert launched == [draft["slug"]]
    assert run.counts["completed"] == 1
    assert Ticket.read(draft["path"]).status == "done"


def test_megalaunch_selection_draft_unready_after_authoring_is_reported(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the authoring interview leaves a draft not-ready, the pick is
    reported as unlaunchable rather than silently dropped."""
    cfg = load_config(repo)
    draft = create_task(
        cfg=cfg,
        title="Never made ready",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )
    t = Ticket.read(draft["path"])
    t.frontmatter["workflow"] = None
    t.write(draft["path"])

    # The interview runs but the human leaves without adding a workflow.
    monkeypatch.setattr(
        "coga.megalaunch._author_draft",
        lambda cfg_, ref, ticket, *, agent_override=None: None,
    )
    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(cfg, selection=[draft["slug"]], author_drafts=True)

    assert launched == []
    assert run.counts["skipped-unlaunchable"] == 1
    assert "no workflow" in run.results[0].detail


def test_author_draft_without_bootstrap_is_noop(repo: Path) -> None:
    """`_author_draft` returns quietly when there is no bootstrap/ticket to
    run — the draft is left untouched for the activate phase to judge."""
    from coga.megalaunch import _author_draft
    from coga.tasks import resolve_task

    cfg = load_config(repo)
    draft = create_task(
        cfg=cfg,
        title="Lonely draft",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )
    ref = resolve_task(cfg, draft["slug"])
    before = Ticket.read(draft["path"]).frontmatter

    _author_draft(cfg, ref, Ticket.read(draft["path"]))  # must not raise

    assert Ticket.read(draft["path"]).frontmatter == before


def test_author_draft_prefers_megalaunch_agent_override(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The megalaunch override also selects the picked draft's authoring
    assistant, without changing the ticket's persisted assignee."""
    from coga.megalaunch import _author_draft
    from coga.tasks import resolve_task

    cfg = load_config(repo)
    draft = create_task(
        cfg=cfg,
        title="Author with Codex",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )
    ref = resolve_task(cfg, draft["slug"])
    captured: dict[str, object] = {}

    # Reusing the draft as the bootstrap ref gives the fallback path a Claude
    # assignee. The explicit Codex override must still win.
    monkeypatch.setattr(
        "coga.megalaunch.resolve_bootstrap", lambda cfg_, name: ref
    )
    monkeypatch.setattr(
        "coga.commands.ticket._run_authoring_session",
        lambda **kwargs: captured.update(kwargs),
    )

    _author_draft(
        cfg,
        ref,
        Ticket.read(draft["path"]),
        agent_override="codex",
    )

    assert captured["launch_assignee"] == "codex"
    assert Ticket.read(draft["path"]).assignee == "claude"


def test_megalaunch_selection_resumes_blocked_and_reblocks_unresolved(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A picked blocked ticket resumes; an unresolved exit re-blocks it."""
    from coga.blackboard import append_blocker

    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Blocked pick",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    append_blocker(Path(ref["path"]), actor="claude", reason="Which region?")
    ticket = Ticket.read(ref["path"])
    ticket.frontmatter["status"] = "blocked"
    ticket.write(ref["path"])

    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")
    launched: list[str] = []
    prompts: list[str] = []

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(cfg_, ref_obj, ticket_, agent, **kwargs):  # type: ignore[no-untyped-def]
        # The agent session exits without resolving the ask.
        launched.append(ref_obj.id_slug)
        prompts.append(
            " ".join(
                compose_prompt(
                    cfg_, ref_obj, ticket_, launch_context=kwargs["launch_context"]
                ).split()
            )
        )
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg, selection=[ref["slug"]])

    assert launched == [ref["slug"]]
    assert "Existing blocker-resolution exception" in prompts[0]
    assert "resolve those already-open asks" in prompts[0]
    assert "new unavailable input still follows the queue rule" in prompts[0]
    # The state-derived preamble still composes independently of conduct.
    assert "Resolve the open blocker first" in prompts[0]
    assert run.counts["blocked"] == 1
    assert "Which region?" in run.results[0].detail
    # The unresolved ask returns the ticket to the blocked queue.
    assert Ticket.read(ref["path"]).status == "blocked"


def test_megalaunch_selection_blocked_resume_resolves_and_completes(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A resumed blocked pick whose session resolves the ask runs to done."""
    from coga.blackboard import append_blocker, resolve_open_blockers

    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Blocked then resolved",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    append_blocker(Path(ref["path"]), actor="claude", reason="Which region?")
    ticket = Ticket.read(ref["path"])
    ticket.frontmatter["status"] = "blocked"
    ticket.write(ref["path"])

    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")
    launched: list[str] = []

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(cfg_, ref_obj, ticket_, agent, **kwargs):  # type: ignore[no-untyped-def]
        # The session resolves the ask and finishes the task.
        launched.append(ref_obj.id_slug)
        resolve_open_blockers(ref_obj.ticket_path, actor="marc", answer="eu-west-1")
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "done"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg, selection=[ref["slug"]])

    assert launched == [ref["slug"]]
    assert run.counts["completed"] == 1
    assert Ticket.read(ref["path"]).status == "done"


def test_megalaunch_selection_unknown_slug_fails_loud(repo: Path) -> None:
    from coga.megalaunch import MegalaunchError

    cfg = load_config(repo)

    with pytest.raises(MegalaunchError, match="not found"):
        run_megalaunch(cfg, selection=["no-such-task"])


def test_launchable_candidates_offers_any_owner_any_non_terminal_status(
    repo: Path,
) -> None:
    """The picker offers every explicitly launchable task, not just mine."""
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
    draft = create_task(  # draft with a workflow — offered (activates inline)
        cfg=cfg,
        title="Still a draft",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )
    foreign = create_task(  # someone else's — offered (explicit picks launch it)
        cfg=cfg,
        title="Lea's work",
        workflow_name="code",
        contexts=[],
        owner="lea",
        assignee="claude",
        status="active",
        watchers=[],
    )
    paused = create_task(
        cfg=cfg,
        title="Paused one",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    ticket = Ticket.read(paused["path"])
    ticket.frontmatter["status"] = "paused"
    ticket.write(paused["path"])
    done = create_task(  # done — never offered
        cfg=cfg,
        title="Finished",
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
    canceled = create_task(  # canceled — never offered
        cfg=cfg,
        title="Declined",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="canceled",
        watchers=[],
    )
    human = create_task(  # human-assigned — still offered; the picker no longer
        cfg=cfg,           # pre-filters launchability, the run reports the gate.
        title="Human work",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="marc",
        status="active",
        watchers=[],
    )
    ticket = Ticket.read(human["path"])
    ticket.frontmatter["assignee"] = "marc"
    ticket.write(human["path"])
    workflowless = create_task(  # draft with no workflow — still offered:
        cfg=cfg,                  # the prepare phase authors it into shape.
        title="Shapeless draft",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="draft",
        watchers=[],
    )
    ticket = Ticket.read(workflowless["path"])
    ticket.frontmatter["workflow"] = None
    ticket.write(workflowless["path"])

    offered = {ref.id_slug for ref, _ in launchable_candidates(cfg)}

    # Everything non-terminal is offered — done/canceled are the only exclusions.
    assert offered == {
        active["slug"],
        running["slug"],
        draft["slug"],
        foreign["slug"],
        paused["slug"],
        workflowless["slug"],
        human["slug"],
    }
    assert done["slug"] not in offered
    assert canceled["slug"] not in offered


def test_launchable_candidates_blocked_needs_open_asks(repo: Path) -> None:
    """Both blocked tickets are offered; the run reports the ask-less one.

    The picker no longer pre-filters launchability — a blocked ticket with no
    open ask shows up too, and the staged run classifies it as
    `skipped-unlaunchable` rather than hiding it from the operator.
    """
    from coga.blackboard import append_blocker
    from coga.megalaunch import launchable_candidates

    cfg = load_config(repo)
    with_ask = create_task(
        cfg=cfg,
        title="Blocked with ask",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    append_blocker(Path(with_ask["path"]), actor="claude", reason="Which region?")
    ticket = Ticket.read(with_ask["path"])
    ticket.frontmatter["status"] = "blocked"
    ticket.write(with_ask["path"])
    askless = create_task(
        cfg=cfg,
        title="Blocked without ask",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    ticket = Ticket.read(askless["path"])
    ticket.frontmatter["status"] = "blocked"
    ticket.write(askless["path"])

    offered = {ref.id_slug for ref, _ in launchable_candidates(cfg)}

    assert offered == {with_ask["slug"], askless["slug"]}


def test_launchable_candidates_ordered_like_status_updated_first(
    repo: Path,
) -> None:
    """The picker lists tasks like the default `coga status` view.

    Last updated first (the last log line per ref), tasks with no recorded
    activity in a trailing bucket — not drain order. Display only: the engine
    re-derives the launch queue in drain order from the confirmed set.
    """
    from coga.megalaunch import launchable_candidates
    from coga.paths import log_path

    cfg = load_config(repo)
    for title in ("Stale", "Fresh", "Silent"):
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
    # Rewrite the log: stale was created first but touched earlier than fresh,
    # and silent has no log line at all (and no git fallback in a non-git tmp
    # repo), so drain order would read [stale, fresh, silent] while the status
    # order under test reads newest activity first with silent trailing.
    log_path(cfg).write_text(
        "2026-06-01 10:00 [stale] [human:marc] created\n"
        "2026-06-02 10:00 [fresh] [human:marc] created\n"
        "2026-06-03 10:00 [stale] [human:marc] bumped\n"
        "2026-06-04 10:00 [fresh] [human:marc] bumped\n"
    )

    assert [ref.id_slug for ref, _ in launchable_candidates(cfg)] == [
        "fresh",
        "stale",
        "silent",
    ]


def test_save_and_load_selection_roundtrip(repo: Path) -> None:
    from coga.megalaunch import MegalaunchError, load_selection, save_selection

    cfg = load_config(repo)

    with pytest.raises(MegalaunchError, match="No saved selection"):
        load_selection(cfg)

    save_selection(cfg, ["a-task", "dir/another"])

    assert load_selection(cfg) == ["a-task", "dir/another"]
    assert (repo / ".coga" / "megalaunch-selection.json").is_file()


def test_decode_key() -> None:
    from coga.commands.megalaunch import _decode_key

    assert _decode_key(b"\x1b[A") == "up"
    assert _decode_key(b"k") == "up"
    assert _decode_key(b"\x1b[B") == "down"
    assert _decode_key(b"j") == "down"
    assert _decode_key(b" ") == "space"
    assert _decode_key(b"\r") == "enter"
    assert _decode_key(b"\n") == "enter"
    assert _decode_key(b"q") == "quit"
    assert _decode_key(b"\x1b") == "quit"  # bare Esc
    assert _decode_key(b"\x03") == "quit"  # Ctrl-C
    assert _decode_key(b"a") == "all"
    assert _decode_key(b"n") == "none"
    assert _decode_key(b"x") == ""  # unknown keys are ignored


def test_picker_window_keeps_cursor_visible() -> None:
    """Long lists window to a viewport that always contains the cursor."""
    from coga.commands.megalaunch import _picker_window

    # Short list: no windowing, everything is shown.
    assert _picker_window(total=5, cursor=0, rows=10) == (0, 5)
    assert _picker_window(total=10, cursor=9, rows=10) == (0, 10)

    # Long list: the window is exactly `rows` tall and never drops the cursor.
    for cursor in range(50):
        start, end = _picker_window(total=50, cursor=cursor, rows=10)
        assert end - start == 10
        assert start <= cursor < end
        assert 0 <= start and end <= 50

    # Top and bottom clamp so we never scroll past the ends.
    assert _picker_window(total=50, cursor=0, rows=10)[0] == 0
    assert _picker_window(total=50, cursor=49, rows=10) == (40, 50)

    # A degenerate terminal height still yields a usable window.
    assert _picker_window(total=50, cursor=20, rows=0) == (0, 50)


def test_picker_view_fits_the_terminal_at_every_size() -> None:
    """The rendered picker is exactly one line per candidate plus 5 of chrome.

    `_picker_window` budgets in candidates while the terminal budgets in lines,
    so anything that wraps — a row, the hint line, a scroll indicator — costs
    more than its one budgeted line. Live keeps only the *first* screenful of
    an overflowing render, so the cursor disappears on the way down the list.
    """
    from rich.console import Console

    from coga.commands.megalaunch import _picker_view
    from coga.tasks import TaskRef

    def candidate(
        index: int,
        title: str,
        owner: str = "zach",
        step: str = "1 (implement)",
    ) -> tuple:
        # Slugs are derived from titles, so real ones run this long. A short
        # stand-in leaves the table inside its width budget and the layout
        # never gets stressed.
        slug = f"a-command-that-reads-machine-local-config-gives-a-{index:02d}"
        return (
            TaskRef(
                slug=slug,
                path=Path(f"coga/tasks/{slug}.md"),
                file_form=True,
            ),
            Ticket(
                frontmatter={
                    "title": title,
                    "status": "in_progress",
                    "owner": owner,
                    "step": step,
                },
                body="",
            ),
        )

    candidates = [
        candidate(
            index,
            f"candidate {index} with a deliberately long title that wraps on "
            "any terminal narrower than a billboard",
        )
        for index in range(39)
    ]
    # Long values in narrow columns push the table over budget, which is what
    # makes Rich shrink every column and wrap the "[x]" checkbox. This step is
    # an existing valid workflow label, not a synthetic extreme.
    candidates[7] = candidate(
        7,
        "short",
        owner="replace-with-human-name",
        step="2 (human-owns-and-finishes)",
    )
    # Mid-list cursors matter: only there are both scroll indicators drawn, so
    # only there does an under-reserved chrome budget overflow.
    cursors = [0, 1, len(candidates) // 2, len(candidates) - 2, len(candidates) - 1]

    for width, height in [(100, 50), (80, 24), (50, 30), (40, 30), (100, 5)]:
        # `max(1, ...)` is the floor for degenerate terminals: a 5-line
        # terminal still needs one row plus 5 lines of chrome.
        rows = max(1, height - 5)
        expected = min(len(candidates), rows) + 5
        for cursor in cursors:
            console = Console(width=width, height=height)
            # No explicit `height` render option: Rich would pad or crop to it
            # and the assertion would pass vacuously.
            lines = console.render_lines(
                _picker_view(candidates, {cursor}, cursor, console)
            )
            # Exact, not `<=`: a wrapped row can still happen to fit the
            # terminal while breaking the one-line-per-candidate invariant.
            # Both scroll-indicator slots are always rendered, blank when there
            # is nothing above or below, so chrome is an unconditional 5 lines
            # and the frame does not jitter by a row at either end of the list.
            assert len(lines) == expected, (
                f"{width}x{height} cursor={cursor} rendered {len(lines)} lines, "
                f"expected {expected}"
            )
            # Fitting is only half of it: the cursor's row has to be one of the
            # rows actually drawn. It carries the reverse style, which — unlike
            # the "❯" marker column — survives however narrow the terminal.
            highlighted = sum(
                any(segment.style and segment.style.reverse for segment in line)
                for line in lines
            )
            assert highlighted == 1, (
                f"cursor row not drawn at {width}x{height} cursor={cursor}"
            )
            # Truncation alone fits the terminal but can still gut the layout:
            # if Rich has to shrink every column it empties the one-cell marker
            # and three-cell checkbox first, and the picker stops showing where
            # the cursor is or what is selected. 50 cells is the narrowest
            # width these survive; below that all seven columns cannot fit.
            if width >= 50:
                rendered = [
                    "".join(segment.text for segment in line) for line in lines
                ]
                assert any("❯" in text for text in rendered), (
                    f"cursor marker collapsed at {width}x{height} cursor={cursor}"
                )
                assert any("[x]" in text for text in rendered), (
                    f"checkbox collapsed at {width}x{height} cursor={cursor}"
                )


def test_read_key_resize_beats_pending_keypress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A byte on the resize pipe wins over a queued keypress and comes back as
    the synthetic "resize" action; the keypress survives for the next read."""
    import os
    import pty
    import tty
    import types

    from coga.commands.megalaunch import _read_key

    master, slave = pty.openpty()
    resize_read, resize_write = os.pipe()
    monkeypatch.setattr("sys.stdin", types.SimpleNamespace(fileno=lambda: slave))
    try:
        # Raw before writing: a byte queued while the slave is still canonical
        # sits in the line buffer and never becomes select()-readable.
        tty.setraw(slave)
        os.write(master, b"j")
        # What signal.set_wakeup_fd would deliver for SIGWINCH.
        os.write(resize_write, b"\x1c")
        assert _read_key(resize_read) == "resize"
        assert _read_key(resize_read) == "down"
    finally:
        for fd in (master, slave, resize_read, resize_write):
            os.close(fd)


def _feed_keys(monkeypatch: pytest.MonkeyPatch, keys: list[str]) -> None:
    """Drive the picker with decoded key actions instead of a raw terminal."""
    pending = iter(keys)
    monkeypatch.setattr(
        "coga.commands.megalaunch._read_key", lambda _resize_fd: next(pending)
    )


def test_megalaunch_cli_picker_launches_checked_tasks(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`coga megalaunch --pick` starts unchecked; Space opts a task in."""
    from typer.testing import CliRunner

    cfg = load_config(repo)
    first = create_task(
        cfg=cfg,
        title="Check me",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    second = create_task(
        cfg=cfg,
        title="Leave me unchecked",
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

    # Check the first task with Space (unknown keys are ignored), Enter.
    _feed_keys(monkeypatch, ["space", "", "enter"])
    result = CliRunner().invoke(app, ["megalaunch", "--pick"])

    assert result.exit_code == 0, result.output
    assert launched == [first["slug"]]
    assert Ticket.read(first["path"]).status == "done"
    assert Ticket.read(second["path"]).status == "active"
    # The confirmed selection is saved for --relaunch.
    from coga.megalaunch import load_selection

    assert load_selection(cfg) == [first["slug"]]


def test_megalaunch_cli_pick_prompts_before_authoring_drafts(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Picking a draft raises the one-shot batch prompt; 'y' runs authoring,
    'n' skips it — either way the ready draft still launches."""
    from typer.testing import CliRunner

    cfg = load_config(repo)

    monkeypatch.setattr(
        "coga.commands.megalaunch._interactive_stdio_has_tty", lambda: True
    )
    monkeypatch.setattr(
        "coga.commands.megalaunch.notification.post", lambda cfg, msg: None
    )

    for answer, expect_authored in (("y", True), ("n", False)):
        draft = create_task(
            cfg=cfg,
            title=f"Draft answered {answer}",
            workflow_name="code",
            contexts=[],
            owner="marc",
            assignee="claude",
            status="draft",
            watchers=[],
        )
        authored: list[str] = []
        monkeypatch.setattr(
            "coga.megalaunch._author_draft",
            lambda cfg_, ref, ticket, *, agent_override=None, _a=authored: (
                _a.append(ref.id_slug)
            ),
        )
        _done_on_spawn(monkeypatch)
        # Only this draft is offered (prior iterations' tasks are already done).
        _feed_keys(monkeypatch, ["space", "enter"])
        result = CliRunner().invoke(app, ["megalaunch", "--pick"], input=f"{answer}\n")

        assert result.exit_code == 0, result.output
        assert "run the guided authoring interview" in result.output
        assert (draft["slug"] in authored) is expect_authored
        assert Ticket.read(draft["path"]).status == "done"


def test_megalaunch_cli_pick_ready_work_is_not_prompted(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pick with no drafts never raises the authoring prompt."""
    from typer.testing import CliRunner

    cfg = load_config(repo)
    ready = create_task(
        cfg=cfg,
        title="Ready active",
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
    _done_on_spawn(monkeypatch)

    _feed_keys(monkeypatch, ["space", "enter"])
    result = CliRunner().invoke(app, ["megalaunch", "--pick"])

    assert result.exit_code == 0, result.output
    assert "authoring interview" not in result.output
    assert Ticket.read(ready["path"]).status == "done"


def test_megalaunch_cli_picker_moves_and_toggles(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Arrows move the cursor; Space toggles the row under it."""
    from typer.testing import CliRunner

    cfg = load_config(repo)
    # Titles sort the same by creation time and slug, so the row order is
    # stable even when the create timestamps tie.
    first = create_task(
        cfg=cfg,
        title="Aaa skipped over",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    second = create_task(
        cfg=cfg,
        title="Bbb picked below",
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

    # Down to the second row, check it, then toggle it off and on again.
    _feed_keys(monkeypatch, ["down", "space", "space", "space", "enter"])
    result = CliRunner().invoke(app, ["megalaunch", "--pick"])

    assert result.exit_code == 0, result.output
    assert launched == [second["slug"]]
    assert Ticket.read(first["path"]).status == "active"


def test_megalaunch_cli_picker_resize_keeps_state(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The synthetic "resize" action re-renders without disturbing the
    selection, and the picker restores the SIGWINCH handler it installed."""
    import signal

    from typer.testing import CliRunner

    cfg = load_config(repo)
    picked = create_task(
        cfg=cfg,
        title="Survives a resize",
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
    handler_before = signal.getsignal(signal.SIGWINCH)

    _feed_keys(monkeypatch, ["space", "resize", "enter"])
    result = CliRunner().invoke(app, ["megalaunch", "--pick"])

    assert result.exit_code == 0, result.output
    assert launched == [picked["slug"]]
    assert signal.getsignal(signal.SIGWINCH) is handler_before


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

    _feed_keys(monkeypatch, ["quit"])
    result = CliRunner().invoke(app, ["megalaunch", "--pick"])

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

    # `a` checks the whole (dir-scoped) list, Enter launches it.
    _feed_keys(monkeypatch, ["all", "enter"])
    result = CliRunner().invoke(app, ["megalaunch", "marketing", "--pick"])

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


def test_megalaunch_disappeared_activation_ticket_fails_only_its_task(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A removal during snapshot capture becomes one failed queue row."""
    from coga import git as git_module

    cfg = load_config(repo)
    first = create_task(
        cfg=cfg,
        title="A disappearing paused task",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="paused",
        watchers=[],
    )
    second = create_task(
        cfg=cfg,
        title="B still launches",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    first_path = Path(first["path"])
    real_capture = git_module.FileMutationRollback.capture
    disappeared = False

    def disappear_during_capture(paths, *, union_paths=()):  # type: ignore[no-untyped-def]
        nonlocal disappeared
        captured_paths = tuple(paths)
        if first_path in captured_paths and not disappeared:
            disappeared = True
            first_path.unlink()
        return real_capture(captured_paths, union_paths=union_paths)

    monkeypatch.setattr(
        git_module.FileMutationRollback,
        "capture",
        staticmethod(disappear_during_capture),
    )
    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(cfg, selection=[first["slug"], second["slug"]])

    assert disappeared
    assert launched == [second["slug"]]
    assert [(result.slug, result.outcome) for result in run.results] == [
        (first["slug"], "failed"),
        (second["slug"], "completed"),
    ]
    assert run.results[0].detail == "ticket disappeared before launch"


def test_megalaunch_disappeared_prompt_layer_fails_only_its_task(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A raw preflight file race becomes one failed row, not a sweep crash."""
    import coga.megalaunch as megalaunch_module

    cfg = load_config(repo)
    first = create_task(
        cfg=cfg,
        title="A missing context",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    second = create_task(
        cfg=cfg,
        title="B still launches",
        workflow_name="code",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    missing = str(repo / "contexts" / "vanished" / "SKILL.md")
    real_compose = megalaunch_module.compose_prompt

    def flaky_compose(cfg_, ref_obj, ticket, *args, **kwargs):
        if ref_obj.id_slug == first["slug"]:
            raise FileNotFoundError(2, "No such file or directory", missing)
        return real_compose(cfg_, ref_obj, ticket, *args, **kwargs)

    monkeypatch.setattr(megalaunch_module, "compose_prompt", flaky_compose)
    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(cfg)

    assert launched == [second["slug"]]
    assert [(result.slug, result.outcome) for result in run.results] == [
        (first["slug"], "failed"),
        (second["slug"], "completed"),
    ]
    assert missing in run.results[0].detail
    assert "not the agent CLI" in run.results[0].detail


def test_megalaunch_missing_packaged_prompt_fails_task_not_sweep(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A packaged prompt resource that vanishes mid-run fails that one task.

    The real case: `coga megalaunch` sweeps for an hour while the operator
    reinstalls the CLI underneath it (an editable reinstall drops the top-level
    `coga/resources/*.md` out of site-packages entirely). The already-imported
    process keeps running, but the *lazy* resource read at the next compose
    hits a deleted file. That must be a per-task `failed` row like any other
    preflight refusal — not a bare FileNotFoundError unwinding out of
    `run_megalaunch` and taking the rest of the queue (and the run summary)
    with it.
    """
    import coga.paths

    real_files = coga.paths.files
    state = {"gone": True}

    class _GoneResource:
        def read_text(self, *args: object, **kwargs: object) -> str:
            # Vanish for exactly one read, so the next task still services.
            state["gone"] = False
            raise FileNotFoundError(2, "No such file or directory", "prompt.md")

    class _Shim:
        def __init__(self, real: object) -> None:
            self._real = real

        def joinpath(self, *parts: str) -> object:
            if state["gone"] and parts == ("prompt.md",):
                return _GoneResource()
            return self._real.joinpath(*parts)  # type: ignore[attr-defined]

    cfg = load_config(repo)
    for title in ("A gone", "B run me"):
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

    monkeypatch.setattr(
        "coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}"
    )

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(cfg_, ref_obj, ticket_, agent, **kwargs):  # type: ignore[no-untyped-def]
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "done"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)
    monkeypatch.setattr("coga.paths.files", lambda package: _Shim(real_files(package)))

    run = run_megalaunch(cfg)

    assert [(r.slug, r.outcome) for r in run.results] == [
        ("a-gone", "failed"),
        ("b-run-me", "completed"),
    ]
    detail = run.results[0].detail
    assert "prompt.md" in detail
    assert "installed Coga package" in detail
    # The run still summarizes instead of dying on a traceback.
    assert run.counts["failed"] == 1
    assert run.counts["completed"] == 1
