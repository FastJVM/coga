"""Tests for `coga mark <state>`."""

from __future__ import annotations

import threading
from dataclasses import replace
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from coga import git as git_module
from coga.blackboard import append_blocker, open_blockers
from conftest import derived_operator, hold_by_agent, hold_by_owner
from coga.cli import app
from coga.config import load_config
from coga.create import create_task
from coga.mark import (
    CancellationError,
    mark_active,
    mark_canceled,
    mark_in_progress,
    mark_paused,
)
from coga.taskfile import read_blackboard, replace_blackboard
from coga.tasks import read_ticket, resolve_task
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
        [notification.slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
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
          - name: pr
            assignee: agent
          - name: merge
            assignee: agent
        ---

        ## implement
        Write the code.

        ## pr
        Open the pull request.

        ## merge
        Merge the change.
        """,
    )
    monkeypatch.chdir(company)
    return company


def _make_task(repo: Path, *, workflow: str | None = "code", status: str = "draft") -> tuple[str, Path]:
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Work",
        workflow_name=workflow,
        contexts=[],
        owner="marc",
        agent="claude",
        status=status,
    )
    return ref["slug"], ref["path"]


def _read_log(repo: Path) -> str:
    """The repo-global audit log (`coga/log.md`)."""
    return (repo / "log.md").read_text()


# --- mark active --------------------------------------------------------------


def test_mark_active_from_draft(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="draft")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path)
    assert t.status == "active"
    log = _read_log(repo)
    assert "activated (draft → active)" in log


def test_mark_active_from_paused(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="paused")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path)
    assert t.status == "active"
    log = _read_log(repo)
    assert "activated (paused → active)" in log


def test_mark_active_refuses_authoring_blackboard_before_mutating(
    repo: Path,
) -> None:
    slug, task_path = _make_task(repo, status="draft")
    t = Ticket.read(task_path)
    t.frontmatter["workflow"] = "code"
    t.write(task_path)
    before_blackboard = "\n" + dedent(
        """\
        The blackboard is a notepad to be written to often as the human and
        agent works through a task.

        ---

        ## Evaluator review

        stale scratch

        ---

        ## Proposals

        maybe do this

        ---

        ## Dev

        branch: work
        """
    )
    replace_blackboard(task_path, before_blackboard)

    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])

    assert result.exit_code == 2
    combined = result.output + (result.stderr or "")
    assert "pre-launch notes" in combined
    assert (
        "Merge the important parts into `## Description` / `## Context`"
        in combined
    )
    assert "`## Production notes`" in combined
    after = Ticket.read(task_path)
    assert after.status == "draft"
    assert after.workflow == "code"
    assert read_blackboard(task_path) == before_blackboard
    assert "activated (draft" not in _read_log(repo)


@pytest.mark.parametrize("heading", ["Production notes", "Superseded designs"])
def test_mark_active_preserves_intentional_blackboard(repo: Path, heading: str) -> None:
    slug, task_path = _make_task(repo, status="draft")
    before = f"\n## {heading}\n\n" + "Retained context. " * 60 + "\n"
    replace_blackboard(task_path, before)

    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])

    assert result.exit_code == 0, result.output
    assert Ticket.read(task_path).status == "active"
    assert read_blackboard(task_path) == before


def test_mark_active_from_paused_does_not_recheck_blackboard(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="paused")
    before = "\n## Evaluator review\n\nAlready launched work notes.\n"
    replace_blackboard(task_path, before)

    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])

    assert result.exit_code == 0, result.output
    assert Ticket.read(task_path).status == "active"
    assert read_blackboard(task_path) == before


def test_mark_active_already_active_errors(repo: Path) -> None:
    slug, _ = _make_task(repo, status="active")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 2
    assert "already 'active'" in result.output


def test_mark_active_from_done_errors(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="active")
    # Hand-set to done.
    t = Ticket.read(task_path)
    t.frontmatter["status"] = "done"
    t.write(task_path)
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 2
    assert "'done'" in result.output


def test_mark_active_refuses_workflow_less_ticket(repo: Path) -> None:
    """A draft with no workflow can't be activated — it would have no steps
    and could never be advanced by `coga bump`."""
    slug, task_path = _make_task(repo, workflow=None, status="draft")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 2
    assert "no workflow" in result.output
    t = Ticket.read(task_path)
    assert t.status == "draft"


def test_mark_active_freezes_string_workflow(repo: Path) -> None:
    """A draft carrying `workflow:` as a bare string ref is frozen into its
    snapshot on activation, and seeded at step 1."""
    slug, task_path = _make_task(repo, workflow=None, status="draft")
    # Hand-author a bare-string workflow ref, as guided authoring would.
    t = Ticket.read(task_path)
    t.frontmatter["workflow"] = "code"
    t.write(task_path)

    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 0, result.output

    t = Ticket.read(task_path)
    assert t.status == "active"
    assert isinstance(t.workflow, dict)
    assert t.workflow["name"] == "code"
    assert t.step == "1 (implement)"


def test_mark_active_resolves_step_one_assignee(repo: Path) -> None:
    """Activation resolves step 1's `assignee:` role token the way creation
    does, so a hand-authored draft lands on an agent-owned step wearing the
    agent rather than the human `assignee:` it was created with."""
    _write(
        repo / "workflows" / "review.md",
        """
        ---
        name: review
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
    slug, task_path = _make_task(repo, workflow=None, status="draft")
    t = Ticket.read(task_path)
    t.frontmatter["workflow"] = "review"
    t.frontmatter.pop("agent", None)
    t.write(task_path)

    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 0, result.output

    t = Ticket.read(task_path)
    assert t.step == "1 (implement)"
    # Activation freezes the snapshot, seeds step 1, and selects the configured
    # default main agent — and writes no assignment, because step 1's `agent`
    # role is what routes it.
    assert t.agent == "claude"
    assert "assignee" not in t.frontmatter
    assert derived_operator(repo, slug) == "claude"


def test_mark_active_refuses_an_unresolvable_step_one_role(repo: Path) -> None:
    """A step-1 role token that can't resolve fails loud at activation rather
    than deferring a contradictory refusal to launch."""
    _write(
        repo / "workflows" / "peer.md",
        """
        ---
        name: peer
        steps:
          - name: implement
            assignee: other-agent
        ---

        ## implement
        Write the code.
        """,
    )
    slug, task_path = _make_task(repo, workflow=None, status="draft")
    t = Ticket.read(task_path)
    t.frontmatter["workflow"] = "peer"
    t.write(task_path)

    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 2
    assert "assignee='other-agent'" in result.output

    t = Ticket.read(task_path)
    assert t.status == "draft"
    assert t.workflow == "peer"
    assert t.step is None


def test_mark_active_leaves_an_existing_frozen_step_alone(repo: Path) -> None:
    """Nothing re-freezes a ticket that already carries a step.

    Its position and its frozen roles are left exactly as they stand, so the
    derived operator is unchanged by the status flip.
    """
    _write(
        repo / "workflows" / "review.md",
        """
        ---
        name: review
        steps:
          - name: implement
            assignee: agent
        ---

        ## implement
        Write the code.
        """,
    )
    slug, task_path = _make_task(repo, status="paused")
    t = Ticket.read(task_path)
    t.frontmatter["workflow"] = {
        "name": "review",
        "steps": [{"name": "implement", "skills": [], "assignee": "agent"}],
    }
    t.frontmatter["step"] = "1 (implement)"
    hold_by_owner(t)
    t.write(task_path)

    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 0, result.output

    t = Ticket.read(task_path)
    assert t.status == "active"
    assert t.step == "1 (implement)"
    assert t.current_step()["assignee"] == "owner"
    assert derived_operator(repo, slug) == "marc"


def test_mark_active_refuses_unknown_string_workflow(repo: Path) -> None:
    """A bare-string `workflow:` ref that names no known workflow is refused
    at activation, when the freeze fails."""
    slug, task_path = _make_task(repo, workflow=None, status="draft")
    t = Ticket.read(task_path)
    t.frontmatter["workflow"] = "no-such-workflow"
    t.write(task_path)

    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 2
    assert "could not" in result.output
    t = Ticket.read(task_path)
    assert t.status == "draft"


def test_mark_active_blocks_on_required_extension_empty(repo: Path) -> None:
    """`mark active` refuses a draft whose `required = true` extension fields
    are empty."""
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text()
        + (
            "\n[ticket.fields.docket]\n"
            'description = "USPTO docket"\n'
            "required = true\n"
        )
    )
    slug, task_path = _make_task(repo, status="draft")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 2
    assert "required extension field" in result.output
    assert "docket" in result.output
    t = Ticket.read(task_path)
    assert t.status == "draft"


def test_mark_active_allows_filled_required_extension(repo: Path) -> None:
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text()
        + (
            "\n[ticket.fields.docket]\n"
            'description = "USPTO docket"\n'
            "required = true\n"
        )
    )
    slug, task_path = _make_task(repo, status="draft")
    t = Ticket.read(task_path)
    t.frontmatter["docket"] = "55-12345"
    t.write(task_path)

    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path)
    assert t.status == "active"
    assert t.frontmatter["docket"] == "55-12345"


def test_mark_active_ignores_required_when_not_required(repo: Path) -> None:
    """Empty non-required extension fields don't block activation."""
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text()
        + '\n[ticket.fields.docket]\ndescription = "x"\n'
    )
    slug, _ = _make_task(repo, status="draft")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 0, result.output


# --- mark paused --------------------------------------------------------------


def test_mark_paused_from_active(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="active")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "paused", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path)
    assert t.status == "paused"
    log = _read_log(repo)
    assert "paused (active → paused)" in log


def test_mark_paused_preserves_step(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="in_progress")
    # Advance to step 2.
    runner = CliRunner()
    runner.invoke(app, ["bump", slug])
    t = Ticket.read(task_path)
    assert t.step == "2 (pr)"
    # Pausing preserves the step.
    result = runner.invoke(app, ["mark", "paused", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path)
    assert t.status == "paused"
    assert t.step == "2 (pr)"


def test_lifecycle_write_waits_until_child_release_even_without_git(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A final spawn proof cannot race a local-only lifecycle mutation."""
    slug, task_path = _make_task(repo, status="in_progress")
    cfg = replace(load_config(repo), git_enabled=False)
    ref = resolve_task(cfg, slug)
    ticket = read_ticket(ref)
    original = task_path.read_bytes()
    attempted = threading.Event()
    gate_written = threading.Event()
    write_finished = threading.Event()
    errors: list[BaseException] = []
    real_write = git_module.write_ticket_under_barrier

    def observed_write(  # type: ignore[no-untyped-def]
        cfg_, ticket_, path_, *, mutation_snapshot=None
    ):
        attempted.set()
        real_write(
            cfg_,
            ticket_,
            path_,
            mutation_snapshot=mutation_snapshot,
        )
        assert gate_written.is_set()
        write_finished.set()

    monkeypatch.setattr(git_module, "write_ticket_under_barrier", observed_write)

    def pause_ticket() -> None:
        try:
            mark_paused(
                cfg,
                ref,
                ticket,
                actor="human:marc",
                log_message="paused during held-child admission",
            )
        except BaseException as exc:
            errors.append(exc)

    worker = threading.Thread(target=pause_ticket)
    with git_module.state_publication_barrier(cfg):
        worker.start()
        assert attempted.wait(timeout=5)
        assert not write_finished.wait(timeout=0.1)
        assert task_path.read_bytes() == original
        # Models the supervisor's gate-byte write while it still owns the
        # shared admission/publication barrier.
        gate_written.set()

    worker.join(timeout=5)
    assert not worker.is_alive()
    assert errors == []
    assert Ticket.read(task_path).status == "paused"


def test_strict_lifecycle_compare_and_write_share_publication_barrier(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A peer write cannot land between a strict byte check and replacement."""
    _, task_path = _make_task(repo, status="active")
    cfg = replace(load_config(repo), git_enabled=False)
    snapshot = git_module.FileMutationRollback.capture((task_path,))
    stale = Ticket.read(task_path)
    stale.frontmatter["status"] = "paused"
    peer = Ticket.read(task_path)
    peer.frontmatter["status"] = "done"
    checked = threading.Event()
    peer_attempted = threading.Event()
    peer_finished = threading.Event()
    errors: list[BaseException] = []
    real_require_unchanged = snapshot.require_unchanged

    def pause_after_compare(path: Path) -> None:
        real_require_unchanged(path)
        checked.set()
        assert peer_attempted.wait(timeout=5)
        assert not peer_finished.wait(timeout=0.1)

    monkeypatch.setattr(snapshot, "require_unchanged", pause_after_compare)

    def write_stale_state() -> None:
        try:
            git_module.write_ticket_under_barrier(
                cfg,
                stale,
                task_path,
                mutation_snapshot=snapshot,
            )
        except BaseException as exc:
            errors.append(exc)

    def write_peer_state() -> None:
        try:
            peer_attempted.set()
            git_module.write_ticket_under_barrier(cfg, peer, task_path)
        except BaseException as exc:
            errors.append(exc)
        finally:
            peer_finished.set()

    stale_worker = threading.Thread(target=write_stale_state)
    stale_worker.start()
    assert checked.wait(timeout=5)
    peer_worker = threading.Thread(target=write_peer_state)
    peer_worker.start()
    stale_worker.join(timeout=5)
    peer_worker.join(timeout=5)

    assert not stale_worker.is_alive()
    assert not peer_worker.is_alive()
    assert errors == []
    assert snapshot.generated == {task_path: stale.render().encode("utf-8")}
    assert Ticket.read(task_path).status == "done"


def test_strict_lifecycle_compare_and_restore_share_publication_barrier(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed stale transition cannot restore over a peer lifecycle write."""
    _, task_path = _make_task(repo, status="active")
    cfg = replace(load_config(repo), git_enabled=False)
    snapshot = git_module.FileMutationRollback.capture((task_path,))
    generated = Ticket.read(task_path)
    generated.frontmatter["status"] = "paused"
    generated.write(task_path)
    snapshot.arm({task_path: generated.render().encode("utf-8")})
    peer = Ticket.read(task_path)
    peer.frontmatter["status"] = "done"
    restore_reached = threading.Event()
    peer_attempted = threading.Event()
    peer_finished = threading.Event()
    errors: list[BaseException] = []
    real_restore_file_bytes = git_module._restore_file_bytes

    def pause_before_restore(path: Path, data: bytes | None) -> None:
        restore_reached.set()
        assert peer_attempted.wait(timeout=5)
        assert not peer_finished.wait(timeout=0.1)
        real_restore_file_bytes(path, data)

    monkeypatch.setattr(git_module, "_restore_file_bytes", pause_before_restore)

    def restore_generated_state() -> None:
        try:
            assert git_module.restore_files_under_barrier(cfg, snapshot) == ()
        except BaseException as exc:
            errors.append(exc)

    def write_peer_state() -> None:
        try:
            peer_attempted.set()
            git_module.write_ticket_under_barrier(cfg, peer, task_path)
        except BaseException as exc:
            errors.append(exc)
        finally:
            peer_finished.set()

    restore_worker = threading.Thread(target=restore_generated_state)
    restore_worker.start()
    assert restore_reached.wait(timeout=5)
    peer_worker = threading.Thread(target=write_peer_state)
    peer_worker.start()
    restore_worker.join(timeout=5)
    peer_worker.join(timeout=5)

    assert not restore_worker.is_alive()
    assert not peer_worker.is_alive()
    assert errors == []
    assert Ticket.read(task_path).status == "done"


def test_bump_clears_finished_megalaunch_claim(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="in_progress")
    ticket = Ticket.read(task_path)
    ticket.frontmatter["launch_generation"] = "finished-session"
    ticket.write(task_path)

    result = CliRunner().invoke(app, ["bump", slug])

    assert result.exit_code == 0, result.output
    advanced = Ticket.read(task_path)
    assert advanced.step == "2 (pr)"
    assert advanced.launch_generation is None


@pytest.mark.parametrize("status", ["paused", "done", "canceled"])
def test_mark_session_end_clears_megalaunch_claim(
    repo: Path, status: str
) -> None:
    slug, task_path = _make_task(repo, status="active")
    ticket = Ticket.read(task_path)
    ticket.frontmatter["launch_generation"] = "finished-session"
    ticket.write(task_path)
    command = ["mark", status, slug]
    if status == "canceled":
        command.extend(["--message", "No longer needed"])

    result = CliRunner().invoke(app, command)

    assert result.exit_code == 0, result.output
    ended = Ticket.read(task_path)
    assert ended.status == status
    assert ended.launch_generation is None


def test_mark_paused_from_draft_errors(repo: Path) -> None:
    slug, _ = _make_task(repo, status="draft")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "paused", slug])
    assert result.exit_code == 2


def test_mark_paused_already_paused_errors(repo: Path) -> None:
    slug, _ = _make_task(repo, status="paused")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "paused", slug])
    assert result.exit_code == 2
    assert "already 'paused'" in result.output


# --- mark done ----------------------------------------------------------------


def _unset_selected_webhook(repo: Path) -> None:
    """Keep Slack selected but make its webhook unresolvable.

    `env:UNSET_SLACK_WEBHOOK` resolves to None, which is the shape of a repo
    that selected Slack and forgot to export the variable.
    """
    config_path = repo / "coga.toml"
    config_path.write_text(
        config_path.read_text().replace(
            "env:SLACK_WEBHOOK_URL", "env:UNSET_SLACK_WEBHOOK"
        )
    )


def test_mark_done_preflights_notification_before_mutation(repo: Path) -> None:
    """An ordinary `mark done` refuses a misconfigured live channel up front.

    The outcome posts live with `fatal=False`, so a missing webhook found
    after the write would be reported and dropped. The preflight is the only
    gate that can still refuse, and it must not be reserved for assist paths.
    """
    slug, task_path = _make_task(repo, status="active")
    _unset_selected_webhook(repo)
    before = task_path.read_bytes()

    result = CliRunner().invoke(app, ["mark", "done", slug])

    assert result.exit_code == 1, result.output
    assert "no webhook is configured" in result.output
    assert task_path.read_bytes() == before
    assert "task done" not in _read_log(repo)


def test_mark_canceled_preflights_notification_before_mutation(
    repo: Path,
) -> None:
    slug, task_path = _make_task(repo, status="active")
    _unset_selected_webhook(repo)
    before = task_path.read_bytes()

    result = CliRunner().invoke(
        app, ["mark", "canceled", slug, "--message", "Owner declined"]
    )

    assert result.exit_code == 1, result.output
    assert "no webhook is configured" in result.output
    assert task_path.read_bytes() == before
    assert "canceled" not in _read_log(repo)



def test_mark_done_from_active_clears_step(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="active")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "done", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path)
    assert t.status == "done"
    assert t.step is None
    log = _read_log(repo)
    assert "task done" in log


def test_mark_done_from_draft_errors(repo: Path) -> None:
    slug, _ = _make_task(repo, status="draft")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "done", slug])
    assert result.exit_code == 2


def test_mark_done_from_paused_errors(repo: Path) -> None:
    slug, _ = _make_task(repo, status="paused")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "done", slug])
    assert result.exit_code == 2


def test_mark_done_already_done_errors(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="active")
    t = Ticket.read(task_path)
    t.frontmatter["status"] = "done"
    t.write(task_path)
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "done", slug])
    assert result.exit_code == 2
    assert "already 'done'" in result.output


# --- mark canceled ------------------------------------------------------------


@pytest.mark.parametrize(
    "status", ["draft", "active", "in_progress", "blocked", "paused"]
)
def test_mark_canceled_from_every_non_terminal_status(
    repo: Path, status: str
) -> None:
    slug, task_path = _make_task(repo, status=status)

    result = CliRunner().invoke(
        app,
        ["mark", "canceled", slug, "--message", "Decision no longer fits"],
    )

    assert result.exit_code == 0, result.output
    ticket = Ticket.read(task_path)
    assert ticket.status == "canceled"
    assert ticket.step is None
    assert (
        f"canceled ({status} → canceled): Decision no longer fits"
        in _read_log(repo)
    )


def test_mark_canceled_accepts_workflow_less_draft(repo: Path) -> None:
    slug, task_path = _make_task(repo, workflow=None, status="draft")

    result = CliRunner().invoke(
        app, ["mark", "canceled", slug, "--message", "Dream finding declined"]
    )

    assert result.exit_code == 0, result.output
    ticket = Ticket.read(task_path)
    assert ticket.status == "canceled"
    assert ticket.workflow is None
    assert ticket.step is None


def test_mark_canceled_requires_non_empty_reason(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="draft")
    runner = CliRunner()

    missing = runner.invoke(app, ["mark", "canceled", slug])
    blank = runner.invoke(
        app, ["mark", "canceled", slug, "--message", "   "]
    )

    assert missing.exit_code == 2
    assert blank.exit_code == 2
    assert "--message cannot be empty" in blank.output
    assert Ticket.read(task_path).status == "draft"
    assert "→ canceled" not in _read_log(repo)


def test_shared_mark_canceled_requires_reason_before_mutating(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="active")
    cfg = load_config(repo)
    ref = resolve_task(cfg, slug)

    with pytest.raises(CancellationError, match="reason cannot be empty"):
        mark_canceled(
            cfg,
            ref,
            read_ticket(ref),
            actor="human:marc",
            reason="   ",
            slack_text="unused",
        )

    assert Ticket.read(task_path).status == "active"


def test_mark_canceled_validates_before_writing_terminal_state(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="active")
    ticket = Ticket.read(task_path)
    ticket.frontmatter["contexts"] = ["missing/context"]
    ticket.write(task_path)
    before = ticket.render()

    result = CliRunner().invoke(
        app,
        ["mark", "canceled", slug, "--message", "No longer wanted"],
    )

    assert result.exit_code == 2
    assert "missing/context" in result.output
    assert task_path.read_text() == before
    assert Ticket.read(task_path).status == "active"
    assert "No longer wanted" not in _read_log(repo)


@pytest.mark.parametrize("status", ["done", "canceled"])
def test_mark_canceled_rejects_terminal_status(repo: Path, status: str) -> None:
    slug, task_path = _make_task(repo, status=status)

    result = CliRunner().invoke(
        app, ["mark", "canceled", slug, "--message", "No longer wanted"]
    )

    assert result.exit_code == 2
    assert status in result.output
    assert Ticket.read(task_path).status == status


def test_mark_canceled_from_blocked_preserves_historical_blocker(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="blocked")
    append_blocker(task_path, "agent:claude", "Which retry ceiling?")
    before_blackboard = read_blackboard(task_path)

    result = CliRunner().invoke(
        app, ["mark", "canceled", slug, "--message", "Declined by owner"]
    )

    assert result.exit_code == 0, result.output
    assert Ticket.read(task_path).status == "canceled"
    assert read_blackboard(task_path) == before_blackboard
    blockers = open_blockers(task_path)
    assert len(blockers) == 1
    assert blockers[0].reason == "Which retry ceiling?"


def test_mark_active_from_canceled_errors(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="canceled")

    result = CliRunner().invoke(app, ["mark", "active", slug])

    assert result.exit_code == 2
    assert "'canceled'" in result.output
    assert Ticket.read(task_path).status == "canceled"


def test_shared_mark_active_refuses_canceled_ticket(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="canceled")
    cfg = load_config(repo)
    ref = resolve_task(cfg, slug)

    with pytest.raises(CancellationError, match="cannot be reactivated"):
        mark_active(
            cfg,
            ref,
            read_ticket(ref),
            actor="human:marc",
            log_message="must not land",
        )

    assert Ticket.read(task_path).status == "canceled"


def test_mark_in_progress_uses_matching_sync_subject(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug, _ = _make_task(repo, status="active")
    cfg = load_config(repo)
    ref = resolve_task(cfg, slug)
    messages: list[str] = []

    def capture_sync(*args: object, message: str, **kwargs: object) -> None:
        messages.append(message)

    monkeypatch.setattr("coga.mark.git.sync_task_state", capture_sync)

    mark_in_progress(
        cfg,
        ref,
        read_ticket(ref),
        actor="human:marc",
        log_message="started",
    )

    assert messages == [f"Ticket: {slug} — in_progress"]


def test_strict_mark_in_progress_publishes_guarded_state_before_announcing(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Delegation cannot announce a start whose exact state CAS was refused."""
    slug, _ = _make_task(repo, status="active")
    cfg = load_config(repo)
    ref = resolve_task(cfg, slug)
    events: list[str] = []

    def exact_guard(base: str) -> None:
        assert base == "control-tip"
        events.append("guard")

    def capture_sync(*args: object, **kwargs: object) -> None:
        assert kwargs["guard"] is exact_guard
        assert kwargs["raise_state_regression"] is True
        assert kwargs["raise_git_error"] is True
        events.append("sync")
        exact_guard("control-tip")

    monkeypatch.setattr("coga.mark.git.sync_task_state", capture_sync)
    monkeypatch.setattr(
        "coga.mark.post", lambda *args, **kwargs: events.append("post")
    )

    mark_in_progress(
        cfg,
        ref,
        read_ticket(ref),
        actor="system",
        log_message="started through exact lease",
        slack_text="started",
        state_guard=exact_guard,
        strict_state_guard=True,
        strict_state_sync=True,
    )

    assert events == ["sync", "guard", "post"]


# --- --message ----------------------------------------------------------------


def test_mark_active_message_appended(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="draft")
    runner = CliRunner()
    result = runner.invoke(
        app, ["mark", "active", slug, "--message", "kicking off"]
    )
    assert result.exit_code == 0, result.output
    log = _read_log(repo)
    assert "activated (draft → active) — kicking off" in log


def test_mark_paused_message_appended(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="in_progress")
    runner = CliRunner()
    result = runner.invoke(
        app, ["mark", "paused", slug, "--message", "blocked on review"]
    )
    assert result.exit_code == 0, result.output
    log = _read_log(repo)
    assert "paused (in_progress → paused) — blocked on review" in log


def test_mark_done_message_appended(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="active")
    runner = CliRunner()
    result = runner.invoke(
        app, ["mark", "done", slug, "--message", "shipped"]
    )
    assert result.exit_code == 0, result.output
    log = _read_log(repo)
    assert "task done — shipped" in log


def test_mark_rejects_empty_message(repo: Path) -> None:
    slug, _ = _make_task(repo, status="draft")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug, "--message", ""])
    assert result.exit_code == 2


# --- prefix resolution --------------------------------------------------------


def test_mark_resolves_prefix(repo: Path) -> None:
    slug, _ = _make_task(repo, status="draft")
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug[:4]])
    assert result.exit_code == 0, result.output


def test_mark_unknown_task_errors(repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", "no-such-task-xyz"])
    assert result.exit_code == 2


# --- slack text ---------------------------------------------------------------


def test_mark_active_is_silent(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slug, _ = _make_task(repo, status="draft")
    posts: list[str] = []

    def _capture(url, json=None, timeout=None):
        posts.append(json["text"])
        class R:
            status_code = 200
            text = "ok"
        return R()

    monkeypatch.setattr("coga.notification.slack.requests.post", _capture)

    runner = CliRunner()
    result = runner.invoke(app, ["mark", "active", slug])
    assert result.exit_code == 0, result.output
    assert posts == []


def test_mark_paused_is_silent(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slug, _ = _make_task(repo, status="active")
    posts: list[str] = []

    def _capture(url, json=None, timeout=None):
        posts.append(json["text"])
        class R:
            status_code = 200
            text = "ok"
        return R()

    monkeypatch.setattr("coga.notification.slack.requests.post", _capture)

    runner = CliRunner()
    result = runner.invoke(app, ["mark", "paused", slug])
    assert result.exit_code == 0, result.output
    assert posts == []


def test_mark_done_slack_text(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slug, _ = _make_task(repo, status="active")
    posts: list[str] = []

    def _capture(url, json=None, timeout=None):
        posts.append(json["text"])
        class R:
            status_code = 200
            text = "ok"
        return R()

    monkeypatch.setattr("coga.notification.slack.requests.post", _capture)

    runner = CliRunner()
    result = runner.invoke(app, ["mark", "done", slug])
    assert result.exit_code == 0, result.output
    assert any(f"🎉 claude finished *{slug}*" in m for m in posts)


def test_mark_canceled_slack_text_includes_reason(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug, _ = _make_task(repo, status="active")
    posts: list[str] = []

    def _capture(url, json=None, timeout=None):
        posts.append(json["text"])

        class R:
            status_code = 200
            text = "ok"

        return R()

    monkeypatch.setattr("coga.notification.slack.requests.post", _capture)

    result = CliRunner().invoke(
        app, ["mark", "canceled", slug, "--message", "Owner declined"]
    )

    assert result.exit_code == 0, result.output
    assert any(
        f"🚫 marc canceled *{slug}*" in message
        and "Owner declined" in message
        for message in posts
    )


def test_mark_canceled_on_feature_lands_union_evidence_on_control(
    git_repo,
) -> None:
    """An abandoned feature branch cannot strand the cancellation reason."""
    cfg = load_config(git_repo.coga_os)
    ref = create_task(
        cfg=cfg,
        title="Decline this work",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status="active",
    )
    git_repo.checkout_branch("feature/cancel")

    # Move origin/main under the feature checkout with a concurrent union-file
    # append. The cancellation sync must retry and preserve both writers.
    local_log = (git_repo.coga_os / "log.md").read_text()
    git_repo.push_competing_commit(
        "coga/log.md", local_log + "2026-01-01 00:00 rival: unrelated event\n"
    )

    result = CliRunner().invoke(
        app,
        ["mark", "canceled", ref["slug"], "--message", "Owner declined"],
    )

    assert result.exit_code == 0, result.output
    task_rel = str(Path(ref["path"]).relative_to(git_repo.root))
    control_ticket = Ticket.parse(
        git_repo.git("show", f"main:{task_rel}", cwd=git_repo.origin)
    )
    control_log = git_repo.git("show", "main:coga/log.md", cwd=git_repo.origin)
    assert control_ticket.status == "canceled"
    assert control_ticket.step is None
    assert "canceled (active → canceled): Owner declined" in control_log
    assert "rival: unrelated event" in control_log
    assert git_repo.git("branch", "--show-current").strip() == "feature/cancel"
    assert git_repo.git("status", "--short") == ""


def _seed_pushed_task(git_repo, cfg, *, title: str, status: str = "active") -> dict:
    """Create a task and land it on the control branch, returning its ref."""
    ref = create_task(
        cfg=cfg,
        title=title,
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="claude",
        status=status,
    )
    rel = str(Path(ref["path"]).relative_to(git_repo.root))
    git_repo.git("add", rel)
    git_repo.git("commit", "-m", f"seed {ref['slug']}")
    git_repo.git("push", "origin", "main")
    return ref


@pytest.mark.parametrize(
    ("seed_status", "landed_status", "argv", "expected_local"),
    [
        ("active", "done", ["canceled", "--message", "Owner declined"], "canceled"),
        ("active", "canceled", ["done"], "done"),
        ("active", "done", ["paused"], "paused"),
        ("paused", "done", ["active"], "active"),
    ],
)
def test_transition_refuses_to_bury_terminal_control_copy(
    git_repo, seed_status, landed_status, argv, expected_local
):
    """No `mark` verb can overlay a stale ticket onto a closed control copy.

    Each transition syncs by overlaying its ticket wholesale onto the control
    tip, so every verb needs the guard — not just cancellation. The refusal is
    non-fatal by design: the local transition stands, git declines to publish
    it, and the divergence is recorded rather than resolved behind the human's
    back.
    """
    cfg = load_config(git_repo.coga_os)
    ref = _seed_pushed_task(git_repo, cfg, title="Contended work", status=seed_status)
    ticket_path = Path(ref["path"])
    rel = str(ticket_path.relative_to(git_repo.root))
    git_repo.checkout_branch("feature/contended")

    # Another checkout closes the ticket on the control branch under us.
    git_repo.push_competing_commit(
        rel,
        ticket_path.read_text().replace(
            f"status: {seed_status}", f"status: {landed_status}"
        ),
    )

    verb, *rest = argv
    result = CliRunner().invoke(app, ["mark", verb, ref["slug"], *rest])

    # Non-fatal: the command succeeds and the local transition is on disk.
    assert result.exit_code == 0, result.output
    assert read_ticket(resolve_task(cfg, ref["slug"])).status == expected_local

    # The control branch keeps the terminal copy it already had.
    control = Ticket.parse(git_repo.git("show", f"main:{rel}", cwd=git_repo.origin))
    assert control.status == landed_status

    # And the refusal is legible, not silent: it names the ticket in the log.
    log = (git_repo.coga_os / "log.md").read_text()
    assert "sync refused" in log
    assert f"terminal status would change from '{landed_status}'" in log


# --- main-agent selection timing (the approved activation-time contract) -------


def _add_codex(repo: Path, *, first: bool = False) -> None:
    """Declare a second agent, optionally ahead of claude in declaration order.

    `Config.default_agent()` is the first agent declared in the effective merged
    configuration, so `first=True` is how a test reorders the default.
    """
    toml = repo / "coga.toml"
    codex = '[agents.codex]\ncli = "codex"\nfile = "AGENTS.md"\n'
    text = toml.read_text()
    if first:
        text = text.replace("[agents.claude]", codex + "[agents.claude]", 1)
    else:
        text = text + "\n" + codex
    toml.write_text(text)


def test_activation_selects_and_freezes_the_default_main_agent(repo: Path) -> None:
    """A draft defers the choice; activation makes it and every later step keeps it."""
    cfg = load_config(repo)
    created = create_task(
        cfg=cfg,
        title="Work",
        workflow_name="code",
        contexts=[],
        owner="marc",
        status="draft",
    )
    slug, path = created["slug"], created["path"]
    assert "agent" not in Ticket.read(path).frontmatter

    assert CliRunner().invoke(app, ["mark", "active", slug]).exit_code == 0
    assert Ticket.read(path).agent == "claude"

    # Reordering the defaults afterwards changes only *future* activations.
    _add_codex(repo, first=True)
    assert load_config(repo).default_agent().name == "codex"
    runner = CliRunner()
    paused = runner.invoke(app, ["mark", "paused", slug, "--message", "hold"])
    assert paused.exit_code == 0, paused.output
    assert Ticket.read(path).agent == "claude"
    assert runner.invoke(app, ["mark", "active", slug]).exit_code == 0
    assert Ticket.read(path).agent == "claude"


def test_activation_keeps_an_explicit_choice(repo: Path) -> None:
    _add_codex(repo)
    cfg = load_config(repo)
    created = create_task(
        cfg=cfg,
        title="Work",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="codex",
        status="draft",
    )
    assert CliRunner().invoke(app, ["mark", "active", created["slug"]]).exit_code == 0
    assert Ticket.read(created["path"]).agent == "codex"


def test_activation_refuses_when_the_selected_agent_is_unconfigured(
    repo: Path,
) -> None:
    """Removing a selected agent is an error to fix, not a substitution."""
    _add_codex(repo)
    cfg = load_config(repo)
    created = create_task(
        cfg=cfg,
        title="Work",
        workflow_name="code",
        contexts=[],
        owner="marc",
        agent="codex",
        status="draft",
    )
    before = Path(created["path"]).read_bytes()
    toml = repo / "coga.toml"
    toml.write_text(toml.read_text().replace(
        '\n[agents.codex]\ncli = "codex"\nfile = "AGENTS.md"\n', ""
    ))

    result = CliRunner().invoke(app, ["mark", "active", created["slug"]])

    assert result.exit_code != 0
    assert "not a configured agent type" in result.output
    # A failed preparation writes nothing — not the status, not a new agent.
    assert Path(created["path"]).read_bytes() == before


def test_a_failed_activation_does_not_write_a_newly_chosen_agent(
    repo: Path,
) -> None:
    """Selection commits only with the successful transition."""
    _write(
        repo / "coga.toml",
        (repo / "coga.toml").read_text()
        + '\n[ticket.fields.tier]\ndescription = "Priority tier"\nrequired = true\n',
    )
    cfg = load_config(repo)
    created = create_task(
        cfg=cfg,
        title="Work",
        workflow_name="code",
        contexts=[],
        owner="marc",
        status="draft",
    )
    before = Path(created["path"]).read_bytes()

    result = CliRunner().invoke(app, ["mark", "active", created["slug"]])

    assert result.exit_code != 0
    assert "tier" in result.output
    assert Path(created["path"]).read_bytes() == before
    assert "agent" not in Ticket.read(created["path"]).frontmatter


def test_main_peer_main_rotation_is_stable(repo: Path) -> None:
    """With unchanged config, main A -> peer B -> main A."""
    _add_codex(repo)
    _write(
        repo / "workflows" / "peer.md",
        """
        ---
        name: peer
        steps:
          - name: build
            assignee: agent
          - name: review
            assignee: other-agent
          - name: finish
            assignee: agent
        ---

        ## build
        Build it.

        ## review
        Review it.

        ## finish
        Finish it.
        """,
    )
    cfg = load_config(repo)
    created = create_task(
        cfg=cfg,
        title="Work",
        workflow_name="peer",
        contexts=[],
        owner="marc",
        status="in_progress",
    )
    slug = created["slug"]
    runner = CliRunner()
    # Creating live makes the same choice activation would.
    assert Ticket.read(created["path"]).agent == "claude"

    assert derived_operator(repo, slug) == "claude"
    assert runner.invoke(app, ["bump", slug]).exit_code == 0
    assert derived_operator(repo, slug) == "codex"
    assert runner.invoke(app, ["bump", slug]).exit_code == 0
    assert derived_operator(repo, slug) == "claude"


def test_a_peer_config_edit_reroutes_the_next_peer_step(repo: Path) -> None:
    """Peers stay live configuration, never frozen ticket metadata."""
    _add_codex(repo)
    toml = repo / "coga.toml"
    # Three agents, so the peer must be declared explicitly. Point claude at
    # codex before creating the ticket, so its `other-agent` step resolves.
    toml.write_text(
        toml.read_text().replace(
            '[agents.claude]\ncli = "claude"',
            '[agents.claude]\npeer = "codex"\ncli = "claude"',
        )
        + '\n[agents.reviewer]\ncli = "reviewer"\nfile = "AGENTS.md"\n'
    )
    _write(
        repo / "workflows" / "peer.md",
        """
        ---
        name: peer
        steps:
          - name: build
            assignee: agent
          - name: review
            assignee: other-agent
        ---

        ## build
        Build it.

        ## review
        Review it.
        """,
    )
    cfg = load_config(repo)
    created = create_task(
        cfg=cfg,
        title="Work",
        workflow_name="peer",
        contexts=[],
        owner="marc",
        agent="claude",
        status="in_progress",
    )
    slug = created["slug"]
    assert CliRunner().invoke(app, ["bump", slug]).exit_code == 0
    assert derived_operator(repo, slug) == "codex"

    # Re-point the peer: the *same* frozen ticket now reviews with reviewer.
    toml.write_text(toml.read_text().replace('peer = "codex"', 'peer = "reviewer"'))
    assert derived_operator(repo, slug) == "reviewer"
    assert "assignee" not in Ticket.read(created["path"]).frontmatter


def test_no_transition_restores_removed_metadata(repo: Path) -> None:
    """No writer reintroduces the removed keys across a ticket's whole life."""
    cfg = load_config(repo)
    created = create_task(
        cfg=cfg,
        title="Work",
        workflow_name="code",
        contexts=[],
        owner="marc",
        status="draft",
    )
    slug, path = created["slug"], Path(created["path"])
    removed = ("slug", "human", "assignee", "watchers", "script")

    def assert_clean(after: str) -> None:
        frontmatter = Ticket.read(path).frontmatter
        for key in removed:
            assert key not in frontmatter, f"{key!r} came back after {after}"

    runner = CliRunner()
    assert_clean("create")
    assert runner.invoke(app, ["mark", "active", slug]).exit_code == 0
    assert_clean("mark active")
    # `in_progress` is launch's flip, not a `mark` subcommand.
    started = Ticket.read(path)
    started.frontmatter["status"] = "in_progress"
    started.write(path)
    assert_clean("in_progress")

    for label, command in (
        ("bump", ["bump", slug]),
        ("block", ["block", "--task", slug, "--reason", "which ceiling?"]),
        ("unblock", ["unblock", slug, "--answer", "the default one"]),
        ("mark paused", ["mark", "paused", slug, "--message", "hold"]),
        ("mark active again", ["mark", "active", slug]),
        ("mark done", ["mark", "done", slug]),
    ):
        result = runner.invoke(app, command)
        assert result.exit_code == 0, f"{label}: {result.output}"
        assert_clean(label)
    assert Ticket.read(path).status == "done"
