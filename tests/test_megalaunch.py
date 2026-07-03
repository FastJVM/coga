from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from textwrap import dedent

import pytest

from coga.cli import app
from coga.config import load_config
from coga.create import create_task
from coga.megalaunch import run_megalaunch, trim_megalaunch_blackboard_text
from coga.ticket import Ticket
from coga.usage_probe import UsageProbe, UsageSnapshot, UsageWindow


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _snapshot(
    session_used: float = 0.0,
    weekly_used: float = 0.0,
    agent: str = "claude",
) -> UsageSnapshot:
    now = datetime.now(timezone.utc)
    return UsageSnapshot(
        agent=agent,
        session=UsageWindow(session_used, now + timedelta(hours=5)),
        # Resets inside the final pacing window, so only the hard floor applies.
        weekly=UsageWindow(weekly_used, now + timedelta(hours=1)),
    )


class _FakeProbe(UsageProbe):
    """Replays a snapshot sequence; the last entry repeats forever."""

    def __init__(self, snapshots: list[UsageSnapshot | None]) -> None:
        self._snapshots = list(snapshots)
        self.reads = 0

    def read(self) -> UsageSnapshot | None:
        self.reads += 1
        if len(self._snapshots) > 1:
            return self._snapshots.pop(0)
        return self._snapshots[0]


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
    # Never build real probes in the suite — the Claude probe would read the
    # developer's live credentials and hit the network. Budget-specific tests
    # override this with their own sequences.
    monkeypatch.setattr(
        "coga.usage_probe.build_probes",
        lambda cfg: {"claude": _FakeProbe([_snapshot()])},
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
        mode="agent",
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
        cfg, ref_obj, ticket, agent, mode, **kwargs
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
        mode="agent",
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
        cfg, ref_obj, ticket, agent, mode, **kwargs
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


def test_megalaunch_agent_filter_only_drains_matching_assignee(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(repo)
    claude_ref = create_task(
        cfg=cfg,
        title="Claude work",
        workflow_name="code",
        contexts=[],
        mode="agent",
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
        mode="agent",
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

    launched: list[str] = []

    def fake_spawn(cfg, ref_obj, ticket, agent, mode, **kwargs):  # type: ignore[no-untyped-def]
        launched.append(ref_obj.id_slug)
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "done"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(
        cfg,
        agent_filter="codex",
        probes={"codex": _FakeProbe([_snapshot(agent="codex")])},
    )

    assert run.agent_filter == "codex"
    assert launched == [codex_ref["slug"]]
    assert [result.slug for result in run.results] == [codex_ref["slug"]]
    assert run.counts["launched"] == 1
    assert run.counts["completed"] == 1
    assert Ticket.read(codex_ref["path"]).status == "done"
    assert Ticket.read(claude_ref["path"]).status == "active"


def test_megalaunch_agent_filter_stops_at_agent_handoff(
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
        title="Handoff",
        workflow_name="two-agent",
        contexts=[],
        mode="agent",
        owner="marc",
        assignee="codex",
        status="active",
        watchers=[],
    )
    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    seen_steps: list[str] = []

    def fake_spawn(cfg, ref_obj, ticket, agent, mode, **kwargs):  # type: ignore[no-untyped-def]
        updated = Ticket.read(ref_obj.ticket_path)
        seen_steps.append(updated.step or "")
        updated.frontmatter["step"] = "2 (verify)"
        updated.frontmatter["assignee"] = "claude"
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(
        cfg,
        agent_filter="codex",
        probes={"codex": _FakeProbe([_snapshot(agent="codex")])},
    )

    assert seen_steps == ["1 (implement)"]
    assert run.counts["launched"] == 1
    assert run.counts["completed"] == 1
    assert run.results[0].detail == "handed off to claude"
    ticket = Ticket.read(ref["path"])
    assert ticket.status == "in_progress"
    assert ticket.assignee == "claude"


def test_megalaunch_cli_accepts_agent_filter(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    cfg = load_config(repo)
    claude_ref = create_task(
        cfg=cfg,
        title="Claude CLI work",
        workflow_name="code",
        contexts=[],
        mode="agent",
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    codex_ref = create_task(
        cfg=cfg,
        title="Codex CLI work",
        workflow_name="code",
        contexts=[],
        mode="agent",
        owner="marc",
        assignee="codex",
        status="active",
        watchers=[],
    )

    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(
        "coga.usage_probe.build_probes",
        lambda cfg: {"codex": _FakeProbe([_snapshot(agent="codex")])},
    )
    monkeypatch.setattr(
        "coga.commands.megalaunch.notification.post", lambda cfg, msg: None
    )

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(  # type: ignore[no-untyped-def]
        cfg, ref_obj, ticket, agent, mode, **kwargs
    ):
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "done"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    result = CliRunner().invoke(app, ["megalaunch", "--agent", "codex"])

    assert result.exit_code == 0, result.output
    assert "Agent: codex" in result.output
    assert codex_ref["slug"] in result.output
    assert claude_ref["slug"] not in result.output
    assert Ticket.read(codex_ref["path"]).status == "done"
    assert Ticket.read(claude_ref["path"]).status == "active"


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
        mode="agent",
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

    def fake_spawn(cfg, ref_obj, ticket, agent, mode, **kwargs):  # type: ignore[no-untyped-def]
        seen["mode"] = mode
        seen["idle_timeout"] = kwargs.get("idle_timeout")
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "done"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg)

    assert run.counts["completed"] == 1
    assert seen["mode"] == "agent"
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
        mode="agent",
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
        mode="agent",
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


def test_megalaunch_budget_guard_skips_on_low_session_window(repo: Path) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Too expensive",
        workflow_name="code",
        contexts=[],
        mode="agent",
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )

    # 97% of the 5h window used — below the default 5% reserve.
    probes = {"claude": _FakeProbe([_snapshot(session_used=97.0)])}
    run = run_megalaunch(cfg, probes=probes)

    assert run.counts["launched"] == 0
    assert run.counts["skipped-budget"] == 1
    assert "session" in run.results[0].detail


def test_megalaunch_skips_agent_without_probe(repo: Path) -> None:
    """No probe implementation for an agent means skip, never launch blind."""
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Unprobeable",
        workflow_name="code",
        contexts=[],
        mode="agent",
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )

    run = run_megalaunch(cfg, probes={})

    assert run.counts["launched"] == 0
    assert run.counts["skipped-budget"] == 1
    assert "no usage probe" in run.results[0].detail


def test_megalaunch_skips_unreadable_usage_window(repo: Path) -> None:
    """A probe returning no signal (error/timeout/stale) skips conservatively."""
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="No signal",
        workflow_name="code",
        contexts=[],
        mode="agent",
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )

    run = run_megalaunch(cfg, probes={"claude": _FakeProbe([None])})

    assert run.counts["launched"] == 0
    assert run.counts["skipped-budget"] == 1
    assert "unreadable" in run.results[0].detail


def test_megalaunch_ignores_non_active_tickets(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """done/draft/paused tickets are ignored — never launched, never `failed`."""
    cfg = load_config(repo)
    for title, status in (("Done", "done"), ("Draft", "draft"), ("Paused", "paused")):
        ref = create_task(
            cfg=cfg,
            title=title,
            workflow_name="code",
            contexts=[],
            mode="agent",
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


def test_megalaunch_resumes_in_progress_agent_task(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An in_progress agent-assigned ticket is resumed, not re-marked."""
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Resume me",
        workflow_name="code",
        contexts=[],
        mode="agent",
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    ticket = Ticket.read(ref["path"])
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(ref["path"])

    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")

    def fail_mark(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("resume must not re-run the active → in_progress mark")

    monkeypatch.setattr("coga.megalaunch.mark_in_progress", fail_mark)

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(cfg, ref_obj, ticket, agent, mode, **kwargs):  # type: ignore[no-untyped-def]
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "done"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    run = run_megalaunch(cfg)

    assert run.counts["launched"] == 1
    assert run.counts["completed"] == 1
    assert Ticket.read(ref["path"]).status == "done"


def test_megalaunch_in_progress_human_assignee_is_human_gate(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An in_progress ticket parked on a human shows up as skipped-human-gate."""
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="With human",
        workflow_name="code",
        contexts=[],
        mode="agent",
        owner="marc",
        assignee="claude",
        status="active",
        watchers=[],
    )
    ticket = Ticket.read(ref["path"])
    ticket.frontmatter["status"] = "in_progress"
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


def test_megalaunch_reprobes_between_launches(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Budget spent by an earlier launch counts against later tasks in one run.

    Regression: the guard must re-read the agent's usage window between
    launches. With a stale snapshot, the second task's guard sees the
    pre-launch budget and over-launches.
    """
    cfg = load_config(repo)
    for title in ("First", "Second"):
        create_task(
            cfg=cfg,
            title=title,
            workflow_name="code",
            contexts=[],
            mode="agent",
            owner="marc",
            assignee="claude",
            status="active",
            watchers=[],
        )

    monkeypatch.setattr("coga.megalaunch.shutil.which", lambda name: f"/usr/bin/{name}")

    class _Session:
        exit_code = 0
        termination_kind = "natural"

    def fake_spawn(cfg_, ref_obj, ticket, agent, mode, **kwargs):  # type: ignore[no-untyped-def]
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "done"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga.megalaunch.spawn_agent_session", fake_spawn)

    # The first task's candidate check and pre-launch check see budget; the
    # launch exhausts the session window, so the second task's probe reads 97%.
    probes = {
        "claude": _FakeProbe([_snapshot(), _snapshot(), _snapshot(session_used=97.0)])
    }
    run = run_megalaunch(cfg, probes=probes)

    assert run.counts["launched"] == 1
    assert run.counts["completed"] == 1
    assert run.counts["skipped-budget"] == 1


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
            mode="agent",
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

    def fake_spawn(cfg_, ref_obj, ticket, agent, mode, **kwargs):  # type: ignore[no-untyped-def]
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
