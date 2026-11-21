from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
from textwrap import dedent

import pytest


from conftest import append_test_usage, hold_by_agent, hold_by_owner, windows_skip
import typer
from coga.cli import app as cli_app
from coga_edge.megalaunch import megalaunch

# Exercise the policy parser directly; alias subprocess coverage lives in
# test_launch_script and test_cli.
app = typer.Typer()
app.command()(megalaunch)
@app.callback()
def _queue_group() -> None:
    pass

from coga.launch import AgentSessionResult
from coga.compose import compose_prompt
from coga.config import load_config
from coga.create import create_task
from coga_edge.megalaunch import (
    render_run_summary,
    run_megalaunch,
    save_selection,
    trim_megalaunch_blackboard_text,
)
from coga.ticket import Ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip(), encoding="utf-8", newline="\n")


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
        "coga_edge.megalaunch.interactive_stdio_has_tty", lambda: True
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




def _no_spawn(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("megalaunch launched work control had already moved on")

    monkeypatch.setattr("coga_edge.megalaunch.spawn_agent_session", refuse)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")
    monkeypatch.setattr("coga_edge.megalaunch.notification.post", lambda cfg, msg: None)
    monkeypatch.setattr("coga_edge.megalaunch.interactive_stdio_has_tty", lambda: True)




_UNSIGNALLED = "but the supervisor saw no done signal"


def test_megalaunch_unknown_directory_fails_loud(repo: Path) -> None:
    """A directory that doesn't exist under tasks/ raises, never sweeps nothing silently."""
    from coga.tasks import UnknownDirectoryError

    cfg = load_config(repo)

    with pytest.raises(UnknownDirectoryError):
        run_megalaunch(cfg, directory="nope")


def test_megalaunch_requires_tty(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Headless runs fail loud — the interactive REPLs need a real terminal."""
    from coga_edge.megalaunch import MegalaunchError

    monkeypatch.setattr(
        "coga_edge.megalaunch.interactive_stdio_has_tty", lambda: False
    )
    cfg = load_config(repo)

    with pytest.raises(MegalaunchError, match="TTY"):
        run_megalaunch(cfg)


def test_megalaunch_skips_open_blocker(repo: Path) -> None:
    from typer.testing import CliRunner

    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Blocked",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    result = CliRunner().invoke(
        cli_app,
        ["block", "--task", ref["slug"], "--reason", "need owner answer"],
    )
    assert result.exit_code == 0, result.output

    run = run_megalaunch(cfg)

    assert run.counts["launched"] == 0
    assert run.counts["skipped-unresolved-blocker"] == 1
    assert "need owner answer" in run.results[0].detail


@pytest.mark.parametrize("remaining", ["active", "done", "canceled", "human"])
def test_megalaunch_drain_resolves_only_satisfied_blockers(
    repo: Path, monkeypatch: pytest.MonkeyPatch, remaining: str
) -> None:
    """Each dependency gets its own answer; unfinished and human asks survive."""
    from coga.blackboard import append_blocker, open_blockers, read_blockers

    cfg = load_config(repo)
    dependencies = []
    for title, status in (("A dependency", "done"), ("C dependency", remaining)):
        dependency = create_task(
            cfg=cfg,
            title=title,
            workflow_name="code",
            contexts=[],
            owner="lea",
            agent="claude",
            status="active",
        )
        ticket = Ticket.read(dependency["path"])
        ticket.frontmatter["status"] = status if status != "human" else "active"
        if status in {"done", "canceled"}:
            ticket.frontmatter.pop("step", None)
        ticket.write(dependency["path"])
        dependencies.append(dependency)
    blocked = create_task(
        cfg=cfg,
        title="B dependent",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    reasons = [
        f"Depends on {dependencies[0]['slug']}: need its result",
        "Which region should we use?" if remaining == "human"
        else f"Depends on {dependencies[1]['slug']}: need its result",
    ]
    for reason in reasons:
        append_blocker(Path(blocked["path"]), actor="claude", reason=reason)
    ticket = Ticket.read(blocked["path"])
    ticket.frontmatter["status"] = "blocked"
    ticket.write(blocked["path"])
    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(cfg)

    blockers = read_blockers(Path(blocked["path"]))
    assert [blocker.resolved for blocker in blockers] == [True, remaining == "done"]
    assert dependencies[0]["slug"] in (blockers[0].answer or "")
    if remaining == "done":
        assert dependencies[1]["slug"] in (blockers[1].answer or "")
        assert launched == [blocked["slug"]]
        assert Ticket.read(blocked["path"]).status == "done"
        assert run.counts["drained"] == 1
    else:
        assert blockers[1].answer is None
        assert [blocker.reason for blocker in open_blockers(Path(blocked["path"]))] == reasons[1:]
        assert launched == []
        assert Ticket.read(blocked["path"]).status == "blocked"
        assert run.results[0].outcome == "skipped-unresolved-blocker"


def test_megalaunch_drain_keeps_ask_open_when_activation_refuses(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A drained ticket that cannot activate keeps its ask and stays reportable."""
    from coga.blackboard import append_blocker, open_blockers
    from coga_edge.blocker_reminders import scan_blocker_reminders

    cfg = load_config(repo)
    blocked = create_task(
        cfg=cfg,
        title="Blocked first",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    dependency = create_task(
        cfg=cfg,
        title="Dependency",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
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
        agent="claude",
        status="active",
    )
    middle = create_task(
        cfg=cfg,
        title="Middle",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    first = create_task(
        cfg=cfg,
        title="First",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
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
        agent="claude",
        status="active",
    )
    dependency = create_task(
        cfg=cfg,
        title="Budget dependency",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
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
        agent="claude",
        status="active",
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
        agent="claude",
        status="active",
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
        agent="claude",
        status="active",
    )
    dependency = create_task(
        cfg=cfg,
        title="Picked dependency",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
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
        agent="claude",
        status="active",
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
    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")
    launched: list[str] = []

    class _Session:
        exit_code = 0
        termination_kind = "natural"
        done_signalled = False

    def fake_spawn(cfg, ref_obj, ticket, agent, **kwargs):  # type: ignore[no-untyped-def]
        launched.append(ref_obj.id_slug)
        updated = Ticket.read(ref_obj.ticket_path)
        updated.frontmatter["status"] = "done"
        updated.frontmatter.pop("step", None)
        updated.write(ref_obj.ticket_path)
        return _Session()

    monkeypatch.setattr("coga_edge.megalaunch.spawn_agent_session", fake_spawn)
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
        agent="claude",
        status="active",
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
        agent="claude",
        status="active",
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
        agent="claude",
        status="canceled",
    )
    workflowless = create_task(
        cfg=cfg,
        title="Shapeless draft",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="draft",
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
        agent="claude",
        status="active",
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
        agent="claude",
        status="draft",
    )
    paused = create_task(
        cfg=cfg,
        title="Paused pick",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
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
        for line in log_path(cfg).read_text(encoding="utf-8").splitlines()
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
        agent="claude",
        status="draft",
    )
    healthy = create_task(
        cfg=cfg,
        title="Good pick",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="draft",
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
        agent="claude",
        status="draft",
    )
    before = Path(draft["path"]).read_bytes()
    monkeypatch.setattr("coga.launch.shutil.which", lambda name: None)

    run = run_megalaunch(cfg, selection=[draft["slug"]])

    result = next(r for r in run.results if r.slug == draft["slug"])
    assert result.outcome == "failed"
    assert "claude" in result.detail
    assert "Set `cli` in [agents.claude] in coga.toml" in result.detail
    assert "PATH" not in result.detail
    assert Path(draft["path"]).read_bytes() == before
    assert Ticket.read(draft["path"]).status == "draft"
    assert _log_lines_for(cfg, draft["slug"], "activated") == []


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
        agent="claude",
        status="active",
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
        agent="claude",
        status="draft",
    )
    second = create_task(
        cfg=cfg,
        title="Bbb unreached pick",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="draft",
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
        agent="claude",
        status="draft",
    )

    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(cfg, selection=[draft["slug"]])

    assert launched == [draft["slug"]]
    assert run.counts["completed"] == 1
    lines = [
        line
        for line in log_path(cfg).read_text(encoding="utf-8").splitlines()
        if f"[{draft['slug']}]" in line
    ]
    activated = next(i for i, line in enumerate(lines) if "activated" in line)
    started = next(i for i, line in enumerate(lines) if "started" in line)
    assert activated < started


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
        agent="claude",
        status="draft",
    )

    def boom(  # type: ignore[no-untyped-def]
        cfg_, ref, ticket, *, agent_override=None
    ):
        raise AssertionError("authoring must not run without opt-in")

    monkeypatch.setattr("coga_edge.megalaunch._author_draft", boom)
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
        agent="claude",
        status="draft",
    )
    t = Ticket.read(draft["path"])
    t.frontmatter["workflow"] = None
    t.write(draft["path"])

    # The interview runs but the human leaves without adding a workflow.
    monkeypatch.setattr(
        "coga_edge.megalaunch._author_draft",
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
    from coga_edge.megalaunch import _author_draft
    from coga.tasks import resolve_task

    cfg = load_config(repo)
    draft = create_task(
        cfg=cfg,
        title="Lonely draft",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="draft",
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
    from coga_edge.megalaunch import _author_draft
    from coga.tasks import resolve_task

    cfg = load_config(repo)
    draft = create_task(
        cfg=cfg,
        title="Author with Codex",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="draft",
    )
    ref = resolve_task(cfg, draft["slug"])
    captured: dict[str, object] = {}

    # Reusing the draft as the bootstrap ref gives the fallback path a Claude
    # main agent. The explicit Codex override must still win.
    monkeypatch.setattr(
        "coga_edge.megalaunch.resolve_bootstrap", lambda cfg_, name: ref
    )
    monkeypatch.setattr(
        "coga_edge.megalaunch.invoke_ticket_authoring",
        lambda cfg, ref, *, agent_name: captured.update(launch_agent=agent_name) or 0,
    )

    _author_draft(
        cfg,
        ref,
        Ticket.read(draft["path"]),
        agent_override="codex",
    )

    assert captured["launch_agent"] == "codex"
    # `--agent` selects the interviewer only; it never lands on the edited draft.
    assert Ticket.read(draft["path"]).agent == "claude"


def _capture_author_draft(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """Stub the interview and fail on any prompt: the batched pass never asks."""
    captured: dict[str, object] = {}

    def no_prompt(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("megalaunch authoring must never prompt")

    monkeypatch.setattr("typer.prompt", no_prompt)
    monkeypatch.setattr(
        "coga_edge.megalaunch.invoke_ticket_authoring",
        lambda cfg, ref, *, agent_name: captured.update(launch_agent=agent_name) or 0,
    )
    return captured


def test_author_draft_prefers_draft_agent_over_bootstrap(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The picked draft's own `agent:` beats the packaged bootstrap/ticket's
    `agent: claude`."""
    from coga_edge.megalaunch import _author_draft
    from coga.tasks import resolve_task

    cfg = load_config(repo)
    draft = create_task(
        cfg=cfg,
        title="Author as draft agent",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="codex",
        status="draft",
    )
    captured = _capture_author_draft(monkeypatch)

    _author_draft(cfg, resolve_task(cfg, draft["slug"]), Ticket.read(draft["path"]))

    assert captured["launch_agent"] == "codex"


def test_author_draft_honors_authoring_agent_env(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from coga_edge.megalaunch import _author_draft
    from coga.tasks import resolve_task

    cfg = load_config(repo)
    draft = create_task(
        cfg=cfg,
        title="Author during quota outage",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="draft",
    )
    monkeypatch.setenv("COGA_AUTHORING_AGENT", "codex")
    captured = _capture_author_draft(monkeypatch)

    _author_draft(cfg, resolve_task(cfg, draft["slug"]), Ticket.read(draft["path"]))

    assert captured["launch_agent"] == "codex"
    assert Ticket.read(draft["path"]).agent == "claude"


def test_megalaunch_authoring_reports_unknown_agent_and_continues(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A bad authoring agent skips each picked draft's interview loudly —
    naming the task, the source, and the override — leaves the draft bytes
    untouched, and lets the rest of the batch run."""
    cfg = load_config(repo)
    drafts = []
    for title in ("First unready", "Second unready"):
        draft = create_task(
            cfg=cfg,
            title=title,
            workflow_name="code",
            contexts=[],
            owner="marc",
            agent="claude",
            status="draft",
        )
        t = Ticket.read(draft["path"])
        t.frontmatter["workflow"] = None
        t.write(draft["path"])
        drafts.append(draft)
    before = {d["slug"]: Path(d["path"]).read_bytes() for d in drafts}
    monkeypatch.setenv("COGA_AUTHORING_AGENT", "ghost")
    _capture_author_draft(monkeypatch)
    monkeypatch.setattr(
        "coga_edge.megalaunch.invoke_ticket_authoring",
        lambda *args, **kwargs: pytest.fail("no interview may spawn"),
    )
    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(
        cfg, selection=[d["slug"] for d in drafts], author_drafts=True
    )

    assert launched == []
    assert run.counts["skipped-unlaunchable"] == 2
    err = capsys.readouterr().err
    for draft in drafts:
        assert f"{draft['slug']}: skipping guided authoring" in err
        assert Path(draft["path"]).read_bytes() == before[draft["slug"]]
    assert "from COGA_AUTHORING_AGENT" in err
    assert "pass --agent" in err


def test_megalaunch_selection_unknown_slug_fails_loud(repo: Path) -> None:
    from coga_edge.megalaunch import MegalaunchError

    cfg = load_config(repo)

    with pytest.raises(MegalaunchError, match="not found"):
        run_megalaunch(cfg, selection=["no-such-task"])


def test_launchable_candidates_all_owners_offers_any_non_terminal_status(
    repo: Path,
) -> None:
    """With --all-owners the picker offers every explicitly launchable task."""
    from coga_edge.megalaunch import launchable_candidates

    cfg = load_config(repo)
    active = create_task(
        cfg=cfg,
        title="Active one",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    running = create_task(
        cfg=cfg,
        title="Running one",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    ticket = Ticket.read(running["path"])
    ticket.frontmatter["status"] = "in_progress"
    ticket.write(running["path"])
    draft = create_task(
        # draft with a workflow — offered (activates inline)
        cfg=cfg,
        title="Still a draft",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="draft",
    )
    foreign = create_task(  # someone else's — offered (explicit picks launch it)
        cfg=cfg,
        title="Lea's work",
        workflow_name="code",
        contexts=[],
        owner="lea",
        agent="claude",
        status="active",
    )
    paused = create_task(
        cfg=cfg,
        title="Paused one",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    ticket = Ticket.read(paused["path"])
    ticket.frontmatter["status"] = "paused"
    ticket.write(paused["path"])
    # done — never offered
    done = create_task(
        cfg=cfg,
        title="Finished",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    ticket = Ticket.read(done["path"])
    ticket.frontmatter["status"] = "done"
    ticket.frontmatter.pop("step", None)
    ticket.write(done["path"])
    # canceled — never offered
    canceled = create_task(
        cfg=cfg,
        title="Declined",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="canceled",
    )
    # Owner-held — still offered; the picker no longer pre-filters
    # launchability, the run reports the gate. The handoff comes from the
    # workflow step's role, which is the only way a ticket is owner-held now.
    human = create_task(
        cfg=cfg,
        title="Human work",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    ticket = Ticket.read(human["path"])
    assert isinstance(ticket.workflow, dict)
    ticket.workflow["steps"][0]["assignee"] = "owner"
    ticket.write(human["path"])
    # Draft with no workflow — still offered: the prepare phase authors it into
    # shape.
    workflowless = create_task(
        cfg=cfg,
        title="Shapeless draft",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="draft",
    )
    ticket = Ticket.read(workflowless["path"])
    ticket.frontmatter["workflow"] = None
    ticket.write(workflowless["path"])

    offered = {
        ref.id_slug for ref, _ in launchable_candidates(cfg, all_owners=True)
    }

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
    from coga_edge.megalaunch import launchable_candidates

    cfg = load_config(repo)
    with_ask = create_task(
        cfg=cfg,
        title="Blocked with ask",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
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
        agent="claude",
        status="active",
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
    from coga_edge.megalaunch import launchable_candidates
    from coga.paths import log_path

    cfg = load_config(repo)
    for title in ("Stale", "Fresh", "Silent"):
        create_task(
            cfg=cfg,
            title=title,
            workflow_name="code",
            contexts=[],
            owner="marc",
            agent="claude",
            status="active",
        )
    # Rewrite the log: stale was created first but touched earlier than fresh,
    # and silent has no log line at all (and no git fallback in a non-git tmp
    # repo), so drain order would read [stale, fresh, silent] while the status
    # order under test reads newest activity first with silent trailing.
    log_path(cfg).write_text(
        "2026-06-01 10:00 [stale] [human:marc] created\n"
        "2026-06-02 10:00 [fresh] [human:marc] created\n"
        "2026-06-03 10:00 [stale] [human:marc] bumped\n"
        "2026-06-04 10:00 [fresh] [human:marc] bumped\n",
        encoding="utf-8", newline="\n",
    )

    assert [ref.id_slug for ref, _ in launchable_candidates(cfg)] == [
        "fresh",
        "stale",
        "silent",
    ]


def test_save_and_load_selection_roundtrip(repo: Path) -> None:
    from coga_edge.megalaunch import MegalaunchError, load_selection, save_selection

    cfg = load_config(repo)

    with pytest.raises(MegalaunchError, match="No saved selection"):
        load_selection(cfg)

    save_selection(cfg, ["a-task", "dir/another"])

    assert load_selection(cfg) == ["a-task", "dir/another"]
    assert (repo / ".coga" / "megalaunch-selection.json").is_file()


def test_decode_key() -> None:
    from coga_edge.megalaunch import _decode_key

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
    from coga_edge.megalaunch import _picker_window

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

    from coga_edge.megalaunch import _picker_view
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


@windows_skip(
    "POSIX raw-mode PTY and SIGWINCH self-pipe; the Windows resize poll is "
    "covered by test_windows_keys_resize_and_extended_keys"
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

    from coga_edge.megalaunch import _read_key

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
    for source in ("_PosixKeys", "_WindowsKeys"):
        monkeypatch.setattr(
            f"coga_edge.megalaunch.{source}.read", lambda self: next(pending)
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
        agent="claude",
        status="active",
    )
    second = create_task(
        cfg=cfg,
        title="Leave me unchecked",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )

    monkeypatch.setattr(
        "coga_edge.megalaunch.interactive_stdio_has_tty", lambda: True
    )
    monkeypatch.setattr(
        "coga_edge.megalaunch.notification.post", lambda cfg, msg: None
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
    from coga_edge.megalaunch import load_selection

    assert load_selection(cfg) == [first["slug"]]


def test_megalaunch_cli_pick_prompts_before_authoring_drafts(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Picking a draft raises the one-shot batch prompt; 'y' runs authoring,
    'n' skips it — either way the ready draft still launches."""
    from typer.testing import CliRunner

    cfg = load_config(repo)

    monkeypatch.setattr(
        "coga_edge.megalaunch.interactive_stdio_has_tty", lambda: True
    )
    monkeypatch.setattr(
        "coga_edge.megalaunch.notification.post", lambda cfg, msg: None
    )

    for answer, expect_authored in (("y", True), ("n", False)):
        draft = create_task(
            cfg=cfg,
            title=f"Draft answered {answer}",
            workflow_name="code",
            contexts=[],
            owner="marc",
            agent="claude",
            status="draft",
        )
        authored: list[str] = []
        monkeypatch.setattr(
            "coga_edge.megalaunch._author_draft",
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
        agent="claude",
        status="active",
    )
    monkeypatch.setattr(
        "coga_edge.megalaunch.interactive_stdio_has_tty", lambda: True
    )
    monkeypatch.setattr(
        "coga_edge.megalaunch.notification.post", lambda cfg, msg: None
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
        agent="claude",
        status="active",
    )
    second = create_task(
        cfg=cfg,
        title="Bbb picked below",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    monkeypatch.setattr(
        "coga_edge.megalaunch.interactive_stdio_has_tty", lambda: True
    )
    monkeypatch.setattr(
        "coga_edge.megalaunch.notification.post", lambda cfg, msg: None
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
    selection, and the picker restores the handler it installed: SIGWINCH
    for the POSIX self-pipe, SIGINT for the Windows quit flag."""
    import signal

    picker_signal = signal.SIGWINCH if os.name == "posix" else signal.SIGINT

    from typer.testing import CliRunner

    cfg = load_config(repo)
    picked = create_task(
        cfg=cfg,
        title="Survives a resize",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    monkeypatch.setattr(
        "coga_edge.megalaunch.interactive_stdio_has_tty", lambda: True
    )
    monkeypatch.setattr(
        "coga_edge.megalaunch.notification.post", lambda cfg, msg: None
    )
    launched = _done_on_spawn(monkeypatch)
    handler_before = signal.getsignal(picker_signal)

    _feed_keys(monkeypatch, ["space", "resize", "enter"])
    result = CliRunner().invoke(app, ["megalaunch", "--pick"])

    assert result.exit_code == 0, result.output
    assert launched == [picked["slug"]]
    assert signal.getsignal(picker_signal) is handler_before


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
        agent="claude",
        status="active",
    )
    monkeypatch.setattr(
        "coga_edge.megalaunch.interactive_stdio_has_tty", lambda: True
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
        agent="claude",
        status="active",
        directory="marketing",
    )
    outside = create_task(
        cfg=cfg,
        title="Out of scope",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    monkeypatch.setattr(
        "coga_edge.megalaunch.interactive_stdio_has_tty", lambda: True
    )
    monkeypatch.setattr(
        "coga_edge.megalaunch.notification.post", lambda cfg, msg: None
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

    from coga_edge.megalaunch import save_selection

    cfg = load_config(repo)
    saved = create_task(
        cfg=cfg,
        title="Saved pick",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    other = create_task(
        cfg=cfg,
        title="Never picked",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    save_selection(cfg, [saved["slug"], "since-deleted-task"])
    monkeypatch.setattr(
        "coga_edge.megalaunch.notification.post", lambda cfg, msg: None
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

    for argv, needle in (
        (["--owner", "zach", "--all-owners"], "cannot be combined"),
        (["--pick", "--owner", "zach", "--all-owners"], "cannot be combined"),
        (["--relaunch", "--owner", "zach"], "--relaunch replays"),
        (["--relaunch", "--all-owners"], "--relaunch replays"),
    ):
        refused = CliRunner().invoke(app, ["megalaunch", *argv])
        assert refused.exit_code == 2, argv
        assert needle in refused.output, argv


# --- owner filter (--owner / --all-owners) ----------------------------------


def _owner_tickets(cfg, *, ownerless: bool = False) -> dict[str, dict]:  # type: ignore[no-untyped-def]
    """One active ticket for marc (the operator) and one for zach, plus an
    owner-less one on request (listable, but it fails validation at launch)."""
    created = {
        owner: create_task(
            cfg=cfg,
            title=f"Work of {owner}",
            workflow_name="code",
            contexts=[],
            owner=owner,
            agent="claude",
            status="active",
        )
        for owner in ("marc", "zach", *(("nobody-yet",) if ownerless else ()))
    }
    if ownerless:
        ticket = Ticket.read(created["nobody-yet"]["path"])
        ticket.frontmatter.pop("owner", None)
        ticket.write(created["nobody-yet"]["path"])
    return created


def test_launchable_candidates_filters_by_ticket_owner(repo: Path) -> None:
    """The picker defaults to the operator's tickets; --owner retargets it,
    --all-owners lists everyone's (owner-less included)."""
    from coga_edge.megalaunch import MegalaunchError, launchable_candidates

    cfg = load_config(repo)
    created = _owner_tickets(cfg, ownerless=True)

    def offered(**kwargs) -> set[str]:  # type: ignore[no-untyped-def]
        return {ref.id_slug for ref, _ in launchable_candidates(cfg, **kwargs)}

    assert offered() == {created["marc"]["slug"]}
    assert offered(owner="zach") == {created["zach"]["slug"]}
    assert offered(all_owners=True) == {
        ticket["slug"] for ticket in created.values()
    }
    # Owners are free strings: an unknown one is an empty list, not an error.
    assert offered(owner="unknown-person") == set()
    with pytest.raises(MegalaunchError, match="cannot be combined"):
        launchable_candidates(cfg, owner="zach", all_owners=True)


def test_megalaunch_owner_sweeps_that_owners_tickets(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--owner zach` sweeps zach's work through the same gates; the default
    sweep is unchanged and `--all-owners` covers every owner."""
    cfg = load_config(repo)
    created = _owner_tickets(cfg)
    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(cfg, owner="zach")

    assert launched == [created["zach"]["slug"]]
    assert [result.slug for result in run.results] == [created["zach"]["slug"]]
    assert run.owner_scope == "zach"
    assert "Owner: zach" in render_run_summary(run)
    assert Ticket.read(created["marc"]["path"]).status == "active"

    launched.clear()
    run = run_megalaunch(cfg)
    assert launched == [created["marc"]["slug"]]
    assert run.owner_scope is None
    assert "Owner:" not in render_run_summary(run)

    fresh = {
        owner: create_task(
            cfg=cfg,
            title=f"More work of {owner}",
            workflow_name="code",
            contexts=[],
            owner=owner,
            agent="claude",
            status="active",
        )
        for owner in ("marc", "zach")
    }
    launched.clear()
    run = run_megalaunch(cfg, all_owners=True)
    assert set(launched) == {fresh["marc"]["slug"], fresh["zach"]["slug"]}
    assert run.owner_scope == "every owner"


def test_megalaunch_owner_sweep_unknown_owner_is_empty(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    cfg = load_config(repo)
    created = _owner_tickets(cfg)
    launched = _done_on_spawn(monkeypatch)
    monkeypatch.setattr(
        "coga_edge.megalaunch.notification.post", lambda cfg, msg: None
    )

    result = CliRunner().invoke(app, ["megalaunch", "--owner", "unknown-person"])

    assert result.exit_code == 0, result.output
    assert launched == []
    assert "No launchable tasks owned by unknown-person." in result.output
    assert Ticket.read(created["marc"]["path"]).status == "active"


def test_megalaunch_owner_sweep_drains_that_owners_blockers(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The dependency drain follows the chosen owner, not the operator."""
    from coga.blackboard import append_blocker, read_blockers

    cfg = load_config(repo)
    tickets = {}
    for owner, title in (("zach", "Zach blocked"), ("marc", "Marc blocked")):
        tickets[owner] = create_task(
            cfg=cfg,
            title=title,
            workflow_name="code",
            contexts=[],
            owner=owner,
            agent="claude",
            status="active",
        )
    dependency = create_task(
        cfg=cfg,
        title="Zach dependency",
        workflow_name="code",
        contexts=[],
        owner="zach",
        agent="claude",
        status="active",
    )
    for blocked in tickets.values():
        append_blocker(
            Path(blocked["path"]),
            actor="claude",
            reason=f"Waiting for {dependency['slug']} to land",
        )
        ticket = Ticket.read(blocked["path"])
        ticket.frontmatter["status"] = "blocked"
        ticket.write(blocked["path"])
    launched = _done_on_spawn(monkeypatch)

    run = run_megalaunch(cfg, owner="zach")

    assert launched == [dependency["slug"], tickets["zach"]["slug"]]
    assert run.counts["drained"] == 1
    assert read_blockers(Path(tickets["zach"]["path"]))[0].resolved is True
    # Marc's blocker names the same finished dependency but is outside the
    # filter, so it stays open and blocked.
    assert read_blockers(Path(tickets["marc"]["path"]))[0].resolved is False
    assert Ticket.read(tickets["marc"]["path"]).status == "blocked"


def test_megalaunch_owner_flags_refused_with_explicit_selection(repo: Path) -> None:
    from coga_edge.megalaunch import MegalaunchError

    cfg = load_config(repo)
    with pytest.raises(MegalaunchError, match="explicit selection"):
        run_megalaunch(cfg, selection=["anything"], owner="zach")
    with pytest.raises(MegalaunchError, match="explicit selection"):
        run_megalaunch(cfg, selection=["anything"], all_owners=True)


@pytest.mark.parametrize(
    ("flags", "expected_owners"),
    [
        ([], {"marc"}),
        (["--owner", "zach"], {"zach"}),
        (["--all-owners"], {"marc", "zach"}),
    ],
)
def test_megalaunch_cli_picker_offers_owner_filtered_list(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    flags: list[str],
    expected_owners: set[str],
) -> None:
    """`--pick` lists my tickets; `--owner`/`--all-owners` reshape the list,
    and the confirmed pick then runs as checked."""
    from typer.testing import CliRunner

    cfg = load_config(repo)
    created = _owner_tickets(cfg)
    monkeypatch.setattr(
        "coga_edge.megalaunch.interactive_stdio_has_tty", lambda: True
    )
    monkeypatch.setattr(
        "coga_edge.megalaunch.notification.post", lambda cfg, msg: None
    )
    offered: list[str] = []

    def pick_everything(candidates):  # type: ignore[no-untyped-def]
        offered.extend(ref.id_slug for ref, _ in candidates)
        return list(offered)

    monkeypatch.setattr("coga_edge.megalaunch._pick_selection", pick_everything)
    launched = _done_on_spawn(monkeypatch)

    result = CliRunner().invoke(app, ["megalaunch", "--pick", *flags])

    assert result.exit_code == 0, result.output
    expected = {created[owner]["slug"] for owner in expected_owners}
    assert set(offered) == expected
    assert set(launched) == expected


def test_megalaunch_cli_picker_requires_tty(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--pick without a terminal fails loud instead of hanging on the prompt."""
    from typer.testing import CliRunner

    monkeypatch.setattr("coga_edge.megalaunch.interactive_stdio_has_tty", lambda: False)
    result = CliRunner().invoke(app, ["megalaunch", "--pick"])

    assert result.exit_code == 2
    assert "TTY" in result.output


# --- the Windows picker key source --------------------------------------------


class _FakeMsvcrt:
    """`kbhit`/`getwch` over a queue; ``on_read`` runs before each `getwch`."""

    def __init__(self, chars: list[str], on_read=None) -> None:
        self.chars = list(chars)
        self.on_read = on_read

    def kbhit(self) -> bool:
        return bool(self.chars)

    def getwch(self) -> str:
        if self.on_read is not None:
            self.on_read(self)
        return self.chars.pop(0)


def _windows_picker(monkeypatch: pytest.MonkeyPatch, msvcrt, sleep=None):
    """Select the Windows key source with fake console input and modes."""
    import sys
    import types

    import coga_edge.megalaunch as command

    modes: list[str] = []

    class Modes:
        @classmethod
        def save(cls):
            modes.append("saved")
            return cls()

        def restore(self) -> None:
            modes.append("restored")

    monkeypatch.setitem(sys.modules, "msvcrt", msvcrt)
    monkeypatch.setattr(command, "_windows_console", lambda: True)
    monkeypatch.setattr("coga.repl_supervisor_nt.ConsoleModes", Modes)
    monkeypatch.setattr(
        command, "time", types.SimpleNamespace(sleep=sleep or (lambda _s: None))
    )
    return modes


def test_windows_keys_resize_and_extended_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    import coga_edge.megalaunch as command

    msvcrt = _FakeMsvcrt(["\xe0", "H", "\xe0", "P", "\x00", "P", " ", "j", "k",
                          "a", "n", "\r", "\x1b", "q", "\x03", "\xe0", "M"])
    _windows_picker(monkeypatch, msvcrt)
    sizes = iter([(80, 24), (80, 24), (100, 30)])
    # shutil is shared with pytest, which queries terminal size while reporting.
    with monkeypatch.context() as terminal:
        terminal.setattr(command.shutil, "get_terminal_size", lambda: next(sizes))
        with command._WindowsKeys() as keys:
            actions = [keys.read() for _ in range(13)]
            assert actions == ["up", "down", "down", "space", "down", "up", "all",
                               "none", "enter", "quit", "quit", "quit", ""]
            # Idle polling notices a resize without SIGWINCH.
            assert keys.read() == "resize"


def _picker_candidates(repo: Path) -> list:
    from coga.tasks import list_tasks

    cfg = load_config(repo)
    for title in ("First", "Second"):
        create_task(cfg=cfg, title=title, workflow_name="code", contexts=[],
                    owner="marc", agent="claude", status="active")
    return [(ref, Ticket.read(ref.ticket_path)) for ref in list_tasks(cfg)]


@pytest.mark.parametrize(
    ("chars", "expected"),
    [([" ", "\r"], 1), (["q"], 0), (["\x03"], 0), (["\x1b"], 0)],
)
def test_windows_picker_restores_handler_and_modes(
    repo: Path, monkeypatch: pytest.MonkeyPatch, chars: list[str], expected: int
) -> None:
    import signal

    from coga_edge.megalaunch import _pick_selection

    modes = _windows_picker(monkeypatch, _FakeMsvcrt(chars))
    previous = signal.getsignal(signal.SIGINT)
    assert len(_pick_selection(_picker_candidates(repo))) == expected
    assert signal.getsignal(signal.SIGINT) is previous
    assert modes == ["saved", "restored"]


def test_windows_picker_restores_after_a_render_failure(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import signal

    import coga_edge.megalaunch as command

    modes = _windows_picker(monkeypatch, _FakeMsvcrt([]))
    previous = signal.getsignal(signal.SIGINT)

    def broken(*args, **kwargs):
        raise RuntimeError("render failed")

    monkeypatch.setattr(command, "_picker_view", broken)
    with pytest.raises(RuntimeError, match="render failed"):
        command._pick_selection(_picker_candidates(repo))
    assert signal.getsignal(signal.SIGINT) is previous
    assert modes == ["saved", "restored"]


def _interrupt_once():
    import signal

    fired: list[bool] = []

    def fire(*_args) -> None:
        if not fired:
            fired.append(True)
            signal.raise_signal(signal.SIGINT)

    return fire


@pytest.mark.parametrize("moment", ["idle-poll", "redraw", "before-enter"])
def test_windows_ctrl_c_signal_quits_the_picker_without_launching(
    repo: Path, monkeypatch: pytest.MonkeyPatch, moment: str
) -> None:
    """A processed Ctrl+C is a SIGINT, not a key: it cancels at any moment."""
    from typer.testing import CliRunner

    import coga_edge.megalaunch as command
    from coga_edge.megalaunch import MegalaunchError, load_selection

    candidates = _picker_candidates(repo)
    fire = _interrupt_once()
    if moment == "idle-poll":
        msvcrt = _FakeMsvcrt([])
        _windows_picker(monkeypatch, msvcrt, sleep=fire)
    elif moment == "redraw":
        _windows_picker(monkeypatch, _FakeMsvcrt([" ", "j", "\r"]))
        real_view = command._picker_view
        calls: list[int] = []

        def view(*args, **kwargs):
            calls.append(1)
            if len(calls) == 2:  # the redraw after the first key
                fire()
            return real_view(*args, **kwargs)

        monkeypatch.setattr(command, "_picker_view", view)
    else:
        # Enter is already queued when the signal lands: cancellation wins.
        _windows_picker(monkeypatch, _FakeMsvcrt([" ", "\r"], on_read=lambda m: (
            fire() if m.chars == ["\r"] else None
        )))
    monkeypatch.setattr(command, "interactive_stdio_has_tty", lambda: True)
    launched = _done_on_spawn(monkeypatch)

    result = CliRunner().invoke(app, ["megalaunch", "--pick"])

    assert result.exit_code == 0, result.output
    assert "Traceback" not in result.output
    assert "Nothing selected" in result.output
    assert launched == []
    with pytest.raises(MegalaunchError):
        load_selection(load_config(repo))
    assert all(Ticket.read(ref.ticket_path).status == "active" for ref, _ in candidates)


def test_queue_reblock_rereads_current_ticket_instead_of_passed_view(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from coga.blackboard import append_blocker
    from coga.tasks import resolve_task
    from coga_edge.megalaunch import _reblock_unresolved

    cfg = load_config(repo)
    created = create_task(cfg=cfg, title="Reblock current ask", workflow_name="code", contexts=[], owner="marc", agent="claude", status="active")
    ref = resolve_task(cfg, created["slug"])
    stale = Ticket.read(ref.ticket_path)
    current = Ticket.read(ref.ticket_path)
    current.frontmatter["status"] = "in_progress"
    current.write(ref.ticket_path)
    append_blocker(ref.ticket_path, "marc", "New current ask")
    result = _reblock_unresolved(cfg, ref, stale)
    assert result.outcome == "blocked" and "New current ask" in result.detail
    assert Ticket.read(ref.ticket_path).status == "blocked"
    assert _reblock_unresolved(cfg, ref, stale) is None


@pytest.mark.parametrize("code", [0, 2, 75])
def test_queue_authoring_propagates_retained_state_only(repo: Path, monkeypatch: pytest.MonkeyPatch, code: int) -> None:
    from coga.tasks import resolve_task
    from coga_edge.megalaunch import _author_draft

    cfg = load_config(repo)
    created = create_task(cfg=cfg, title="Authoring stop policy", workflow_name="code", contexts=[], owner="marc", agent="claude", status="draft")
    ref = resolve_task(cfg, created["slug"])
    before = ref.ticket_path.read_bytes()
    monkeypatch.setattr("coga_edge.megalaunch.invoke_ticket_authoring", lambda *a, **kw: code)
    if code == 75:
        with pytest.raises(SystemExit) as result:
            _author_draft(cfg, ref, Ticket.read(ref.ticket_path))
        assert result.value.code == 75
    else:
        _author_draft(cfg, ref, Ticket.read(ref.ticket_path))
    assert ref.ticket_path.read_bytes() == before


# --- an agent that fails to start stops the run ------------------------------


def _agent_exec_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> list[str]:
    """Model a PTY exec failure while exercising launch admission and audit.
    """
    from coga.repl_supervisor import ReplOutcome

    monkeypatch.setattr("coga.launch.shutil.which", lambda name, **kwargs: f"/usr/bin/{name}")
    spawned: list[str] = []

    def child(cmd, env, *, session_id=None, after_spawn=None, spawn_release_guard=None,  # type: ignore[no-untyped-def]
              after_spawn_release=None, **kwargs):
        if spawn_release_guard is not None:
            with spawn_release_guard():
                after_spawn()
                if after_spawn_release is not None:
                    after_spawn_release()
        elif after_spawn is not None:
            after_spawn()
        spawned.append(session_id)
        return ReplOutcome(127, "natural", exec_failed=True)

    monkeypatch.setattr("coga.launch.run_with_done_marker", child)
    return spawned


def _two_tasks(repo: Path, status: str) -> tuple[dict, dict]:
    cfg = load_config(repo)
    return tuple(  # type: ignore[return-value]
        create_task(
            cfg=cfg, title=title, workflow_name="code", contexts=[],
            owner="marc", agent="claude", status=status,
        )
        for title in ("First broken", "Second untouched")
    )


def test_megalaunch_pick_restores_draft_and_activates_no_later_pick(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from coga.blackboard import open_blockers

    cfg = load_config(repo)
    first, second = _two_tasks(repo, "draft")
    before = {task["slug"]: Path(task["path"]).read_bytes() for task in (first, second)}
    spawned = _agent_exec_fails(monkeypatch)

    run = run_megalaunch(cfg, selection=[first["slug"], second["slug"]])

    assert spawned == [first["slug"]]
    assert [result.slug for result in run.results] == [first["slug"]]
    row = run.results[0]
    assert row.outcome == "failed" and row.stops_run and row.launched
    assert "exited with code 127" in row.detail and "restored to draft" in row.detail
    # Exactly as picked: draft again, no frozen workflow, no claim, no ask.
    assert Path(first["path"]).read_bytes() == before[first["slug"]]
    assert Path(second["path"]).read_bytes() == before[second["slug"]]
    assert open_blockers(Path(first["path"])) == []


@windows_skip("Uses a real POSIX PTY and a script with a missing interpreter.")
@pytest.mark.parametrize("exit_code", [None, 1, 127])
def test_megalaunch_posix_pty_distinguishes_exec_failure_from_agent_exit(
    repo: Path, monkeypatch: pytest.MonkeyPatch, exit_code: int | None,
) -> None:
    import os
    import shlex
    import sys

    cfg = load_config(repo)
    first, second = _two_tasks(repo, "draft")
    before = [Path(task["path"]).read_bytes() for task in (first, second)]
    artifact = repo / "work.txt"
    agent = repo / "claude"
    if exit_code is None:
        _write(agent, "#!/coga-test-missing-interpreter\n")
    else:
        _write(
            agent,
            f"#!/bin/sh\nprintf worked >> {shlex.quote(str(artifact))}\nexit {exit_code}\n",
        )
    agent.chmod(0o755)
    monkeypatch.setenv("PATH", str(repo))

    # Give the real supervisor terminal descriptors without forwarding input
    # from pytest or relying on the runner's console.
    master, slave = os.openpty()
    try:
        with (
            os.fdopen(os.dup(slave), "w", buffering=1) as terminal,
            monkeypatch.context() as patch,
        ):
            patch.setattr(sys, "stdin", terminal)
            patch.setattr(sys, "stdout", terminal)
            run = run_megalaunch(cfg, selection=[first["slug"], second["slug"]])
    finally:
        os.close(slave)
        os.close(master)

    if exit_code is None:
        assert [row.slug for row in run.results] == [first["slug"]]
        assert run.results[0].stops_run
        assert "exited with code 127" in run.results[0].detail
        assert [Path(task["path"]).read_bytes() for task in (first, second)] == before
        assert not artifact.exists()
    else:
        assert artifact.read_text() == "workedworked"
        assert [row.slug for row in run.results] == [first["slug"], second["slug"]]
        assert all(not row.stops_run for row in run.results)
        assert [row.detail for row in run.results] == [f"agent exited with code {exit_code}"] * 2
        assert all(Ticket.read(task["path"]).status == "in_progress" for task in (first, second))
