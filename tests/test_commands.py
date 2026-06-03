from __future__ import annotations

import shutil
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.scaffold import scaffold_task
from relay.config import load_config
from relay.tasks import list_tasks
from relay.ticket import Ticket


# Source of the bundled `bootstrap/delete-task` skill — `relay delete` and a
# `mode: script` step both dispatch into it. Test repos are hand-built and do
# not run `relay init`, so tests materialize it explicitly.
DELETE_SKILL_SRC = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "relay"
    / "resources"
    / "templates"
    / "relay-os"
    / "bootstrap"
    / "skills"
    / "bootstrap"
    / "delete-task"
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _install_delete_skill(repo: Path) -> None:
    shutil.copytree(DELETE_SKILL_SRC, repo / "skills" / "bootstrap" / "delete-task")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    company = tmp_path / "relay-os"
    _write(
        company / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "relay.local.toml", 'user = "marc"\n')
    _write(
        company / "workflows" / "code.md",
        """
        ---
        name: code
        description: tiny.
        steps:
          - name: implement
          - name: pr
          - name: merge
        ---

        ## implement
        Write the code.
        """,
    )
    monkeypatch.chdir(company)
    return company


def _make_task(repo: Path, *, workflow: str | None = "code", status: str = "in_progress") -> tuple[str, Path]:
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg, title="Work", workflow_name=workflow,
        contexts=[], mode="interactive", owner="marc", assignee="claude",
        watchers=[], status=status,
    )
    return ref["slug"], ref["path"]


# --- bump ---------------------------------------------------------------------


def test_bump_advances(repo: Path) -> None:
    slug, _ = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    cfg = load_config(repo)
    ref = list_tasks(cfg)[0]
    t = Ticket.read(ref.path / "ticket.md")
    assert t.step == "2 (pr)"
    assert "advanced to step 2" in (ref.path / "log.md").read_text()


def test_bump_rewinds_by_number(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    runner.invoke(app, ["bump", slug])
    runner.invoke(app, ["bump", slug])

    result = runner.invoke(app, ["bump", slug, "--to", "1"])

    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.step == "1 (implement)"
    log = (task_path / "log.md").read_text()
    assert "rewound to step 1 (implement)" in log


def test_bump_backward_rewinds_one_step(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    runner.invoke(app, ["bump", slug])
    runner.invoke(app, ["bump", slug])

    result = runner.invoke(app, ["bump", slug, "--backward"])

    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.step == "2 (pr)"
    assert "rewound to step 2 (pr)" in (task_path / "log.md").read_text()


def test_bump_rewind_rejects_invalid_current_step(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    t = Ticket.read(task_path / "ticket.md")
    t.frontmatter["step"] = "99 (bogus)"
    t.write(task_path / "ticket.md")

    result = CliRunner().invoke(app, ["bump", slug, "--backward"])

    assert result.exit_code == 2, result.output
    assert "invalid step '99 (bogus)'" in result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.step == "99 (bogus)"


def test_bump_rejects_named_rewind_target(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    runner.invoke(app, ["bump", slug])

    result = runner.invoke(app, ["bump", slug, "--to", "implement"])

    assert result.exit_code == 2, result.output
    assert "Invalid value for '--to'" in result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.step == "2 (pr)"


def test_bump_rejects_unknown_rewind_target(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    runner.invoke(app, ["bump", slug])

    result = runner.invoke(app, ["bump", slug, "--to", "99"])

    assert result.exit_code == 2, result.output
    assert "Unknown step 99" in result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.step == "2 (pr)"


def test_bump_to_refuses_forward_skip(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()

    result = runner.invoke(app, ["bump", slug, "--to", "3"])

    assert result.exit_code == 2, result.output
    assert "Cannot skip ahead" in result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.step == "1 (implement)"


def test_bump_rewind_refuses_supervised_agent(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    runner.invoke(app, ["bump", slug])

    result = runner.invoke(
        app,
        ["bump", slug, "--backward"],
        env={"RELAY_SUPERVISED": "1"},
    )

    assert result.exit_code == 2, result.output
    assert "Agents cannot rewind" in result.output
    assert "relay panic" in result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.step == "2 (pr)"


def test_bump_supervised_prints_handoff_hint_when_assignee_changes(repo: Path) -> None:
    # Next step carries `assignee: owner`, so on bump the assignee rewrites
    # away from the current agent — the hint should say handoff.
    _write(
        repo / "workflows" / "handoff.md",
        """
        ---
        name: handoff
        description: next step is the owner's.
        steps:
          - name: implement
          - name: review
            assignee: owner
        ---
        """,
    )
    slug, _ = _make_task(repo, workflow="handoff")
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug], env={"RELAY_SUPERVISED": "1"})
    assert result.exit_code == 0, result.output
    assert "Supervised launch" in result.output
    # owner is a human, not a configured agent → the supervisor stops.
    assert "will stop and return to the caller" in result.output


def test_bump_supervised_prints_chain_hint_on_agent_rotation(repo: Path) -> None:
    # Regression: bumping from a claude step into an `other-agent` (codex) step
    # is an assignee *change*, but the supervisor chains across agent rotations
    # — so the hint must announce the relaunch, not a stop. The old
    # `new_assignee is None` logic wrongly printed the handoff/"will stop" hint.
    _add_codex_agent(repo)
    _write_peer_review_workflow(repo)
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg, title="W", workflow_name="peer",
        contexts=[], mode="interactive",
        owner="marc", assignee="claude",
        human="marc", agent="claude",
        watchers=[], status="in_progress",
    )
    slug = ref["slug"]
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug], env={"RELAY_SUPERVISED": "1"})
    assert result.exit_code == 0, result.output
    assert "Supervised launch" in result.output
    # claude → codex is a rotation between two configured agents → chains.
    assert "spawn a fresh agent session" in result.output
    assert "will stop and return to the caller" not in result.output


def test_bump_supervised_prints_chain_hint_when_assignee_unchanged(repo: Path) -> None:
    # `code` workflow has no per-step assignee tokens, so the agent stays
    # the assignee across bumps — the hint should announce the relaunch.
    # No skills on the next step is fine; chain is gated on assignee, not skills.
    slug, _ = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug], env={"RELAY_SUPERVISED": "1"})
    assert result.exit_code == 0, result.output
    assert "Supervised launch" in result.output
    assert "spawn a fresh agent session" in result.output


def test_bump_unsupervised_prints_no_hint(repo: Path) -> None:
    slug, _ = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    assert "Supervised launch" not in result.output


def test_bump_past_final_step_errors_with_mark_done_hint(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    # Workflow has 3 steps; advance to the final step.
    runner.invoke(app, ["bump", slug])
    runner.invoke(app, ["bump", slug])
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 2, result.output
    assert "final step" in result.output
    assert f"relay mark done {slug}" in result.output
    # Ticket stays in progress — bump does not mark done.
    t = Ticket.read(task_path / "ticket.md")
    assert t.status == "in_progress"


def test_bump_rejects_non_in_progress(repo: Path) -> None:
    slug, _ = _make_task(repo, status="paused")
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 2


def test_bump_no_workflow_errors_with_mark_done_hint(repo: Path) -> None:
    slug, task_path = _make_task(repo, workflow=None)
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 2, result.output
    assert "no workflow" in result.output
    assert f"relay mark done {slug}" in result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.status == "in_progress"


# --- panic --------------------------------------------------------------------


def test_panic_writes_blocker(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["panic", "--task", slug, "--reason", "unclear ceiling for 429 backoff"])
    # Panic exits non-zero so a parent process can detect agent distress.
    assert result.exit_code == 1, result.output
    blackboard = (task_path / "blackboard.md").read_text()
    assert "unclear ceiling for 429 backoff" in blackboard
    assert "## Blockers" in blackboard
    assert "panic:" in (task_path / "log.md").read_text()


# --- delete -------------------------------------------------------------------


def test_delete_removes_task_directory(repo: Path) -> None:
    _install_delete_skill(repo)
    slug, task_path = _make_task(repo)
    assert task_path.is_dir()
    runner = CliRunner()
    result = runner.invoke(app, ["delete", slug])
    assert result.exit_code == 0, result.output
    assert not task_path.exists()
    assert "deleted" in result.output


def test_delete_resolves_prefix(repo: Path) -> None:
    _install_delete_skill(repo)
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["delete", slug[:6]])
    assert result.exit_code == 0, result.output
    assert not task_path.exists()


def test_delete_unknown_task_exits_nonzero(repo: Path) -> None:
    # Unknown slug fails at resolution, before the skill is even consulted.
    runner = CliRunner()
    result = runner.invoke(app, ["delete", "no-such-task-xyz"])
    assert result.exit_code == 2


def test_delete_missing_skill_exits_nonzero(repo: Path) -> None:
    # The skill is the implementation; without it `relay delete` fails loud
    # rather than silently falling back to a private rmtree.
    slug, task_path = _make_task(repo)
    result = CliRunner().invoke(app, ["delete", slug])
    assert result.exit_code == 2
    assert task_path.is_dir()
    assert "bootstrap/delete-task" in result.output


def test_delete_skill_runs_as_script_step(repo: Path) -> None:
    # The same skill `relay delete` dispatches into is independently
    # launchable: a `mode: script` task whose one step references it deletes
    # its own directory on `relay launch`.
    _install_delete_skill(repo)
    _write(
        repo / "workflows" / "delete-self.md",
        """
        ---
        name: delete-self
        description: script worker.
        steps:
          - name: run
            skills:
              - bootstrap/delete-task
        ---
        """,
    )
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg, title="Throwaway", workflow_name="delete-self",
        contexts=[], mode="script", owner="marc", assignee="claude",
        watchers=[], status="active",
    )
    task_path = ref["path"]
    assert task_path.is_dir()

    result = CliRunner().invoke(app, ["launch", ref["slug"]])
    assert result.exit_code == 0, result.output
    assert not task_path.exists()


# --- slack --------------------------------------------------------------------


def test_slack_logs(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["slack", "--task", slug, "--message", "opened PR #142"])
    assert result.exit_code == 0
    assert "slack: opened PR #142" in (task_path / "log.md").read_text()


# --- bump --message -----------------------------------------------------------


def test_bump_message_appended_to_log(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["bump", slug, "--message", "PR opened: https://example/142"],
    )
    assert result.exit_code == 0, result.output
    log = (task_path / "log.md").read_text()
    assert "advanced to step 2 (pr) — PR opened: https://example/142" in log


def test_mark_done_message_on_no_workflow(repo: Path) -> None:
    slug, task_path = _make_task(repo, workflow=None)
    runner = CliRunner()
    result = runner.invoke(
        app, ["mark", "done", slug, "--message", "talked to marc, scope ok"]
    )
    assert result.exit_code == 0, result.output
    log = (task_path / "log.md").read_text()
    assert "task done — talked to marc, scope ok" in log


def test_mark_done_message_on_final_step(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    runner.invoke(app, ["bump", slug])
    runner.invoke(app, ["bump", slug])
    result = runner.invoke(
        app, ["mark", "done", slug, "--message", "shipped to prod"]
    )
    assert result.exit_code == 0, result.output
    log = (task_path / "log.md").read_text()
    assert "task done — shipped to prod" in log


def test_bump_rejects_empty_message(repo: Path) -> None:
    slug, _ = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug, "--message", ""])
    assert result.exit_code == 2


# --- bump assignee handoff ----------------------------------------------------


def _write_assignee_workflow(repo: Path) -> None:
    """Workflow whose three steps each declare a different role token."""
    _write(
        repo / "workflows" / "review.md",
        """
        ---
        name: review
        description: Roles per step.
        steps:
          - name: implement
            assignee: agent
          - name: review
            assignee: human
          - name: signoff
            assignee: owner
        ---
        """,
    )


def test_bump_resolves_role_token_to_ticket_field(repo: Path) -> None:
    _write_assignee_workflow(repo)
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg, title="W", workflow_name="review",
        contexts=[], mode="interactive",
        owner="marc", assignee="claude",
        human="marc", agent="claude",
        watchers=[], status="in_progress",
    )
    slug = ref["slug"]
    task_path = ref["path"]

    # Step 1 declared `assignee: agent` → resolved at scaffold time.
    t = Ticket.read(task_path / "ticket.md")
    assert t.assignee == "claude"

    # Bump into step 2 (assignee: human) → ticket.assignee = ticket.human.
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.step == "2 (review)"
    assert t.assignee == "marc"
    log = (task_path / "log.md").read_text()
    assert "→ assigned to marc" in log

    # Bump into step 3 (assignee: owner) → ticket.assignee = ticket.owner.
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.assignee == "marc"  # owner == marc, no change → no handoff line
    log = (task_path / "log.md").read_text()
    # Only one handoff line so far (the human→owner step is a no-op handoff).
    assert log.count("→ assigned to") == 1


def test_bump_no_assignee_declared_leaves_assignee_unchanged(repo: Path) -> None:
    # The default `code` workflow in this fixture has no assignee declarations.
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.assignee == "claude"  # unchanged
    log = (task_path / "log.md").read_text()
    assert "→ assigned to" not in log


def test_bump_role_token_with_missing_field_fails_loud(repo: Path) -> None:
    _write_assignee_workflow(repo)
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg, title="W", workflow_name="review",
        contexts=[], mode="interactive",
        owner="marc", assignee="claude",
        human="marc", agent="claude",
        watchers=[], status="in_progress",
    )
    # Hand-edit the ticket to remove the `human` field, then bump into the
    # human step. Bump must refuse rather than silently skip.
    t = Ticket.read(ref["path"] / "ticket.md")
    del t.frontmatter["human"]
    t.write(ref["path"] / "ticket.md")

    runner = CliRunner()
    result = runner.invoke(app, ["bump", ref["slug"]])
    assert result.exit_code == 2, result.output
    assert "human" in result.output


def _add_codex_agent(repo: Path) -> None:
    """Append a second agent type so `other-agent` has a peer to resolve to."""
    toml = repo / "relay.toml"
    toml.write_text(
        toml.read_text()
        + dedent(
            """
            [agents.codex]
            cli = "codex"
            auto = "exec"
            file = "AGENTS.md"
            """
        )
    )


def _write_peer_review_workflow(repo: Path) -> None:
    """implement (coder) → peer-review (the other agent) → signoff (owner)."""
    _write(
        repo / "workflows" / "peer.md",
        """
        ---
        name: peer
        description: Reviewed by the other agent.
        steps:
          - name: implement
            assignee: agent
          - name: peer-review
            assignee: other-agent
          - name: signoff
            assignee: owner
        ---
        """,
    )


def test_other_agent_resolves_to_the_peer_on_bump(repo: Path) -> None:
    _add_codex_agent(repo)
    _write_peer_review_workflow(repo)
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg, title="W", workflow_name="peer",
        contexts=[], mode="interactive",
        owner="marc", assignee="claude",
        human="marc", agent="claude",
        watchers=[], status="in_progress",
    )
    slug, task_path = ref["slug"], ref["path"]

    # Step 1 `assignee: agent` → the coder (claude).
    t = Ticket.read(task_path / "ticket.md")
    assert t.assignee == "claude"

    # Bump into peer-review (`assignee: other-agent`) → codex, the agent
    # that is not the ticket's `agent: claude`.
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.step == "2 (peer-review)"
    assert t.assignee == "codex"
    assert "→ assigned to codex" in (task_path / "log.md").read_text()


def test_bump_rewind_resolves_target_step_assignee(repo: Path) -> None:
    _add_codex_agent(repo)
    _write_peer_review_workflow(repo)
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg, title="W", workflow_name="peer",
        contexts=[], mode="interactive",
        owner="marc", assignee="claude",
        human="marc", agent="claude",
        watchers=[], status="in_progress",
    )
    slug, task_path = ref["slug"], ref["path"]

    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.step == "2 (peer-review)"
    assert t.assignee == "codex"

    result = runner.invoke(app, ["bump", slug, "--to", "1"])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path / "ticket.md")
    assert t.step == "1 (implement)"
    assert t.assignee == "claude"
    log = (task_path / "log.md").read_text()
    assert "rewound to step 1 (implement) → assigned to claude" in log


def test_other_agent_flips_with_the_coder(repo: Path) -> None:
    # A change written by codex is peer-reviewed by claude — the token is
    # relative to the ticket's own `agent:`, not hard-coded.
    _add_codex_agent(repo)
    _write_peer_review_workflow(repo)
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg, title="W", workflow_name="peer",
        contexts=[], mode="interactive",
        owner="marc", assignee="codex",
        human="marc", agent="codex",
        watchers=[], status="in_progress",
    )
    runner = CliRunner()
    result = runner.invoke(app, ["bump", ref["slug"]])
    assert result.exit_code == 0, result.output
    t = Ticket.read(ref["path"] / "ticket.md")
    assert t.assignee == "claude"


def test_other_agent_step_one_resolves_at_scaffold_time(repo: Path) -> None:
    _add_codex_agent(repo)
    _write(
        repo / "workflows" / "peer-first.md",
        """
        ---
        name: peer-first
        description: First step is the other agent.
        steps:
          - name: peer-review
            assignee: other-agent
        ---
        """,
    )
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg, title="W", workflow_name="peer-first",
        contexts=[], mode="interactive",
        owner="marc", assignee="claude",
        human="marc", agent="claude",
        watchers=[], status="in_progress",
    )
    t = Ticket.read(ref["path"] / "ticket.md")
    assert t.assignee == "codex"


def test_other_agent_fails_loud_without_exactly_two_agents(repo: Path) -> None:
    # The base fixture configures only `claude`, so there is no peer to pick.
    _write_peer_review_workflow(repo)
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg, title="W", workflow_name="peer",
        contexts=[], mode="interactive",
        owner="marc", assignee="claude",
        human="marc", agent="claude",
        watchers=[], status="in_progress",
    )
    runner = CliRunner()
    result = runner.invoke(app, ["bump", ref["slug"]])
    assert result.exit_code == 2, result.output
    assert "other-agent" in result.output
    # assignee must not have changed on the failed bump.
    t = Ticket.read(ref["path"] / "ticket.md")
    assert t.assignee == "claude"
    assert t.step == "1 (implement)"


def test_bump_freezes_bare_string_workflow_then_advances(repo: Path) -> None:
    # Hand-authored ticket: `workflow:` is a bare string ref, no `step:`.
    legacy = repo / "tasks" / "legacy"
    legacy.mkdir(parents=True)
    (legacy / "ticket.md").write_text(dedent(
        """
        ---
        title: Legacy
        status: in_progress
        mode: interactive
        owner: marc
        human: marc
        agent: claude
        assignee: claude
        contexts: []
        skills: []
        workflow: code
        ---
        """
    ).lstrip())
    (legacy / "blackboard.md").write_text("")
    (legacy / "log.md").write_text("")

    runner = CliRunner()
    result = runner.invoke(app, ["bump", "legacy"])
    assert result.exit_code == 0, result.output
    t = Ticket.read(legacy / "ticket.md")
    # Workflow now frozen; bump advanced step 1 → 2.
    assert isinstance(t.workflow, dict)
    assert t.step == "2 (pr)"


def test_bump_handoff_appears_in_slack_text(repo: Path) -> None:
    _write_assignee_workflow(repo)
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg, title="W", workflow_name="review",
        contexts=[], mode="interactive",
        owner="marc", assignee="claude",
        human="marc", agent="claude",
        watchers=[], status="in_progress",
    )
    runner = CliRunner()
    result = runner.invoke(app, ["bump", ref["slug"]])
    assert result.exit_code == 0, result.output
    # Echo to stdout includes the same handoff phrasing as the slack text.
    assert "→ assigned to marc" in result.output


# --- show ---------------------------------------------------------------------


def test_show_prints_ticket_blackboard_and_log(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    (task_path / "blackboard.md").write_text("# Plan\n\nfigure it out\n")
    (task_path / "log.md").write_text("created task\n")
    runner = CliRunner()
    result = runner.invoke(app, ["show", slug])
    assert result.exit_code == 0, result.output
    assert "ticket.md" in result.output
    assert "blackboard.md" in result.output
    assert "log.md" in result.output
    assert "figure it out" in result.output


def test_show_resolves_prefix(repo: Path) -> None:
    slug, _ = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["show", slug[:6]])
    assert result.exit_code == 0, result.output
    assert "ticket.md" in result.output


def test_show_handles_missing_blackboard_and_log(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    (task_path / "blackboard.md").unlink(missing_ok=True)
    (task_path / "log.md").unlink(missing_ok=True)
    runner = CliRunner()
    result = runner.invoke(app, ["show", slug])
    assert result.exit_code == 0, result.output
    assert "no blackboard.md" in result.output
    assert "no log.md" in result.output


def test_show_unknown_task_exits_nonzero(repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["show", "no-such-task-xyz"])
    assert result.exit_code == 2


# --- status -------------------------------------------------------------------


def test_status_shows_active(repo: Path) -> None:
    slug, _ = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert slug in result.output


def test_status_narrow_terminal_keeps_each_task_on_one_line(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, title="anything", workflow_name=None,
        contexts=[], mode="interactive", owner="marc", assignee="claude",
        watchers=[], status="active", slug_override="t1",
    )
    monkeypatch.setenv("COLUMNS", "60")
    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    # Header + one data row + separator, followed by the summary footer.
    # Anything more in the table means Rich wrapped.
    body = [line for line in result.output.splitlines() if line.strip()]
    assert body[-1] == "1 task  ·  1 active"
    assert len(body[:-1]) <= 3, result.output


def test_status_does_not_show_title_column(repo: Path) -> None:
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, title="A distinctive ticket title", workflow_name=None,
        contexts=[], mode="interactive", owner="marc", assignee="claude",
        watchers=[], status="active", slug_override="t1",
    )
    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    assert "A distinctive ticket title" not in result.output
    assert "title" not in result.output.lower().split()


# --- validate -----------------------------------------------------------------


def test_validate_clean_repo_succeeds(repo: Path) -> None:
    _make_task(repo, workflow=None)
    runner = CliRunner()
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0, result.output
    assert "All good" in result.output


def test_validate_json_emits_payload(repo: Path) -> None:
    _make_task(repo, workflow=None)
    runner = CliRunner()
    result = runner.invoke(app, ["validate", "--json"])
    assert result.exit_code == 0, result.output
    import json
    payload = json.loads(result.output)
    assert payload["fixes"] == []
    assert payload["issues"] == []
    assert payload["ok_count"] == 1


def test_validate_fix_json_repairs_missing_workspace_file(repo: Path) -> None:
    _, task_path = _make_task(repo, workflow=None)
    (task_path / "blackboard.md").unlink()

    runner = CliRunner()
    result = runner.invoke(app, ["validate", "--fix", "--json"])

    assert result.exit_code == 0, result.output
    import json
    payload = json.loads(result.output)
    assert payload["fixes"][0]["message"] == "created blackboard.md"
    assert payload["issues"] == []
    assert (task_path / "blackboard.md").is_file()


def test_validate_warns_for_large_blackboard(repo: Path) -> None:
    _, task_path = _make_task(repo, workflow=None)
    (task_path / "blackboard.md").write_text("x" * 2048)

    runner = CliRunner()
    result = runner.invoke(app, ["validate", "--max-blackboard-kb", "1"])
    assert result.exit_code == 0, result.output
    assert "[WARN]" in result.output
    assert "large-blackboard" in result.output


def test_status_shows_done_tasks(repo: Path) -> None:
    slug, task_path = _make_task(repo, workflow=None)
    # Mark done directly
    t = Ticket.read(task_path / "ticket.md")
    t.frontmatter["status"] = "done"
    t.write(task_path / "ticket.md")
    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    assert slug in result.output


# --- status --order-by / --reverse / updated column ---------------------------


def _set_log_timestamp(task_path: Path, when: str) -> None:
    """Overwrite task's log.md with a single line at the given timestamp."""
    (task_path / "log.md").write_text(f"{when} [system] backdated\n")


def test_status_includes_updated_column(repo: Path) -> None:
    _make_task(repo, workflow=None)
    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    assert "updated" in result.output


def test_status_default_orders_by_updated_desc(repo: Path) -> None:
    cfg = load_config(repo)
    older = scaffold_task(
        cfg=cfg, title="older", workflow_name=None,
        contexts=[], mode="interactive", owner="marc", assignee="claude",
        watchers=[], status="active", slug_override="aaa-old",
    )
    newer = scaffold_task(
        cfg=cfg, title="newer", workflow_name=None,
        contexts=[], mode="interactive", owner="marc", assignee="claude",
        watchers=[], status="active", slug_override="zzz-new",
    )
    _set_log_timestamp(older["path"], "2026-01-01 09:00")
    _set_log_timestamp(newer["path"], "2026-04-30 17:00")

    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    new_idx = result.output.index("zzz-new")
    old_idx = result.output.index("aaa-old")
    assert new_idx < old_idx, result.output


def test_status_order_by_slug_is_alphabetical(repo: Path) -> None:
    cfg = load_config(repo)
    for slug in ("zeta", "alpha", "mu"):
        scaffold_task(
            cfg=cfg, title=slug, workflow_name=None,
            contexts=[], mode="interactive", owner="marc", assignee="claude",
            watchers=[], status="active", slug_override=slug,
        )
    runner = CliRunner()
    result = runner.invoke(app, ["status", "--order-by", "slug"])
    assert result.exit_code == 0, result.output
    a = result.output.index("alpha")
    m = result.output.index("mu")
    z = result.output.index("zeta")
    assert a < m < z, result.output


def test_status_reverse_flips_order(repo: Path) -> None:
    cfg = load_config(repo)
    for slug in ("alpha", "zeta"):
        scaffold_task(
            cfg=cfg, title=slug, workflow_name=None,
            contexts=[], mode="interactive", owner="marc", assignee="claude",
            watchers=[], status="active", slug_override=slug,
        )
    runner = CliRunner()
    result = runner.invoke(app, ["status", "--order-by", "slug", "--reverse"])
    assert result.exit_code == 0, result.output
    assert result.output.index("zeta") < result.output.index("alpha"), result.output


def test_status_rejects_unknown_order_by(repo: Path) -> None:
    _make_task(repo, workflow=None)
    runner = CliRunner()
    result = runner.invoke(app, ["status", "--order-by", "bogus"])
    assert result.exit_code == 2


def test_status_tasks_without_log_sort_to_end(repo: Path) -> None:
    cfg = load_config(repo)
    has_log = scaffold_task(
        cfg=cfg, title="logged", workflow_name=None,
        contexts=[], mode="interactive", owner="marc", assignee="claude",
        watchers=[], status="active", slug_override="zzz-logged",
    )
    no_log = scaffold_task(
        cfg=cfg, title="no log", workflow_name=None,
        contexts=[], mode="interactive", owner="marc", assignee="claude",
        watchers=[], status="active", slug_override="aaa-nolog",
    )
    _set_log_timestamp(has_log["path"], "2026-04-30 17:00")
    (no_log["path"] / "log.md").unlink()

    runner = CliRunner()
    # Default order (updated desc) — logged task on top, no-log task at bottom.
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    assert result.output.index("zzz-logged") < result.output.index("aaa-nolog")

    # Even with --reverse, missing log stays at the bottom.
    result = runner.invoke(app, ["status", "--reverse"])
    assert result.exit_code == 0, result.output
    assert result.output.index("zzz-logged") < result.output.index("aaa-nolog")
