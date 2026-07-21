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
        seen["prompt_suffix"] = kwargs.get("prompt_suffix")
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
    suffix = " ".join(str(seen["prompt_suffix"]).split())
    assert "Megalaunch queue execution" in suffix
    assert "Do not ask for plan" in suffix
    # The appended queue directive overrides the attended ask-and-wait
    # default composed into Agent mode...
    assert "overrides the attended ask-and-wait default in Agent mode" in suffix
    assert "Do not ask-and-wait for missing input here" in suffix
    # ...and unavailable input must end in a terminal `coga block`.
    assert (
        'run `coga block --task <slug> --reason "<specific ask>"` as the'
        " terminal action" in suffix
    )


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

    run = run_megalaunch(cfg, selection=[done["slug"], workflowless["slug"]])

    assert launched == []
    assert run.counts["skipped-unlaunchable"] == 2
    outcomes = {result.slug: result.detail for result in run.results}
    assert outcomes[done["slug"]] == "status is done"
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

    def fake_author(cfg_, ref, ticket):  # type: ignore[no-untyped-def]
        events.append(("author", ref.id_slug))
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
        cfg, selection=[first["slug"], second["slug"]], author_drafts=True
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

    def boom(cfg_, ref, ticket):  # type: ignore[no-untyped-def]
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
    monkeypatch.setattr("coga.megalaunch._author_draft", lambda cfg_, ref, ticket: None)
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
    prompt_suffixes: list[str] = []

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(cfg_, ref_obj, ticket_, agent, **kwargs):  # type: ignore[no-untyped-def]
        # The agent session exits without resolving the ask.
        launched.append(ref_obj.id_slug)
        prompt_suffixes.append(" ".join(str(kwargs["prompt_suffix"]).split()))
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg, selection=[ref["slug"]])

    assert launched == [ref["slug"]]
    assert "Existing blocker-resolution exception" in prompt_suffixes[0]
    assert "resolve those already-open asks" in prompt_suffixes[0]
    assert (
        "new unavailable input still follows the queue rule"
        in prompt_suffixes[0]
    )
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


def test_launchable_candidates_offers_any_owner_any_status_but_done(
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
    human = create_task(  # human-assigned — never offered (no agent to spawn)
        cfg=cfg,
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

    assert offered == {
        active["slug"],
        running["slug"],
        draft["slug"],
        foreign["slug"],
        paused["slug"],
        workflowless["slug"],
    }


def test_launchable_candidates_blocked_needs_open_asks(repo: Path) -> None:
    """A blocked ticket is offered only when it has an ask to resolve."""
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

    assert offered == {with_ask["slug"]}


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
            lambda cfg_, ref, ticket, _a=authored: _a.append(ref.id_slug),
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

# --- script steps ---------------------------------------------------------------
#
# A script launch — a script-backed current step or a
# ticket-owned `script:` — is megalaunch's to run, exactly like the
# `coga launch` supervisor: the sweep executes the script in-process (no agent,
# no REPL), exit 0 advances the step, and a non-zero exit fails that one task
# without stopping the rest of the sweep.


def _write_script_step_workflow(repo: Path) -> None:
    """A three-step workflow with a deterministic script step in the middle."""
    _write(
        repo / "workflows" / "pr.md",
        """
        ---
        name: pr
        description: agent step, then a script step, then human review.
        steps:
          - name: implement
            assignee: agent
          - name: ship
            assignee: agent
            skills:
              - ops/opener
          - name: review
            assignee: owner
        ---
        """,
    )
    _write(
        repo / "skills" / "ops" / "opener" / "SKILL.md",
        """
        ---
        name: ops/opener
        description: deterministic step.
        script: open.sh
        ---

        Opens the PR.
        """,
    )
    script = repo / "skills" / "ops" / "opener" / "open.sh"
    script.write_text('#!/bin/sh\ntouch "$PWD/pr-opened.txt"\n')
    script.chmod(0o755)


def test_megalaunch_runs_script_step_task(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ticket parked on a script-backed step launches: the sweep runs the
    script itself, the step advances on exit 0, and the chain stops at the
    human review handoff."""
    _write_script_step_workflow(repo)
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Ship it",
        workflow_name="pr",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    ticket = Ticket.read(ref["path"])
    ticket.frontmatter["step"] = "2 (ship)"
    ticket.write(ref["path"])

    def fail_spawn(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("a script step must not spawn an agent")

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fail_spawn)

    run = run_megalaunch(cfg)

    assert (cfg.repo_root.parent / "pr-opened.txt").exists()
    assert run.counts["launched"] == 1
    assert run.counts["completed"] == 1
    assert "handed off to marc" in run.results[0].detail
    after = Ticket.read(ref["path"])
    assert after.step == "3 (review)"
    assert after.assignee == "marc"


def test_megalaunch_failed_script_step_fails_task_not_sweep(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-zero script exit fails that task's result, leaves the step put,
    and the sweep still services the next task."""
    _write_script_step_workflow(repo)
    script = repo / "skills" / "ops" / "opener" / "open.sh"
    script.write_text("#!/bin/sh\nexit 3\n")
    script.chmod(0o755)
    cfg = load_config(repo)
    failing = create_task(
        cfg=cfg,
        title="A fail",
        workflow_name="pr",
        contexts=[],
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    ticket = Ticket.read(failing["path"])
    ticket.frontmatter["step"] = "2 (ship)"
    ticket.write(failing["path"])
    create_task(
        cfg=cfg,
        title="B run me",
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

    run = run_megalaunch(cfg)

    assert [(r.slug, r.outcome) for r in run.results] == [
        ("a-fail", "failed"),
        ("b-run-me", "completed"),
    ]
    assert "script step 2 (ship) exited with code 3" in run.results[0].detail
    assert Ticket.read(failing["path"]).step == "2 (ship)"


def test_megalaunch_chains_agent_bump_into_script_step(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When an agent step bumps into a script step, the chain runs the script
    directly instead of spawning an agent REPL on it."""
    _write_script_step_workflow(repo)
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Chain me",
        workflow_name="pr",
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

    spawned_steps: list[str] = []

    def fake_spawn(cfg_, ref_obj, ticket_, agent, **kwargs):  # type: ignore[no-untyped-def]
        updated = Ticket.read(ref_obj.ticket_path)
        spawned_steps.append(updated.step or "")
        updated.frontmatter["step"] = "2 (ship)"
        updated.frontmatter["assignee"] = "claude"
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg)

    assert spawned_steps == ["1 (implement)"]
    assert (cfg.repo_root.parent / "pr-opened.txt").exists()
    assert run.counts["launched"] == 1
    assert run.counts["completed"] == 1
    after = Ticket.read(ref["path"])
    assert after.step == "3 (review)"
    assert after.assignee == "marc"


def test_launchable_candidates_includes_script_step_tasks(repo: Path) -> None:
    """Script launches run without an agent, so the picker offers them even
    when the assignee isn't a configured agent — the same exemption
    `coga launch` applies at its entry."""
    from coga.megalaunch import launchable_candidates

    _write_script_step_workflow(repo)
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Ship it",
        workflow_name="pr",
        contexts=[],
        owner="marc",
        assignee="marc",
        status="active",
        watchers=[],
    )
    ticket = Ticket.read(ref["path"])
    ticket.frontmatter["step"] = "2 (ship)"
    ticket.write(ref["path"])

    candidates = launchable_candidates(cfg)

    assert [r.id_slug for r, _ in candidates] == ["ship-it"]
