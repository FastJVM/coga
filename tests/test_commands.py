from __future__ import annotations

import shutil
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from coga.blackboard import append_blocker
from coga.commands import delete as delete_cmd
from coga.cli import app
from coga.create import create_task
from coga.config import load_config
from coga.logfile import task_log_lines
from coga.paths import log_path
from coga.repl_supervisor import EXPECTED_STEP_ENV, EXPECTED_TASK_ENV, SENTINEL_ENV
from coga.taskfile import join_task_body, read_blackboard, replace_blackboard
from coga.tasks import list_tasks
from coga.ticket import Ticket


def _log_text(repo: Path, ref: str) -> str:
    """The repo-global log filtered to one task ref, joined back into text.

    The single-file format moves per-task history into one repo-global
    `coga/log.md`; a task's history is the subset of lines tagged with its
    ref. Tests that used to read `tasks/<slug>/log.md` read this instead.
    """
    return "\n".join(task_log_lines(load_config(repo), ref))


# Source of the bundled `bootstrap/delete-task` skill — `coga delete` and a
# `mode: script` step both dispatch into it. Test repos are hand-built and do
# not run `coga init`, so tests materialize it explicitly.
DELETE_SKILL_SRC = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "coga"
    / "resources"
    / "templates"
    / "coga"
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


def _make_task(
    repo: Path,
    *,
    workflow: str | None = "code",
    status: str = "in_progress",
    force_directory: bool = False,
) -> tuple[str, Path]:
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg, title="Work", workflow_name=workflow,
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status=status, force_directory=force_directory,
    )
    # File form: `ref["path"]` is the `tasks/<slug>.md` ticket file (it *is* the
    # ticket). Directory form (`force_directory=True`): it is the task
    # directory; the ticket lives at `<dir>/ticket.md`. Tests that read ticket
    # content use the returned path directly in the file-form case.
    path = ref["path"]
    return ref["slug"], path


def _write_workflow_less_task(
    repo: Path, slug: str = "work", status: str = "in_progress"
) -> tuple[str, Path]:
    """Write a workflow-less task directly to disk. `create_task` refuses to
    create a workflow-less non-draft task now, so on-disk construction is the
    only way to exercise the workflow-less (structurally stuck) shape.

    Written in the default file form (`tasks/<slug>.md`); the returned path is
    the ticket file itself, so callers read it directly like a `_make_task`
    result."""
    tasks = repo / "tasks"
    tasks.mkdir(parents=True, exist_ok=True)
    ticket_path = tasks / f"{slug}.md"
    ticket_path.write_text(dedent(f"""
        ---
        slug: {slug}
        title: Work
        status: {status}
        owner: marc
        human: marc
        agent: claude
        assignee: claude
        contexts: []
        skills: []
        workflow: null
        ---

        ## Description

        <!-- coga:blackboard -->

        # Blackboard
    """).lstrip())
    return slug, ticket_path


# --- bump ---------------------------------------------------------------------


def test_bump_advances(repo: Path) -> None:
    slug, _ = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    cfg = load_config(repo)
    ref = list_tasks(cfg)[0]
    t = Ticket.read(ref.ticket_path)
    assert t.step == "2 (pr)"
    assert "advanced to step 2" in _log_text(repo, slug)


def test_bump_rewinds_by_number(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    runner.invoke(app, ["bump", slug])
    runner.invoke(app, ["bump", slug])

    result = runner.invoke(app, ["bump", slug, "--to", "1"])

    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path)
    assert t.step == "1 (implement)"
    log = _log_text(repo, slug)
    assert "rewound to step 1 (implement)" in log


def test_bump_backward_rewinds_one_step(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    runner.invoke(app, ["bump", slug])
    runner.invoke(app, ["bump", slug])

    result = runner.invoke(app, ["bump", slug, "--backward"])

    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path)
    assert t.step == "2 (pr)"
    assert "rewound to step 2 (pr)" in _log_text(repo, slug)


def test_bump_rewind_rejects_invalid_current_step(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    t = Ticket.read(task_path)
    t.frontmatter["step"] = "99 (bogus)"
    t.write(task_path)

    result = CliRunner().invoke(app, ["bump", slug, "--backward"])

    assert result.exit_code == 2, result.output
    assert "invalid step '99 (bogus)'" in result.output
    t = Ticket.read(task_path)
    assert t.step == "99 (bogus)"


def test_bump_rejects_named_rewind_target(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    runner.invoke(app, ["bump", slug])

    result = runner.invoke(app, ["bump", slug, "--to", "implement"])

    assert result.exit_code == 2, result.output
    assert "Invalid value for '--to'" in result.output
    t = Ticket.read(task_path)
    assert t.step == "2 (pr)"


def test_bump_rejects_unknown_rewind_target(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    runner.invoke(app, ["bump", slug])

    result = runner.invoke(app, ["bump", slug, "--to", "99"])

    assert result.exit_code == 2, result.output
    assert "Unknown step 99" in result.output
    t = Ticket.read(task_path)
    assert t.step == "2 (pr)"


def test_bump_to_refuses_forward_skip(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()

    result = runner.invoke(app, ["bump", slug, "--to", "3"])

    assert result.exit_code == 2, result.output
    assert "Cannot skip ahead" in result.output
    t = Ticket.read(task_path)
    assert t.step == "1 (implement)"


def test_bump_rewind_refuses_supervised_agent(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    runner.invoke(app, ["bump", slug])

    result = runner.invoke(
        app,
        ["bump", slug, "--backward"],
        env={"COGA_SUPERVISED": "1"},
    )

    assert result.exit_code == 2, result.output
    assert "Agents cannot rewind" in result.output
    assert "coga block" in result.output
    t = Ticket.read(task_path)
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
    result = runner.invoke(app, ["bump", slug], env={"COGA_SUPERVISED": "1"})
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
    ref = create_task(
        cfg=cfg, title="W", workflow_name="peer",
        contexts=[],
        owner="marc", assignee="claude",
        human="marc", agent="claude",
        watchers=[], status="in_progress",
    )
    slug = ref["slug"]
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug], env={"COGA_SUPERVISED": "1"})
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
    result = runner.invoke(app, ["bump", slug], env={"COGA_SUPERVISED": "1"})
    assert result.exit_code == 0, result.output
    assert "Supervised launch" in result.output
    assert "spawn a fresh agent session" in result.output


def test_bump_unsupervised_prints_no_hint(repo: Path) -> None:
    slug, _ = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    assert "Supervised launch" not in result.output


def test_bump_supervised_refuses_stale_composed_step(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    ticket = Ticket.read(task_path)
    ticket.frontmatter["step"] = "2 (pr)"
    ticket.write(task_path)

    result = CliRunner().invoke(
        app,
        ["bump", slug],
        env={
            "COGA_SUPERVISED": "1",
            EXPECTED_TASK_ENV: str(task_path.resolve()),
            EXPECTED_STEP_ENV: "1 (implement)",
        },
    )

    assert result.exit_code == 2, result.output
    assert "Refusing to bump" in result.output
    assert "composed for step '1 (implement)'" in result.output
    assert "now on step '2 (pr)'" in result.output
    assert Ticket.read(task_path).step == "2 (pr)"


def test_bump_supervised_allows_unfrozen_workflow_without_step(repo: Path) -> None:
    legacy = repo / "tasks" / "legacy"
    legacy.mkdir(parents=True)
    ticket_path = legacy / "ticket.md"
    ticket_path.write_text(dedent(
        """
        ---
        slug: legacy
        title: Legacy
        status: in_progress
        owner: marc
        human: marc
        agent: claude
        assignee: claude
        contexts: []
        skills: []
        workflow: code
        ---

        <!-- coga:blackboard -->
        """
    ).lstrip())

    result = CliRunner().invoke(
        app,
        ["bump", "legacy"],
        env={
            "COGA_SUPERVISED": "1",
            EXPECTED_TASK_ENV: str(legacy.resolve()),
            EXPECTED_STEP_ENV: "",
        },
    )

    assert result.exit_code == 0, result.output
    assert Ticket.read(ticket_path).step == "2 (pr)"


def test_bump_past_final_step_errors_with_mark_done_hint(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    # Workflow has 3 steps; advance to the final step.
    runner.invoke(app, ["bump", slug])
    runner.invoke(app, ["bump", slug])
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 2, result.output
    assert "final step" in result.output
    assert f"coga mark done {slug}" in result.output
    # Ticket stays in progress — bump does not mark done.
    t = Ticket.read(task_path)
    assert t.status == "in_progress"


@pytest.mark.parametrize("status", ["paused", "canceled"])
def test_bump_rejects_non_in_progress(repo: Path, status: str) -> None:
    slug, _ = _make_task(repo, status=status)
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 2


def test_bump_no_workflow_errors_with_mark_done_hint(repo: Path) -> None:
    slug, task_path = _write_workflow_less_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 2, result.output
    assert "no workflow" in result.output
    assert f"coga mark done {slug}" in result.output
    t = Ticket.read(task_path)
    assert t.status == "in_progress"


# --- bump completion gate (`requires:`) --------------------------------------


def _set_step_requires(task_path: Path, step_idx0: int, token: object) -> None:
    """Add `requires: <token>` to the 0-based frozen workflow step."""
    t = Ticket.read(task_path)
    t.frontmatter["workflow"]["steps"][step_idx0]["requires"] = token
    t.write(task_path)


def _record_pr(task_path: Path, url: str) -> None:
    """Write a `## Dev` `pr:` line into the task blackboard.

    The blackboard region conventionally begins right after the fence, so it
    starts with a newline (matching `read_blackboard`'s output); without it the
    `## Dev` header would weld onto the fence line and break the fence match.
    """
    replace_blackboard(task_path, f"\n\n## Dev\npr: {url}\n")


def test_bump_gate_blocks_until_required_artifact_recorded(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    _set_step_requires(task_path, 0, "pr")  # gate the current `implement` step
    runner = CliRunner()

    # No `pr:` recorded → the bump is refused, the step does not move.
    blocked = runner.invoke(app, ["bump", slug])
    assert blocked.exit_code == 2, blocked.output
    assert "requires a recorded `pr`" in blocked.output
    assert f"coga open-pr {slug}" in blocked.output
    assert Ticket.read(task_path).step == "1 (implement)"

    # Record the artifact → the same bump now advances.
    _record_pr(task_path, "https://github.com/acme/repo/pull/5")
    allowed = runner.invoke(app, ["bump", slug])
    assert allowed.exit_code == 0, allowed.output
    assert Ticket.read(task_path).step == "2 (pr)"


def test_bump_rewind_ignores_requires_gate(repo: Path) -> None:
    """A human rewind is never gated — only forward advancement is."""
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    runner.invoke(app, ["bump", slug])  # 1 (implement) -> 2 (pr)
    _set_step_requires(task_path, 1, "pr")  # gate step 2, leave no `pr:` recorded

    result = runner.invoke(app, ["bump", slug, "--backward"])

    assert result.exit_code == 0, result.output
    assert Ticket.read(task_path).step == "1 (implement)"


def test_bump_gate_fails_loud_on_non_string_requires(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    _set_step_requires(task_path, 0, ["pr"])

    result = CliRunner().invoke(app, ["bump", slug])

    assert result.exit_code == 2, result.output
    assert "malformed `requires:" in result.output
    assert "must be strings" in result.output
    assert not isinstance(result.exception, TypeError)
    assert Ticket.read(task_path).step == "1 (implement)"


# --- block / unblock ----------------------------------------------------------


def test_block_writes_blocker_and_status(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["block", "--task", slug, "--reason", "unclear ceiling for 429 backoff"])
    assert result.exit_code == 0, result.output
    blackboard = read_blackboard(task_path)
    assert "unclear ceiling for 429 backoff" in blackboard
    assert "## Blockers" in blackboard
    ticket = Ticket.read(task_path)
    assert ticket.status == "blocked"
    assert ticket.step == "1 (implement)"
    assert "blocked:" in _log_text(repo, slug)


def test_unblock_records_answer_and_reactivates(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["block", "--task", slug, "--reason", "which retry ceiling?"])
    assert result.exit_code == 0, result.output

    result = runner.invoke(app, ["unblock", slug, "--answer", "cap at 5 minutes"])

    assert result.exit_code == 0, result.output
    ticket = Ticket.read(task_path)
    assert ticket.status == "active"
    assert ticket.step == "1 (implement)"
    blackboard = read_blackboard(task_path)
    assert "- [x]" in blackboard
    assert "cap at 5 minutes" in blackboard


def test_unblock_in_progress_resolves_asks_only(repo: Path) -> None:
    """An interactive blocked-launch session records its resolution while the
    ticket is already `in_progress` (launch reactivated it): the asks resolve,
    status and step stay untouched."""
    slug, task_path = _make_task(repo)
    append_blocker(task_path, "agent:claude", "which retry ceiling?")

    result = CliRunner().invoke(app, ["unblock", slug, "--answer", "cap at 5 minutes"])

    assert result.exit_code == 0, result.output
    ticket = Ticket.read(task_path)
    assert ticket.status == "in_progress"
    assert ticket.step == "1 (implement)"
    blackboard = read_blackboard(task_path)
    assert "- [x]" in blackboard
    assert "cap at 5 minutes" in blackboard
    assert "asks resolved, still in_progress" in _log_text(repo, slug)


def test_unblock_in_progress_without_asks_refuses(repo: Path) -> None:
    slug, _ = _make_task(repo)
    result = CliRunner().invoke(app, ["unblock", slug, "--answer", "nothing open"])
    assert result.exit_code == 2
    assert "no open blockers" in result.output


def test_unblock_refuses_other_statuses(repo: Path) -> None:
    slug, task_path = _make_task(repo, status="draft")
    append_blocker(task_path, "agent:claude", "which retry ceiling?")
    result = CliRunner().invoke(app, ["unblock", slug, "--answer", "cap it"])
    assert result.exit_code == 2
    assert "unblock requires" in result.output


def _make_named_task(repo: Path, title: str) -> tuple[str, Path]:
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg, title=title, workflow_name="code",
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status="in_progress",
    )
    return ref["slug"], ref["path"]


def test_unblock_all_walks_every_blocked_task(repo: Path) -> None:
    slug_a, path_a = _make_named_task(repo, "Alpha")
    slug_b, path_b = _make_named_task(repo, "Beta")
    runner = CliRunner()
    for slug in (slug_a, slug_b):
        r = runner.invoke(app, ["block", "--task", slug, "--reason", f"why {slug}?"])
        assert r.exit_code == 0, r.output

    # One answer per blocked task, in list order; same text so order is moot.
    result = runner.invoke(app, ["unblock", "--all"], input="do it\ndo it\n")

    assert result.exit_code == 0, result.output
    assert "Unblocked 2, skipped 0" in result.output
    for path in (path_a, path_b):
        ticket = Ticket.read(path)
        assert ticket.status == "active"
        blackboard = read_blackboard(path)
        assert "- [x]" in blackboard
        assert "do it" in blackboard


def test_unblock_all_blank_answer_skips(repo: Path) -> None:
    slug, path = _make_named_task(repo, "Gamma")
    runner = CliRunner()
    r = runner.invoke(app, ["block", "--task", slug, "--reason", "which ceiling?"])
    assert r.exit_code == 0, r.output

    result = runner.invoke(app, ["unblock", "--all"], input="\n")

    assert result.exit_code == 0, result.output
    assert "skipped" in result.output
    assert "Unblocked 0, skipped 1" in result.output
    # A skipped task stays blocked with its ask open.
    assert Ticket.read(path).status == "blocked"


def test_unblock_all_no_blocked_tasks(repo: Path) -> None:
    _make_named_task(repo, "Delta")  # active, not blocked
    result = CliRunner().invoke(app, ["unblock", "--all"])
    assert result.exit_code == 0, result.output
    assert "No blocked tasks." in result.output


def test_unblock_all_rejects_task_argument(repo: Path) -> None:
    slug, _ = _make_named_task(repo, "Epsilon")
    result = CliRunner().invoke(app, ["unblock", slug, "--all"])
    assert result.exit_code == 2
    assert "not both" in result.output


# --- delete -------------------------------------------------------------------


def test_delete_removes_task_directory(repo: Path) -> None:
    _install_delete_skill(repo)
    # The delete skill removes a task *directory*, so exercise it against a
    # directory-form task (its single implementation is `rmtree` of the dir).
    slug, task_path = _make_task(repo, force_directory=True)
    assert task_path.is_dir()
    runner = CliRunner()
    result = runner.invoke(app, ["delete", slug])
    assert result.exit_code == 0, result.output
    assert not task_path.exists()
    assert "deleted" in result.output


def test_delete_resolves_prefix(repo: Path) -> None:
    _install_delete_skill(repo)
    slug, task_path = _make_task(repo, force_directory=True)
    runner = CliRunner()
    result = runner.invoke(app, ["delete", slug[:6]])
    assert result.exit_code == 0, result.output
    assert not task_path.exists()


def test_delete_keep_control_checkout_refuses_primary(repo: Path) -> None:
    _install_delete_skill(repo)
    slug, task_path = _make_task(repo, force_directory=True)

    result = CliRunner().invoke(
        app, ["delete", slug, "--keep-control-checkout"]
    )

    assert result.exit_code == 2
    assert task_path.is_dir()
    assert "requires a linked git worktree" in result.output


def test_delete_unknown_task_exits_nonzero(repo: Path) -> None:
    # Unknown slug fails at resolution, before the skill is even consulted.
    runner = CliRunner()
    result = runner.invoke(app, ["delete", "no-such-task-xyz"])
    assert result.exit_code == 2


def test_delete_missing_skill_exits_nonzero(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The skill is the implementation; without it `coga delete` fails loud
    # rather than silently falling back to a private rmtree.
    slug, task_path = _make_task(repo, force_directory=True)
    monkeypatch.setattr("coga.delete_task.resolve_skill_path", lambda cfg, ref: None)
    result = CliRunner().invoke(app, ["delete", slug])
    assert result.exit_code == 2
    assert task_path.is_dir()
    assert "bootstrap/delete-task" in result.output


def test_delete_skill_runs_as_script_step(repo: Path) -> None:
    # The same skill `coga delete` dispatches into is independently
    # launchable: a `mode: script` task whose one step references it deletes
    # its own directory on `coga launch`.
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
    ref = create_task(
        cfg=cfg, title="Throwaway", workflow_name="delete-self",
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status="active", force_directory=True,
    )
    task_path = ref["path"]
    assert task_path.is_dir()

    result = CliRunner().invoke(app, ["launch", ref["slug"]])
    assert result.exit_code == 0, result.output
    assert not task_path.exists()


def _install_noop_script_skill(repo: Path) -> None:
    """A trivial `mode: script` skill: a no-op `run.sh` that exits 0."""
    skill_dir = repo / "skills" / "local" / "noop"
    _write(
        skill_dir / "SKILL.md",
        """
        ---
        name: local/noop
        description: No-op script step for tests.
        script: run.sh
        ---

        # Noop
        """,
    )
    (skill_dir / "run.sh").write_text("#!/bin/sh\nexit 0\n")


def test_script_mode_marks_done_after_final_step(repo: Path) -> None:
    """A successful script step on a single-step workflow finishes the task.

    Regression: `run_script_mode` ran the script and left the task at
    `in_progress`, so a recurring scan halted on it ("stopping before the next
    due task"). The launcher must apply the agent completion contract itself.
    """
    _install_noop_script_skill(repo)
    _write(
        repo / "workflows" / "flush-once.md",
        """
        ---
        name: flush-once
        description: One-step script workflow.
        steps:
          - name: flush
            skills:
              - local/noop
            assignee: agent
        ---
        """,
    )
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg, title="Daily flush", workflow_name="flush-once",
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status="active",
    )
    task_path = ref["path"]

    result = CliRunner().invoke(app, ["launch", ref["slug"]])
    assert result.exit_code == 0, result.output

    ticket = Ticket.read(task_path)
    assert ticket.status == "done"
    assert "script ran successfully" in result.output
    assert "done" in result.output


def test_script_mode_advances_to_next_step(repo: Path) -> None:
    """On a multi-step workflow a script step bumps to the next step, not done."""
    _install_noop_script_skill(repo)
    _write(
        repo / "workflows" / "flush-twice.md",
        """
        ---
        name: flush-twice
        description: Two-step script workflow.
        steps:
          - name: first
            skills:
              - local/noop
            assignee: agent
          - name: second
            skills:
              - local/noop
            assignee: agent
        ---
        """,
    )
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg, title="Two stage", workflow_name="flush-twice",
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status="active",
    )
    task_path = ref["path"]

    result = CliRunner().invoke(app, ["launch", ref["slug"]])
    assert result.exit_code == 0, result.output

    ticket = Ticket.read(task_path)
    assert ticket.status == "in_progress"
    assert ticket.step_index() == 2


# --- slack --------------------------------------------------------------------


def test_slack_logs(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["slack", "--task", slug, "--message", "opened PR #142"])
    assert result.exit_code == 0
    assert "slack: opened PR #142" in _log_text(repo, slug)


def test_slack_on_durable_task_does_not_complete_session(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug, _ = _make_task(repo)
    sentinel = repo / "task-session.done"
    monkeypatch.setenv(SENTINEL_ENV, str(sentinel))

    result = CliRunner().invoke(
        app, ["slack", "--task", slug, "--message", "still working"]
    )

    assert result.exit_code == 0, result.output
    assert not sentinel.exists()


def test_slack_accepts_and_completes_stateless_bootstrap_target(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A command ticket's final roll-up releases its stateless supervisor."""
    sentinel = repo / "bootstrap-command.done"
    monkeypatch.setenv(SENTINEL_ENV, str(sentinel))
    result = CliRunner().invoke(
        app,
        [
            "slack",
            "--task",
            "bootstrap/resolve-conflicts",
            "--message",
            "2 rebased-pushed; 1 conflict",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "slack: 2 rebased-pushed; 1 conflict" in _log_text(
        repo, "bootstrap/resolve-conflicts"
    )
    assert sentinel.read_text() == "bootstrap/resolve-conflicts\n"


def test_slack_important_forwards_to_notification_post(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug, _ = _make_task(repo)
    calls: list[dict] = []

    def fake_post(cfg, message, **kwargs):  # type: ignore[no-untyped-def]
        calls.append({"message": message, **kwargs})

    monkeypatch.setattr("coga.commands.slack.post", fake_post)

    result = CliRunner().invoke(
        app,
        ["slack", "--task", slug, "--message", "fee window closes", "--important"],
    )

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert calls[0]["important"] is True
    assert "fee window closes" in calls[0]["message"]


# --- bump --message -----------------------------------------------------------


def test_bump_message_appended_to_log(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["bump", slug, "--message", "PR opened: https://example/142"],
    )
    assert result.exit_code == 0, result.output
    log = _log_text(repo, slug)
    assert "advanced to step 2 (pr) — PR opened: https://example/142" in log


def test_mark_done_message_on_no_workflow(repo: Path) -> None:
    slug, task_path = _write_workflow_less_task(repo)
    runner = CliRunner()
    result = runner.invoke(
        app, ["mark", "done", slug, "--message", "talked to marc, scope ok"]
    )
    assert result.exit_code == 0, result.output
    log = _log_text(repo, slug)
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
    log = _log_text(repo, slug)
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
    ref = create_task(
        cfg=cfg, title="W", workflow_name="review",
        contexts=[],
        owner="marc", assignee="claude",
        human="marc", agent="claude",
        watchers=[], status="in_progress",
    )
    slug = ref["slug"]
    task_path = ref["path"]

    # Step 1 declared `assignee: agent` → resolved at create time.
    t = Ticket.read(task_path)
    assert t.assignee == "claude"

    # Bump into step 2 (assignee: human) → ticket.assignee = ticket.human.
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path)
    assert t.step == "2 (review)"
    assert t.assignee == "marc"
    log = _log_text(repo, slug)
    assert "→ assigned to marc" in log

    # Bump into step 3 (assignee: owner) → ticket.assignee = ticket.owner.
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path)
    assert t.assignee == "marc"  # owner == marc, no change → no handoff line
    log = _log_text(repo, slug)
    # Only one handoff line so far (the human→owner step is a no-op handoff).
    assert log.count("→ assigned to") == 1


def test_bump_no_assignee_declared_leaves_assignee_unchanged(repo: Path) -> None:
    # The default `code` workflow in this fixture has no assignee declarations.
    slug, task_path = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path)
    assert t.assignee == "claude"  # unchanged
    log = _log_text(repo, slug)
    assert "→ assigned to" not in log


def test_bump_role_token_with_missing_field_fails_loud(repo: Path) -> None:
    _write_assignee_workflow(repo)
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg, title="W", workflow_name="review",
        contexts=[],
        owner="marc", assignee="claude",
        human="marc", agent="claude",
        watchers=[], status="in_progress",
    )
    # Hand-edit the ticket to remove the `human` field, then bump into the
    # human step. Bump must refuse rather than silently skip.
    t = Ticket.read(ref["path"])
    del t.frontmatter["human"]
    t.write(ref["path"])

    runner = CliRunner()
    result = runner.invoke(app, ["bump", ref["slug"]])
    assert result.exit_code == 2, result.output
    assert "human" in result.output


def _add_codex_agent(repo: Path) -> None:
    """Append a second agent type so `other-agent` has a peer to resolve to."""
    toml = repo / "coga.toml"
    toml.write_text(
        toml.read_text()
        + dedent(
            """
            [agents.codex]
            cli = "codex"
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
    ref = create_task(
        cfg=cfg, title="W", workflow_name="peer",
        contexts=[],
        owner="marc", assignee="claude",
        human="marc", agent="claude",
        watchers=[], status="in_progress",
    )
    slug, task_path = ref["slug"], ref["path"]

    # Step 1 `assignee: agent` → the coder (claude).
    t = Ticket.read(task_path)
    assert t.assignee == "claude"

    # Bump into peer-review (`assignee: other-agent`) → codex, the agent
    # that is not the ticket's `agent: claude`.
    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path)
    assert t.step == "2 (peer-review)"
    assert t.assignee == "codex"
    assert "→ assigned to codex" in _log_text(repo, slug)


def test_bump_rewind_resolves_target_step_assignee(repo: Path) -> None:
    _add_codex_agent(repo)
    _write_peer_review_workflow(repo)
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg, title="W", workflow_name="peer",
        contexts=[],
        owner="marc", assignee="claude",
        human="marc", agent="claude",
        watchers=[], status="in_progress",
    )
    slug, task_path = ref["slug"], ref["path"]

    runner = CliRunner()
    result = runner.invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path)
    assert t.step == "2 (peer-review)"
    assert t.assignee == "codex"

    result = runner.invoke(app, ["bump", slug, "--to", "1"])
    assert result.exit_code == 0, result.output
    t = Ticket.read(task_path)
    assert t.step == "1 (implement)"
    assert t.assignee == "claude"
    log = _log_text(repo, slug)
    assert "rewound to step 1 (implement) → assigned to claude" in log


def test_other_agent_flips_with_the_coder(repo: Path) -> None:
    # A change written by codex is peer-reviewed by claude — the token is
    # relative to the ticket's own `agent:`, not hard-coded.
    _add_codex_agent(repo)
    _write_peer_review_workflow(repo)
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg, title="W", workflow_name="peer",
        contexts=[],
        owner="marc", assignee="codex",
        human="marc", agent="codex",
        watchers=[], status="in_progress",
    )
    runner = CliRunner()
    result = runner.invoke(app, ["bump", ref["slug"]])
    assert result.exit_code == 0, result.output
    t = Ticket.read(ref["path"])
    assert t.assignee == "claude"


def test_other_agent_step_one_resolves_at_create_time(repo: Path) -> None:
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
    ref = create_task(
        cfg=cfg, title="W", workflow_name="peer-first",
        contexts=[],
        owner="marc", assignee="claude",
        human="marc", agent="claude",
        watchers=[], status="in_progress",
    )
    t = Ticket.read(ref["path"])
    assert t.assignee == "codex"


def test_other_agent_fails_loud_without_exactly_two_agents(repo: Path) -> None:
    # The base fixture configures only `claude`, so there is no peer to pick.
    _write_peer_review_workflow(repo)
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg, title="W", workflow_name="peer",
        contexts=[],
        owner="marc", assignee="claude",
        human="marc", agent="claude",
        watchers=[], status="in_progress",
    )
    runner = CliRunner()
    result = runner.invoke(app, ["bump", ref["slug"]])
    assert result.exit_code == 2, result.output
    assert "other-agent" in result.output
    # assignee must not have changed on the failed bump.
    t = Ticket.read(ref["path"])
    assert t.assignee == "claude"
    assert t.step == "1 (implement)"


def test_bump_freezes_bare_string_workflow_then_advances(repo: Path) -> None:
    # Hand-authored ticket: `workflow:` is a bare string ref, no `step:`.
    legacy = repo / "tasks" / "legacy"
    legacy.mkdir(parents=True)
    (legacy / "ticket.md").write_text(dedent(
        """
        ---
        slug: legacy
        title: Legacy
        status: in_progress
        owner: marc
        human: marc
        agent: claude
        assignee: claude
        contexts: []
        skills: []
        workflow: code
        ---

        <!-- coga:blackboard -->
        """
    ).lstrip())

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
    ref = create_task(
        cfg=cfg, title="W", workflow_name="review",
        contexts=[],
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
    from coga.logfile import append_log
    from coga.taskfile import upsert_blackboard

    slug, task_path = _make_task(repo)
    # Blackboard now lives inside ticket.md; history lives in the global log.
    upsert_blackboard(task_path, "# Plan\n\nfigure it out\n")
    append_log(load_config(repo), slug, "system", "created task")
    runner = CliRunner()
    result = runner.invoke(app, ["show", slug])
    assert result.exit_code == 0, result.output
    # The single-file ticket section, the blackboard content folded into it,
    # and the reconstructed log history all show.
    assert "ticket.md" in result.output
    assert "log" in result.output
    assert "figure it out" in result.output
    assert "created task" in result.output


def test_show_resolves_prefix(repo: Path) -> None:
    slug, _ = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["show", slug[:6]])
    assert result.exit_code == 0, result.output
    assert "ticket.md" in result.output


def test_show_handles_missing_blackboard_and_log(repo: Path) -> None:
    from coga.taskfile import replace_blackboard

    slug, task_path = _make_task(repo)
    # Empty the blackboard region and drop the global log entirely, so the task
    # has no blackboard content and no reconstructable history.
    replace_blackboard(task_path, "")
    log_path(load_config(repo)).unlink(missing_ok=True)
    runner = CliRunner()
    result = runner.invoke(app, ["show", slug])
    assert result.exit_code == 0, result.output
    # Ticket still renders; the log section reports no reconstructable history.
    assert "ticket.md" in result.output
    assert "no log entries" in result.output


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


def test_status_blocked_expands_open_blockers(repo: Path) -> None:
    slug, _ = _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["block", "--task", slug, "--reason", "pick retry ceiling"])
    assert result.exit_code == 0, result.output

    result = runner.invoke(app, ["status", "--blocked"], env={"COLUMNS": "200"})

    assert result.exit_code == 0, result.output
    assert slug in result.output
    assert "blocked" in result.output
    assert "pick retry ceiling" in result.output
    # The unblock command is a shared footer with a <slug> placeholder now,
    # not a repeated per-row column.
    assert 'coga unblock <slug> --answer "..."' in result.output


def test_status_narrow_terminal_keeps_each_task_on_one_line(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="anything", workflow_name="code",
        contexts=[], owner="marc", assignee="claude",
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


def _write_recurring_template(repo: Path, name: str = "foo") -> None:
    _write(
        repo / "recurring" / name / "ticket.md",
        """
        ---
        schedule: "0 9 * * 1"
        ---

        ## Description
        Weekly job.

        <!-- coga:blackboard -->
        """,
    )


def test_status_renders_recurring_tasks_as_normal_rows(repo: Path) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Normal", workflow_name="code", contexts=[],
        owner="marc", assignee="claude",
        watchers=[], status="active", slug_override="normal-task",
    )
    create_task(
        cfg=cfg, title="Recurring", workflow_name="code", contexts=[],
        owner="marc", assignee="claude",
        watchers=[], status="active", slug_override="recurring/foo",
    )
    _write_recurring_template(repo, "foo")
    result = CliRunner().invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    out = result.output
    # Instantiated period tasks are ordinary tasks: both rows share the main
    # table (and its summary), before the "Recurring" templates footer.
    footer_at = out.index("Recurring")
    assert out.index("recurring/foo") < footer_at
    assert out.index("normal-task") < footer_at
    assert "2 tasks" in out
    # The footer lists the template with its schedule and current-period state.
    footer = out[footer_at:]
    assert "0 9 * * 1" in footer
    assert "active" in footer


def test_status_shows_templates_even_without_instantiated_tasks(repo: Path) -> None:
    _write_recurring_template(repo, "foo")
    result = CliRunner().invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    # No tasks on disk at all — the templates footer still renders, so a
    # steady-state repo (all period tasks done or not yet created) keeps its
    # recurring schedule visible in the triage view.
    assert "(no tasks)" in result.output
    assert "Recurring" in result.output
    assert "due — not created" in result.output


def test_status_hides_templates_footer_outside_recurring_scope(repo: Path) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Other", workflow_name="code", contexts=[],
        owner="marc", assignee="claude",
        watchers=[], status="active", slug_override="marketing/other",
    )
    _write_recurring_template(repo, "foo")
    result = CliRunner().invoke(app, ["status", "marketing"])
    assert result.exit_code == 0, result.output
    assert "Recurring" not in result.output
    no_recurse = CliRunner().invoke(app, ["status", "--no-recurse"])
    assert no_recurse.exit_code == 0, no_recurse.output
    assert "Recurring" not in no_recurse.output


def test_status_does_not_show_title_column(repo: Path) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="A distinctive ticket title", workflow_name="code",
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status="active", slug_override="t1",
    )
    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    assert "A distinctive ticket title" not in result.output
    assert "title" not in result.output.lower().split()


# --- validate -----------------------------------------------------------------


def test_validate_clean_repo_succeeds(repo: Path) -> None:
    _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0, result.output
    assert "All good" in result.output


def test_validate_json_emits_payload(repo: Path) -> None:
    _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["validate", "--json"])
    assert result.exit_code == 0, result.output
    import json
    payload = json.loads(result.output)
    assert payload["fixes"] == []
    assert payload["issues"] == []
    assert payload["ok_count"] == 1


def test_validate_fix_json_repairs_missing_workspace_file(repo: Path) -> None:
    from coga.taskfile import fence_count

    _, task_path = _make_task(repo)
    # Single-file equivalent of a missing workspace file: a ticket.md whose
    # blackboard fence is gone. The safe fix re-appends the fence + region.
    ticket_path = task_path
    text = ticket_path.read_text()
    above, _, _ = text.partition("\n<!-- coga:blackboard -->")
    ticket_path.write_text(above + "\n")
    assert fence_count(ticket_path.read_text()) == 0

    runner = CliRunner()
    result = runner.invoke(app, ["validate", "--fix", "--json"])

    assert result.exit_code == 0, result.output
    import json
    payload = json.loads(result.output)
    assert payload["fixes"][0]["message"] == "added blackboard fence + region"
    assert payload["issues"] == []
    assert fence_count(ticket_path.read_text()) == 1


def test_validate_warns_for_large_blackboard(repo: Path) -> None:
    from coga.taskfile import replace_blackboard

    _, task_path = _make_task(repo)
    # The blackboard region now lives inside ticket.md; inflate it there. The
    # region keeps its leading newlines so the fence stays on its own line.
    replace_blackboard(task_path, "\n\n" + "x" * 2048 + "\n")

    runner = CliRunner()
    result = runner.invoke(app, ["validate", "--max-blackboard-kb", "1"])
    assert result.exit_code == 0, result.output
    assert "[WARN]" in result.output
    assert "large-blackboard" in result.output


def test_status_shows_done_tasks_with_all(repo: Path) -> None:
    slug, task_path = _make_task(repo)
    # Mark done directly
    t = Ticket.read(task_path)
    t.frontmatter["status"] = "done"
    t.write(task_path)
    runner = CliRunner()
    # Done is hidden by default; --all reveals it.
    assert slug not in runner.invoke(app, ["status"]).output
    result = runner.invoke(app, ["status", "--all"])
    assert result.exit_code == 0, result.output
    assert slug in result.output


def test_status_hides_done_by_default_without_deleting(repo: Path) -> None:
    cfg = load_config(repo)
    active = create_task(
        cfg=cfg, title="Active", workflow_name="code", contexts=[],
        owner="marc", assignee="claude",
        watchers=[], status="active", slug_override="active-task",
    )
    done = create_task(
        cfg=cfg, title="Finished", workflow_name="code", contexts=[],
        owner="marc", assignee="claude",
        watchers=[], status="done", slug_override="finished-task",
    )
    runner = CliRunner()

    result = runner.invoke(app, ["status", "--order-by", "slug"])

    assert result.exit_code == 0, result.output
    assert active["slug"] in result.output
    assert done["slug"] not in result.output
    assert "1 task  ·  1 active" in result.output
    # Hidden, not deleted — the task file survives and a hint points at --all.
    assert done["path"].is_file()
    assert "1 done task hidden — use --all to show" in result.output


def test_status_all_includes_done_tasks(repo: Path) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Finished", workflow_name="code", contexts=[],
        owner="marc", assignee="claude",
        watchers=[], status="done", slug_override="finished-task",
    )

    result = CliRunner().invoke(app, ["status", "--all"])

    assert result.exit_code == 0, result.output
    assert "finished-task" in result.output


def test_status_hides_canceled_by_default_and_all_reports_terminal_totals(
    repo: Path,
) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg, title="Active", workflow_name="code", contexts=[],
        owner="marc", assignee="claude", watchers=[], status="active",
        slug_override="active-task",
    )
    done = create_task(
        cfg=cfg, title="Finished", workflow_name="code", contexts=[],
        owner="marc", assignee="claude", watchers=[], status="done",
        slug_override="finished-task",
    )
    canceled = create_task(
        cfg=cfg, title="Declined", workflow_name="code", contexts=[],
        owner="marc", assignee="claude", watchers=[], status="canceled",
        slug_override="declined-task",
    )
    runner = CliRunner()

    default = runner.invoke(app, ["status", "--order-by", "slug"])

    assert default.exit_code == 0, default.output
    assert done["slug"] not in default.output
    assert canceled["slug"] not in default.output
    assert (
        "2 terminal tasks hidden: 1 done, 1 canceled — use --all to show"
        in default.output
    )

    all_tasks = runner.invoke(app, ["status", "--all", "--order-by", "slug"])

    assert all_tasks.exit_code == 0, all_tasks.output
    assert done["slug"] in all_tasks.output
    assert canceled["slug"] in all_tasks.output
    assert "3 tasks  ·  1 active · 1 done · 1 canceled" in all_tasks.output


# --- status --order-by / --reverse / updated column ---------------------------


def _set_log_timestamp(repo: Path, slug: str, when: str) -> None:
    """Append one line for `slug` to the repo-global log at the given timestamp.

    Activity time now comes from the last line tagged with the task's ref in
    `coga/log.md`. Appending after the `created` line makes this the task's
    most-recent line, so it drives the `updated` column / ordering.
    """
    path = log_path(load_config(repo))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(f"{when} [{slug}] [system] backdated\n")


def test_status_includes_updated_column(repo: Path) -> None:
    _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    assert "updated" in result.output


def test_status_default_orders_by_updated_desc(repo: Path) -> None:
    cfg = load_config(repo)
    older = create_task(
        cfg=cfg, title="older", workflow_name="code",
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status="active", slug_override="aaa-old",
    )
    newer = create_task(
        cfg=cfg, title="newer", workflow_name="code",
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status="active", slug_override="zzz-new",
    )
    _set_log_timestamp(repo, older["slug"], "2026-01-01 09:00")
    _set_log_timestamp(repo, newer["slug"], "2026-04-30 17:00")

    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    new_idx = result.output.index("zzz-new")
    old_idx = result.output.index("aaa-old")
    assert new_idx < old_idx, result.output


def test_status_order_by_slug_is_alphabetical(repo: Path) -> None:
    cfg = load_config(repo)
    for slug in ("zeta", "alpha", "mu"):
        create_task(
            cfg=cfg, title=slug, workflow_name="code",
            contexts=[], owner="marc", assignee="claude",
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
        create_task(
            cfg=cfg, title=slug, workflow_name="code",
            contexts=[], owner="marc", assignee="claude",
            watchers=[], status="active", slug_override=slug,
        )
    runner = CliRunner()
    result = runner.invoke(app, ["status", "--order-by", "slug", "--reverse"])
    assert result.exit_code == 0, result.output
    assert result.output.index("zeta") < result.output.index("alpha"), result.output


def test_status_rejects_unknown_order_by(repo: Path) -> None:
    _make_task(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["status", "--order-by", "bogus"])
    assert result.exit_code == 2


def test_status_tasks_without_log_sort_to_end(repo: Path) -> None:
    cfg = load_config(repo)
    has_log = create_task(
        cfg=cfg, title="logged", workflow_name="code",
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status="active", slug_override="zzz-logged",
    )
    no_log = create_task(
        cfg=cfg, title="no log", workflow_name="code",
        contexts=[], owner="marc", assignee="claude",
        watchers=[], status="active", slug_override="aaa-nolog",
    )
    _set_log_timestamp(repo, has_log["slug"], "2026-04-30 17:00")
    # Strip every global-log line tagged for the no-log task, so it has no
    # reconstructable activity at all (the single-file analogue of a missing
    # per-task log.md).
    path = log_path(cfg)
    kept = [
        line
        for line in path.read_text().splitlines()
        if f"[{no_log['slug']}]" not in line
    ]
    path.write_text("\n".join(kept) + ("\n" if kept else ""))

    runner = CliRunner()
    # Default order (updated desc) — logged task on top, no-log task at bottom.
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    assert result.output.index("zzz-logged") < result.output.index("aaa-nolog")

    # Even with --reverse, missing log stays at the bottom.
    result = runner.invoke(app, ["status", "--reverse"])
    assert result.exit_code == 0, result.output
    assert result.output.index("zzz-logged") < result.output.index("aaa-nolog")
