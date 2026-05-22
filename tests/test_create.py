from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from typer.testing import CliRunner

from relay.cli import app
from relay.scaffold import scaffold_task
from relay.config import load_config
from relay.ticket import Ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    company = tmp_path / "relay-os"
    company.mkdir()

    _write(
        company / "relay.toml",
        """
        version = 1
        default_status = "draft"

        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        mode = "local"

        """,
    )
    _write(company / "relay.local.toml", 'user = "marc"\n')

    _write(
        company / "workflows" / "code" / "with-review.md",
        """
        ---
        name: code/with-review
        description: Standard code workflow.
        steps:
          - name: implement
            skills:
              - infra/testing-conventions
          - name: pr
          - name: merge
        ---

        ## pr
        Open a PR.

        ## merge
        Merge and clean up.
        """,
    )
    _write(company / "skills" / "infra" / "testing-conventions" / "SKILL.md", "---\nname: x\n---\n")
    _write(company / "contexts" / "email" / "payment-flow" / "SKILL.md", "---\nname: x\n---\n")
    return company


def test_create_minimal(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo)
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg,
        title="Fix retry logic",
        workflow_name=None,
        contexts=[],
        mode="interactive",
        owner=None,
        assignee=None,
        watchers=[],
        status=None,
    )
    assert ref["slug"] == "fix-retry-logic"
    task_dir = ref["path"]
    assert (task_dir / "ticket.md").is_file()
    assert (task_dir / "blackboard.md").is_file()
    assert (task_dir / "log.md").is_file()
    ticket = Ticket.read(task_dir / "ticket.md")
    assert ticket.title == "Fix retry logic"
    assert ticket.status == "draft"
    assert ticket.mode == "interactive"
    assert ticket.owner == "marc"
    assert ticket.assignee == "marc"
    # Auto-populated role fields: human ← owner, agent ← owner's lone configured agent.
    assert ticket.human == "marc"
    assert ticket.agent == "claude"
    assert ticket.workflow is None


def test_create_uses_first_configured_agent_for_multi_agent_owner(repo: Path) -> None:
    _write(
        repo / "relay.toml",
        """
        version = 1
        default_status = "draft"

        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        mode = "local"

        [agents.codex]
        cli = "codex"
        auto = "exec"
        file = "AGENTS.md"
        mode = "local"

        """,
    )
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg,
        title="Try me",
        workflow_name=None,
        contexts=[],
        mode="interactive",
        owner=None,
        assignee=None,
        watchers=[],
        status=None,
    )
    ticket = Ticket.read(ref["path"] / "ticket.md")
    assert ticket.human == "marc"
    assert ticket.agent == "claude"


def test_create_requires_agent_before_writing_task_dir(repo: Path) -> None:
    _write(
        repo / "relay.toml",
        """
        version = 1
        default_status = "draft"
        """,
    )
    cfg = load_config(repo)
    with pytest.raises(ValueError, match="No default agent configured"):
        scaffold_task(
            cfg=cfg,
            title="No agent",
            workflow_name=None,
            contexts=[],
            mode="interactive",
            owner=None,
            assignee=None,
            watchers=[],
            status=None,
        )

    assert not (repo / "tasks" / "no-agent").exists()


def test_create_initial_assignee_resolved_from_workflow_step(repo: Path) -> None:
    _write(
        repo / "workflows" / "review.md",
        """
        ---
        name: review
        steps:
          - name: implement
            assignee: agent
          - name: review
            assignee: human
        ---
        """,
    )
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg, title="W", workflow_name="review",
        contexts=[], mode="interactive",
        owner="marc", assignee=None,
        watchers=[], status="active",
    )
    ticket = Ticket.read(ref["path"] / "ticket.md")
    # Step 1 declares `assignee: agent` → resolves to `marc`'s configured agent.
    assert ticket.assignee == "claude"


def test_create_explicit_human_and_agent_overrides_defaults(repo: Path) -> None:
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=[], mode="interactive",
        owner="marc", assignee=None,
        human="alice", agent="claude2",
        watchers=[], status="draft",
    )
    ticket = Ticket.read(ref["path"] / "ticket.md")
    assert ticket.human == "alice"
    assert ticket.agent == "claude2"


# --- retrofit ----------------------------------------------------------------


def test_backfill_role_fields_adds_human_and_agent(repo: Path) -> None:
    from relay.retrofit import backfill_role_fields

    # Seed a legacy ticket without `human:` / `agent:`.
    legacy = repo / "tasks" / "legacy"
    legacy.mkdir(parents=True)
    (legacy / "ticket.md").write_text(dedent(
        """
        ---
        title: Legacy
        status: active
        mode: interactive
        owner: marc
        assignee: claude
        ---

        ## Description
        old.
        """
    ).lstrip())
    (legacy / "blackboard.md").write_text("")
    (legacy / "log.md").write_text("")

    cfg = load_config(repo)
    rewritten = backfill_role_fields(cfg)
    assert rewritten == ["legacy"]
    t = Ticket.read(legacy / "ticket.md")
    assert t.human == "marc"
    assert t.agent == "claude"  # detected from assignee being a known agent nick

    # Idempotent: second run does nothing.
    assert backfill_role_fields(cfg) == []


def test_backfill_uses_owner_lone_agent_when_assignee_unknown(repo: Path) -> None:
    from relay.retrofit import backfill_role_fields

    legacy = repo / "tasks" / "legacy2"
    legacy.mkdir(parents=True)
    (legacy / "ticket.md").write_text(dedent(
        """
        ---
        title: Legacy2
        status: active
        owner: marc
        assignee: marc
        ---
        """
    ).lstrip())
    (legacy / "blackboard.md").write_text("")
    (legacy / "log.md").write_text("")

    cfg = load_config(repo)
    backfill_role_fields(cfg)
    t = Ticket.read(legacy / "ticket.md")
    assert t.human == "marc"
    # Assignee `marc` isn't an agent type, so fall back to the first declared agent.
    assert t.agent == "claude"


def test_backfill_freezes_legacy_workflow_and_fills_assignee(repo: Path) -> None:
    from relay.retrofit import backfill_role_fields
    from relay.tasks import TaskRef
    from relay.validate import validate_task_dir

    legacy = repo / "tasks" / "legacy3"
    legacy.mkdir(parents=True)
    (legacy / "ticket.md").write_text(dedent(
        """
        ---
        title: Legacy3
        status: active
        mode: interactive
        owner: zach
        workflow: code/with-review
        step: 2 (pr)
        ---
        """
    ).lstrip())
    (legacy / "blackboard.md").write_text("")
    (legacy / "log.md").write_text("")

    cfg = load_config(repo)
    assert backfill_role_fields(cfg) == ["legacy3"]
    t = Ticket.read(legacy / "ticket.md")
    assert t.human == "zach"
    assert t.agent == "claude"  # current user's default when owner is unknown.
    assert t.assignee == "zach"
    assert t.workflow["name"] == "code/with-review"
    assert t.workflow["steps"][0] == {
        "name": "implement",
        "skills": ["infra/testing-conventions"],
    }

    errors = [
        issue for issue in validate_task_dir(cfg, TaskRef(slug="legacy3", path=legacy))
        if issue.severity == "error"
    ]
    assert errors == []


def test_create_with_workflow_and_contexts(repo: Path) -> None:
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg,
        title="Task A",
        workflow_name="code/with-review",
        contexts=["email/payment-flow", "email/payment-flow"],  # dupe ignored
        mode="auto",
        owner="marc",
        assignee="claude",
        watchers=["pierre"],
        status="active",
    )
    ticket = Ticket.read(ref["path"] / "ticket.md")
    assert ticket.contexts == ["email/payment-flow"]
    assert ticket.workflow["name"] == "code/with-review"
    assert ticket.step == "1 (implement)"
    assert ticket.frontmatter["watchers"] == ["pierre"]


def test_create_rejects_unknown_context(repo: Path) -> None:
    cfg = load_config(repo)
    with pytest.raises(ValueError, match="Unknown contexts"):
        scaffold_task(
            cfg=cfg,
            title="X",
            workflow_name=None,
            contexts=["does/not/exist"],
            mode="interactive",
            owner=None,
            assignee=None,
            watchers=[],
            status=None,
        )


def test_create_distinct_titles_get_distinct_slugs(repo: Path) -> None:
    cfg = load_config(repo)
    refs = [
        scaffold_task(
            cfg=cfg,
            title=f"Task {i}",
            workflow_name=None,
            contexts=[],
            mode="interactive",
            owner=None,
            assignee=None,
            watchers=[],
            status=None,
        )
        for i in range(3)
    ]
    assert [r["slug"] for r in refs] == ["task-0", "task-1", "task-2"]


def test_create_collision_auto_suffixes(repo: Path) -> None:
    """Two tasks with the same title should not clash — second gets `-2`."""
    cfg = load_config(repo)
    kwargs = dict(
        cfg=cfg,
        workflow_name=None,
        contexts=[],
        mode="interactive",
        owner=None,
        assignee=None,
        watchers=[],
        status=None,
    )
    a = scaffold_task(title="Same title", **kwargs)
    b = scaffold_task(title="Same title", **kwargs)
    c = scaffold_task(title="Same title", **kwargs)
    assert a["slug"] == "same-title"
    assert b["slug"] == "same-title-2"
    assert c["slug"] == "same-title-3"


def test_create_log_entry_written(repo: Path) -> None:
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg,
        title="X",
        workflow_name=None,
        contexts=[],
        mode="interactive",
        owner=None,
        assignee=None,
        watchers=[],
        status=None,
    )
    log = (ref["path"] / "log.md").read_text()
    assert "[human:marc] created" in log


@pytest.fixture
def repo_with_shim(repo: Path) -> Path:
    """Same fixture as `repo`, plus the bootstrap/ticket shim + skill."""
    _write(
        repo / "bootstrap" / "ticket" / "ticket.md",
        """
        ---
        title: Create a new ticket
        mode: interactive
        skills:
          - bootstrap/ticket
        assignee: claude
        ---

        ## Description

        Persistent launch shim.
        """,
    )
    _write(
        repo / "skills" / "bootstrap" / "ticket" / "SKILL.md",
        """
        ---
        name: bootstrap/ticket
        description: Author a Relay task.
        ---

        Interview, fill in the ticket. Stop.
        """,
    )
    return repo


def test_recurring_scaffolds_and_broadcasts(
    repo_with_shim: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bare `relay recurring` scans templates, scaffolds due tasks, broadcasts."""
    _write(
        repo_with_shim / "recurring" / "weekly-check.md",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly deliverability check"
        mode: interactive
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the diagnostic suite.
        """,
    )
    monkeypatch.chdir(repo_with_shim)

    slack_msgs: list[str] = []

    def _capture(url, json=None, timeout=None):
        slack_msgs.append(json["text"])
        class R:
            status_code = 200
            text = "ok"
        return R()

    monkeypatch.setattr("relay.slack.requests.post", _capture)
    # The bare scan launches due tasks sequentially — stub the launch out.
    monkeypatch.setattr("relay.commands.launch.launch", lambda *a, **k: None)

    runner = CliRunner()
    result = runner.invoke(app, ["recurring"])
    assert result.exit_code == 0, result.output
    assert "Created" in result.output

    cfg = load_config(repo_with_shim)
    assert any(
        "recurring scaffolded" in m
        and "assignee" in m
        and cfg.project_name in m
        for m in slack_msgs
    )


def test_recurring_posts_error_summary(
    repo_with_shim: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A broken template surfaces as a Slack summary, not just stderr."""
    _write(repo_with_shim / "recurring" / "broken.md", "no frontmatter here\n")
    monkeypatch.chdir(repo_with_shim)

    slack_msgs: list[str] = []

    def _capture(url, json=None, timeout=None):
        slack_msgs.append(json["text"])
        class R:
            status_code = 200
            text = "ok"
        return R()

    monkeypatch.setattr("relay.slack.requests.post", _capture)

    runner = CliRunner()
    result = runner.invoke(app, ["recurring"])
    assert result.exit_code == 0, result.output
    assert any("skipped 1 template" in m and "broken.md" in m for m in slack_msgs)
    # Path duplication regression: the bullet should NOT contain the full file path.
    assert not any(str(repo_with_shim) in m for m in slack_msgs)


# --- `relay draft` / legacy `relay create` CLI --------------------------------


def test_cli_draft_scaffolds_draft_and_posts(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`relay draft "<title>"` scaffolds a raw draft ticket and posts ✨."""
    monkeypatch.chdir(repo)
    posts: list[str] = []

    def _capture(url, json=None, timeout=None):
        posts.append(json["text"])
        class R:
            status_code = 200
            text = "ok"
        return R()

    monkeypatch.setattr("relay.slack.requests.post", _capture)

    runner = CliRunner()
    result = runner.invoke(
        app, ["draft", "Investigate retries", "--workflow", "code/with-review"]
    )
    assert result.exit_code == 0, result.output

    cfg = load_config(repo)
    task_dir = repo / "tasks" / "investigate-retries"
    assert task_dir.is_dir()
    t = Ticket.read(task_dir / "ticket.md")
    assert t.title == "Investigate retries"
    assert t.status == "draft"
    assert t.mode == "interactive"

    assert any(
        f"✨ {cfg.current_user} created *investigate-retries*" in m
        and "Investigate retries" in m
        and cfg.project_name in m
        for m in posts
    )


def test_cli_create_scaffolds_draft_and_posts(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`relay create "<title>"` scaffolds a draft ticket and posts ✨."""
    monkeypatch.chdir(repo)
    posts: list[str] = []

    def _capture(url, json=None, timeout=None):
        posts.append(json["text"])
        class R:
            status_code = 200
            text = "ok"
        return R()

    monkeypatch.setattr("relay.slack.requests.post", _capture)

    runner = CliRunner()
    result = runner.invoke(
        app, ["create", "Investigate retries", "--workflow", "code/with-review"]
    )
    assert result.exit_code == 0, result.output

    cfg = load_config(repo)
    task_dir = repo / "tasks" / "investigate-retries"
    assert task_dir.is_dir()
    t = Ticket.read(task_dir / "ticket.md")
    assert t.title == "Investigate retries"
    assert t.status == "draft"
    assert t.mode == "interactive"

    assert any(
        f"✨ {cfg.current_user} created *investigate-retries*" in m
        and "Investigate retries" in m
        and cfg.project_name in m
        for m in posts
    )


def test_cli_create_does_not_spawn_agent(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`relay create` only scaffolds; it never spawns an agent."""
    monkeypatch.chdir(repo)
    called = False

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        nonlocal called
        called = True
        class R: returncode = 0
        return R()

    monkeypatch.setattr("relay.commands.launch.subprocess.run", fake_run, raising=False)

    runner = CliRunner()
    result = runner.invoke(
        app, ["create", "Just a draft", "--workflow", "code/with-review"]
    )
    assert result.exit_code == 0, result.output
    assert not called


def test_cli_create_mode_option(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo)
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["create", "Auto job", "--mode", "auto", "--workflow", "code/with-review"],
    )
    assert result.exit_code == 0, result.output
    t = Ticket.read(repo / "tasks" / "auto-job" / "ticket.md")
    assert t.mode == "auto"


def test_cli_create_rejects_empty_title(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["create", "   "])
    assert result.exit_code == 2


# --- workflow always required ------------------------------------------------


def test_cli_create_workflow_flag_attaches_workflow(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`relay create --workflow <name>` attaches the workflow to the draft."""
    monkeypatch.chdir(repo)
    monkeypatch.setattr(
        "relay.slack.requests.post",
        lambda *a, **kw: type("R", (), {"status_code": 200, "text": "ok"})(),
    )
    runner = CliRunner()
    result = runner.invoke(
        app, ["create", "With workflow", "--workflow", "code/with-review"]
    )
    assert result.exit_code == 0, result.output
    t = Ticket.read(repo / "tasks" / "with-workflow" / "ticket.md")
    assert t.workflow is not None
    assert t.workflow["name"] == "code/with-review"
    assert t.step == "1 (implement)"


def test_cli_create_allows_no_workflow(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`relay create` without `--workflow` scaffolds a workflow-less draft.

    `--workflow` is optional; `relay mark active` is the gate that refuses to
    activate a workflow-less ticket.
    """
    monkeypatch.chdir(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["create", "No workflow"])
    assert result.exit_code == 0, result.output
    t = Ticket.read(repo / "tasks" / "no-workflow" / "ticket.md")
    assert t.workflow is None
    assert t.status == "draft"


def test_cli_draft_allows_no_workflow(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`relay draft` also allows a workflow-less draft."""
    monkeypatch.chdir(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["draft", "Still no workflow"])
    assert result.exit_code == 0, result.output
    t = Ticket.read(repo / "tasks" / "still-no-workflow" / "ticket.md")
    assert t.workflow is None


def test_scaffold_draft_without_workflow(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`scaffold_draft` with no workflow produces a workflow-less draft."""
    from relay.commands.create import scaffold_draft

    monkeypatch.chdir(repo)
    monkeypatch.setattr(
        "relay.slack.requests.post",
        lambda *a, **kw: type("R", (), {"status_code": 200, "text": "ok"})(),
    )
    result = scaffold_draft(title="Interview start", mode="interactive")
    t = Ticket.read(result["path"] / "ticket.md")
    assert t.workflow is None


# --- ticket frontmatter extensions ------------------------------------------


def test_scaffold_writes_declared_extension_fields(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + (
            "\n[ticket.fields.docket]\n"
            'description = "USPTO docket"\n'
            "\n[ticket.fields.priority]\n"
            'description = "triage"\n'
            'values = ["P0", "P1", "P2"]\n'
            'default = "P2"\n'
        )
    )
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg,
        title="With extensions",
        workflow_name=None,
        contexts=[],
        mode="interactive",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="draft",
    )
    t = Ticket.read(ref["path"] / "ticket.md")
    assert t.frontmatter["docket"] == ""
    assert t.frontmatter["priority"] == "P2"

    raw = (ref["path"] / "ticket.md").read_text()
    assert "# --- extensions ---" in raw
    # Marker sits between canonical keys and extension keys.
    marker_pos = raw.index("# --- extensions ---")
    assert raw.index("docket:") > marker_pos
    assert raw.index("priority:") > marker_pos
    assert raw.index("workflow:") < marker_pos


def test_scaffold_no_extensions_no_marker(repo: Path) -> None:
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg,
        title="Plain",
        workflow_name=None,
        contexts=[],
        mode="interactive",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="draft",
    )
    raw = (ref["path"] / "ticket.md").read_text()
    assert "# --- extensions ---" not in raw


def test_extension_fields_round_trip(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + '\n[ticket.fields.docket]\ndescription = "d"\n'
    )
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg,
        title="Round trip",
        workflow_name=None,
        contexts=[],
        mode="interactive",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="draft",
    )
    t = Ticket.read(ref["path"] / "ticket.md")
    t.frontmatter["docket"] = "55-12345"
    t.write(ref["path"] / "ticket.md")
    again = Ticket.read(ref["path"] / "ticket.md")
    assert again.frontmatter["docket"] == "55-12345"
    raw = (ref["path"] / "ticket.md").read_text()
    assert "# --- extensions ---" in raw


def test_resolve_task_exact_then_prefix(repo: Path) -> None:
    """Resolve prefers exact slug match; falls back to unique prefix; errors on ambiguity."""
    from relay.tasks import resolve_task, TaskNotFoundError

    cfg = load_config(repo)
    for slug in ("fix-retry", "fix-retry-logic"):
        d = repo / "tasks" / slug
        d.mkdir(parents=True)
        (d / "ticket.md").write_text(f"---\ntitle: {slug}\n---\n")

    # Exact slug wins even when it's a prefix of another slug.
    assert resolve_task(cfg, "fix-retry").slug == "fix-retry"
    assert resolve_task(cfg, "fix-retry-logic").slug == "fix-retry-logic"

    # Unique prefix resolves.
    assert resolve_task(cfg, "fix-retry-l").slug == "fix-retry-logic"

    # Ambiguous prefix lists matches.
    with pytest.raises(TaskNotFoundError, match="Ambiguous"):
        resolve_task(cfg, "fix-r")
