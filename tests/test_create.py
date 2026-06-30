from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from typer.testing import CliRunner

from conftest import seed_direct_body_workflow
from coga.cli import app
from coga.create import create_task
from coga.config import load_config
from coga.logfile import task_log_lines
from coga.paths import log_path
from coga.taskfile import fence_count, read_blackboard
from coga.tasks import list_tasks
from coga.ticket import Ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    company = tmp_path / "coga"
    company.mkdir()

    _write(
        company / "coga.toml",
        """
        version = 1
        default_status = "draft"

        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        mode = "local"

        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')

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
    # The recurring creator auto-attaches `coga/period-task` to every
    # period task, so any recurring test path needs a resolvable stub.
    _write(
        company / "contexts" / "coga" / "period-task" / "SKILL.md",
        "---\nname: coga/period-task\ndescription: stub\n---\n",
    )
    return company


def test_create_minimal(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo)
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Fix retry logic",
        workflow_name=None,
        contexts=[],
        autonomy="interactive",
        owner=None,
        assignee=None,
        watchers=[],
        status=None,
    )
    assert ref["slug"] == "fix-retry-logic"
    ticket_path = ref["path"]
    # Single-file format: the created path IS a single `<slug>.md` ticket file
    # carrying exactly one blackboard fence, with no companion directory and
    # therefore no sibling blackboard.md / log.md.
    assert ticket_path.is_file()
    assert ticket_path.name == "fix-retry-logic.md"
    assert not (repo / "tasks" / "fix-retry-logic").exists()
    assert fence_count(ticket_path.read_text()) == 1
    ticket = Ticket.read(ticket_path)
    assert ticket.title == "Fix retry logic"
    assert ticket.status == "draft"
    assert ticket.autonomy == "interactive"
    assert ticket.owner == "marc"
    assert ticket.assignee == "marc"
    # Auto-populated role fields: human ← owner, agent ← owner's lone configured agent.
    assert ticket.human == "marc"
    assert ticket.agent == "claude"
    assert ticket.workflow is None
    assert "secrets" in ticket.frontmatter
    assert ticket.secrets is None


def test_create_preserves_secret_declaration(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo)
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Call API",
        workflow_name=None,
        contexts=[],
        autonomy="interactive",
        owner=None,
        assignee=None,
        watchers=[],
        status=None,
        secrets=[{"API_KEY": "op://Vault/item/field"}],
    )
    ticket = Ticket.read(ref["path"])
    assert ticket.secrets == [{"API_KEY": "op://Vault/item/field"}]


def test_create_uses_first_configured_agent_for_multi_agent_owner(repo: Path) -> None:
    _write(
        repo / "coga.toml",
        """
        version = 1
        default_status = "draft"

        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
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
    ref = create_task(
        cfg=cfg,
        title="Try me",
        workflow_name=None,
        contexts=[],
        autonomy="interactive",
        owner=None,
        assignee=None,
        watchers=[],
        status=None,
    )
    ticket = Ticket.read(ref["path"])
    assert ticket.human == "marc"
    assert ticket.agent == "claude"


def test_create_requires_agent_before_writing_task_dir(repo: Path) -> None:
    _write(
        repo / "coga.toml",
        """
        version = 1
        default_status = "draft"
        """,
    )
    cfg = load_config(repo)
    with pytest.raises(ValueError, match="No default agent configured"):
        create_task(
            cfg=cfg,
            title="No agent",
            workflow_name=None,
            contexts=[],
            autonomy="interactive",
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
    ref = create_task(
        cfg=cfg, title="W", workflow_name="review",
        contexts=[], autonomy="interactive",
        owner="marc", assignee=None,
        watchers=[], status="active",
    )
    ticket = Ticket.read(ref["path"])
    # Step 1 declares `assignee: agent` → resolves to `marc`'s configured agent.
    assert ticket.assignee == "claude"


def test_create_explicit_human_and_agent_overrides_defaults(repo: Path) -> None:
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=[], autonomy="interactive",
        owner="marc", assignee=None,
        human="alice", agent="claude2",
        watchers=[], status="draft",
    )
    ticket = Ticket.read(ref["path"])
    assert ticket.human == "alice"
    assert ticket.agent == "claude2"


def test_create_with_workflow_and_contexts(repo: Path) -> None:
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Task A",
        workflow_name="code/with-review",
        contexts=["email/payment-flow", "email/payment-flow"],  # dupe ignored
        autonomy="auto",
        owner="marc",
        assignee="claude",
        watchers=["pierre"],
        status="active",
    )
    ticket = Ticket.read(ref["path"])
    assert ticket.contexts == ["email/payment-flow"]
    assert ticket.workflow["name"] == "code/with-review"
    assert ticket.step == "1 (implement)"
    assert ticket.frontmatter["watchers"] == ["pierre"]


def test_create_rejects_unknown_context(repo: Path) -> None:
    cfg = load_config(repo)
    with pytest.raises(ValueError, match="Unknown contexts"):
        create_task(
            cfg=cfg,
            title="X",
            workflow_name=None,
            contexts=["does/not/exist"],
            autonomy="interactive",
            owner=None,
            assignee=None,
            watchers=[],
            status=None,
        )


def test_create_distinct_titles_get_distinct_slugs(repo: Path) -> None:
    cfg = load_config(repo)
    refs = [
        create_task(
            cfg=cfg,
            title=f"Task {i}",
            workflow_name=None,
            contexts=[],
            autonomy="interactive",
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
        autonomy="interactive",
        owner=None,
        assignee=None,
        watchers=[],
        status=None,
    )
    a = create_task(title="Same title", **kwargs)
    b = create_task(title="Same title", **kwargs)
    c = create_task(title="Same title", **kwargs)
    assert a["slug"] == "same-title"
    assert b["slug"] == "same-title-2"
    assert c["slug"] == "same-title-3"


def test_create_nested_slug_can_reuse_top_level_leaf(repo: Path) -> None:
    cfg = load_config(repo)
    kwargs = dict(
        cfg=cfg,
        workflow_name=None,
        contexts=[],
        autonomy="interactive",
        owner=None,
        assignee=None,
        watchers=[],
        status=None,
    )
    top = create_task(title="Digest", slug_override="digest", **kwargs)
    nested = create_task(
        title="Recurring digest", slug_override="recurring/digest", **kwargs
    )

    assert top["slug"] == "digest"
    assert nested["slug"] == "recurring/digest"
    refs = {ref.id_slug: ref for ref in list_tasks(cfg)}
    assert refs["digest"].directory is None
    assert refs["recurring/digest"].directory == "recurring"


# --- `--dir` sub-directory creates ------------------------------------------


def _dir_kwargs(cfg, **overrides):  # type: ignore[no-untyped-def]
    base = dict(
        cfg=cfg,
        workflow_name=None,
        contexts=[],
        autonomy="interactive",
        owner=None,
        assignee=None,
        watchers=[],
        status=None,
    )
    base.update(overrides)
    return base


def test_create_into_subdirectory(repo: Path) -> None:
    cfg = load_config(repo)
    ref = create_task(title="Build the flow", **_dir_kwargs(cfg, directory="v2"))
    assert ref["slug"] == "v2/build-the-flow"
    ticket_path = ref["path"]
    assert ticket_path == repo / "tasks" / "v2" / "build-the-flow.md"
    assert ticket_path.is_file()
    t = Ticket.read(ticket_path)
    # The on-disk slug is path-qualified so the file is self-describing.
    assert t.frontmatter["slug"] == "v2/build-the-flow"
    refs = {r.id_slug: r for r in list_tasks(cfg)}
    assert refs["v2/build-the-flow"].directory == "v2"


def test_create_into_nested_subdirectory(repo: Path) -> None:
    cfg = load_config(repo)
    ref = create_task(
        title="Relaunch", **_dir_kwargs(cfg, directory="marketing/social")
    )
    assert ref["slug"] == "marketing/social/relaunch"
    assert ref["path"] == repo / "tasks" / "marketing" / "social" / "relaunch.md"


def test_create_dir_strips_surrounding_slashes(repo: Path) -> None:
    cfg = load_config(repo)
    ref = create_task(title="Trim", **_dir_kwargs(cfg, directory="/v2/"))
    assert ref["slug"] == "v2/trim"


def test_create_same_leaf_across_directories_no_suffix(repo: Path) -> None:
    """A leaf may repeat across directories — uniqueness is per-directory."""
    cfg = load_config(repo)
    top = create_task(title="Inventory", **_dir_kwargs(cfg))
    nested = create_task(title="Inventory", **_dir_kwargs(cfg, directory="v2"))
    assert top["slug"] == "inventory"
    assert nested["slug"] == "v2/inventory"  # not auto-suffixed to -2


def test_create_collision_within_directory_suffixes(repo: Path) -> None:
    cfg = load_config(repo)
    a = create_task(title="Same", **_dir_kwargs(cfg, directory="v2"))
    b = create_task(title="Same", **_dir_kwargs(cfg, directory="v2"))
    assert a["slug"] == "v2/same"
    assert b["slug"] == "v2/same-2"


def test_create_dir_rejects_parent_traversal(repo: Path) -> None:
    cfg = load_config(repo)
    with pytest.raises(ValueError, match="must stay under tasks/"):
        create_task(title="Escape", **_dir_kwargs(cfg, directory="../escape"))
    assert not (repo / "tasks" / "escape.md").exists()


def test_create_dir_rejects_underscore_component(repo: Path) -> None:
    cfg = load_config(repo)
    with pytest.raises(ValueError, match="template"):
        create_task(title="Hidden", **_dir_kwargs(cfg, directory="_drafts"))


def test_create_dir_rejects_nesting_inside_task(repo: Path) -> None:
    """A task directory is never recursed into — refuse to create inside one."""
    cfg = load_config(repo)
    parent = repo / "tasks" / "parent"
    parent.mkdir(parents=True)
    (parent / "ticket.md").write_text("---\ntitle: parent\n---\n")
    with pytest.raises(ValueError, match="can't live inside another task"):
        create_task(title="Child", **_dir_kwargs(cfg, directory="parent"))


def test_split_create_path() -> None:
    from coga.commands.create import _split_create_path

    assert _split_create_path("Plain title") == (None, "Plain title")
    assert _split_create_path("v2/Build the flow") == ("v2", "Build the flow")
    assert _split_create_path("marketing/social/relaunch") == (
        "marketing/social",
        "relaunch",
    )
    # A leading slash has no directory; a trailing slash has an empty leaf
    # (which `create_draft` then rejects as an empty title).
    assert _split_create_path("/leading") == (None, "leading")
    assert _split_create_path("trailing/") == ("trailing", "")


def test_cli_create_path_syntax(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`coga create <dir>/<leaf>` lands under tasks/<dir>/; leaf is the title."""
    monkeypatch.chdir(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["create", "v2/subdir-ticket"])
    assert result.exit_code == 0, result.output
    ticket_path = repo / "tasks" / "v2" / "subdir-ticket.md"
    assert ticket_path.is_file()
    t = Ticket.read(ticket_path)
    assert t.frontmatter["slug"] == "v2/subdir-ticket"
    assert t.title == "subdir-ticket"
    assert "v2/subdir-ticket: created" in result.output


def test_cli_create_path_syntax_preserves_title(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The leaf is the human title (spaces kept); only the slug is slugified."""
    monkeypatch.chdir(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["create", "v2/Build the flow"])
    assert result.exit_code == 0, result.output
    ticket_path = repo / "tasks" / "v2" / "build-the-flow.md"
    assert ticket_path.is_file()
    t = Ticket.read(ticket_path)
    assert t.title == "Build the flow"
    assert t.frontmatter["slug"] == "v2/build-the-flow"


def test_cli_create_nested_path_syntax(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["create", "marketing/social/relaunch"])
    assert result.exit_code == 0, result.output
    assert (repo / "tasks" / "marketing" / "social" / "relaunch.md").is_file()


def test_cli_create_no_slash_is_top_level(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No slash → top-level create, unchanged behavior."""
    monkeypatch.chdir(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["create", "Plain title"])
    assert result.exit_code == 0, result.output
    assert (repo / "tasks" / "plain-title.md").is_file()


def test_cli_create_path_rejects_traversal(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["create", "../escape/foo"])
    assert result.exit_code == 2


def test_create_log_entry_written(repo: Path) -> None:
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="X",
        workflow_name=None,
        contexts=[],
        autonomy="interactive",
        owner=None,
        assignee=None,
        watchers=[],
        status=None,
    )
    # The audit line lands in the repo-global log, tagged with the new slug.
    log = log_path(cfg).read_text()
    assert "[x] [human:marc] created" in log
    lines = task_log_lines(cfg, ref["slug"])
    assert any("[human:marc] created" in line for line in lines)


@pytest.fixture
def repo_with_bootstrap_ticket(repo: Path) -> Path:
    """Same fixture as `repo`, plus the `bootstrap/ticket` launch target + skill."""
    _write(
        repo / "bootstrap" / "ticket" / "ticket.md",
        """
        ---
        title: Create a new ticket
        autonomy: interactive
        skills:
          - bootstrap/ticket
        assignee: claude
        ---

        ## Description

        Persistent launch target.
        """,
    )
    _write(
        repo / "skills" / "bootstrap" / "ticket" / "SKILL.md",
        """
        ---
        name: bootstrap/ticket
        description: Author a Coga task.
        ---

        Interview, fill in the ticket. Stop.
        """,
    )
    # Recurring period tasks now create with the `direct/body` workflow, so a
    # repo that materializes them needs the shipped workflow + skill present.
    seed_direct_body_workflow(repo)
    return repo


def test_recurring_creates_silently(
    repo_with_bootstrap_ticket: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bare `coga recurring` scans and creates due tasks without lifecycle Slack."""
    _write(
        repo_with_bootstrap_ticket / "recurring" / "weekly-check" / "ticket.md",
        """
        ---
        schedule: "0 9 * * 1"
        title: "Weekly deliverability check"
        autonomy: interactive
        assignee: claude
        owner: marc
        ---

        ## Description

        Run the diagnostic suite.
        """,
    )
    monkeypatch.chdir(repo_with_bootstrap_ticket)

    slack_msgs: list[str] = []

    def _capture(url, json=None, timeout=None):
        slack_msgs.append(json["text"])
        class R:
            status_code = 200
            text = "ok"
        return R()

    monkeypatch.setattr("coga.notification.slack.requests.post", _capture)
    monkeypatch.setattr(
        "coga.commands.recurring._interactive_stdio_has_tty", lambda: True
    )
    # The bare scan launches due tasks sequentially; mark the stubbed launch
    # done so the recurring sweep sees a completed run.
    def fake_launch(task: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        ticket = Ticket.read(repo_with_bootstrap_ticket / "tasks" / task / "ticket.md")
        ticket.frontmatter["status"] = "done"
        ticket.write(repo_with_bootstrap_ticket / "tasks" / task / "ticket.md")

    monkeypatch.setattr("coga.commands.launch.launch", fake_launch)

    runner = CliRunner()
    result = runner.invoke(app, ["recurring"])
    assert result.exit_code == 0, result.output
    assert "Created" in result.output

    assert slack_msgs == []


def test_recurring_posts_error_summary(
    repo_with_bootstrap_ticket: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A broken template surfaces as a Slack summary, not just stderr."""
    _write(repo_with_bootstrap_ticket / "recurring" / "broken.md", "no frontmatter here\n")
    monkeypatch.chdir(repo_with_bootstrap_ticket)

    slack_msgs: list[str] = []

    def _capture(url, json=None, timeout=None):
        slack_msgs.append(json["text"])
        class R:
            status_code = 200
            text = "ok"
        return R()

    monkeypatch.setattr("coga.notification.slack.requests.post", _capture)

    runner = CliRunner()
    result = runner.invoke(app, ["recurring"])
    assert result.exit_code == 0, result.output
    assert any("skipped 1 template" in m and "broken.md" in m for m in slack_msgs)
    # Path duplication regression: the bullet should NOT contain the full file path.
    assert not any(str(repo_with_bootstrap_ticket) in m for m in slack_msgs)


# --- `coga create` CLI ------------------------------------------------------


def test_cli_create_creates_draft_silently(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`coga create "<title>"` creates a draft ticket without Slack noise."""
    monkeypatch.chdir(repo)
    posts: list[str] = []

    def _capture(url, json=None, timeout=None):
        posts.append(json["text"])
        class R:
            status_code = 200
            text = "ok"
        return R()

    monkeypatch.setattr("coga.notification.slack.requests.post", _capture)

    runner = CliRunner()
    result = runner.invoke(
        app, ["create", "Investigate retries", "--workflow", "code/with-review"]
    )
    assert result.exit_code == 0, result.output

    ticket_path = repo / "tasks" / "investigate-retries.md"
    assert ticket_path.is_file()
    t = Ticket.read(ticket_path)
    assert t.title == "Investigate retries"
    assert t.status == "draft"
    assert t.autonomy == "interactive"

    assert posts == []


def test_cli_create_does_not_spawn_agent(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`coga create` only creates; it never spawns an agent."""
    monkeypatch.chdir(repo)
    called = False

    def fake_run(cmd, env=None, check=False):  # type: ignore[no-untyped-def]
        nonlocal called
        called = True
        class R: returncode = 0
        return R()

    monkeypatch.setattr("coga.commands.launch.subprocess.run", fake_run, raising=False)

    runner = CliRunner()
    result = runner.invoke(
        app, ["create", "Just a draft", "--workflow", "code/with-review"]
    )
    assert result.exit_code == 0, result.output
    assert not called


def test_cli_create_autonomy_option(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo)
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["create", "Auto job", "--autonomy", "auto", "--workflow", "code/with-review"],
    )
    assert result.exit_code == 0, result.output
    t = Ticket.read(repo / "tasks" / "auto-job.md")
    assert t.autonomy == "auto"


def test_cli_create_rejects_empty_title(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["create", "   "])
    assert result.exit_code == 2


# --- workflow always required ------------------------------------------------


def test_cli_create_workflow_flag_attaches_workflow(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`coga create --workflow <name>` attaches the workflow to the draft."""
    monkeypatch.chdir(repo)
    monkeypatch.setattr(
        "coga.notification.slack.requests.post",
        lambda *a, **kw: type("R", (), {"status_code": 200, "text": "ok"})(),
    )
    runner = CliRunner()
    result = runner.invoke(
        app, ["create", "With workflow", "--workflow", "code/with-review"]
    )
    assert result.exit_code == 0, result.output
    t = Ticket.read(repo / "tasks" / "with-workflow.md")
    assert t.workflow is not None
    assert t.workflow["name"] == "code/with-review"
    assert t.step == "1 (implement)"


def test_cli_create_allows_no_workflow(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`coga create` without `--workflow` creates a workflow-less draft.

    `--workflow` is optional; `coga mark active` is the gate that refuses to
    activate a workflow-less ticket.
    """
    monkeypatch.chdir(repo)
    runner = CliRunner()
    result = runner.invoke(app, ["create", "No workflow"])
    assert result.exit_code == 0, result.output
    t = Ticket.read(repo / "tasks" / "no-workflow.md")
    assert t.workflow is None
    assert t.status == "draft"


def test_create_draft_without_workflow(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`create_draft` with no workflow produces a workflow-less draft."""
    from coga.commands.create import create_draft

    monkeypatch.chdir(repo)
    monkeypatch.setattr(
        "coga.notification.slack.requests.post",
        lambda *a, **kw: type("R", (), {"status_code": 200, "text": "ok"})(),
    )
    result = create_draft(title="Interview start", autonomy="interactive")
    t = Ticket.read(result["path"])
    assert t.workflow is None


def test_create_draft_path_syntax_places_in_subdir(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`create_draft` parses the `<dir>/<leaf>` title — shared by create + ticket."""
    from coga.commands.create import create_draft

    monkeypatch.chdir(repo)
    monkeypatch.setattr(
        "coga.notification.slack.requests.post",
        lambda *a, **kw: type("R", (), {"status_code": 200, "text": "ok"})(),
    )
    result = create_draft(title="v2/Build the flow", autonomy="interactive")
    assert result["slug"] == "v2/build-the-flow"
    assert result["path"] == repo / "tasks" / "v2" / "build-the-flow.md"
    t = Ticket.read(result["path"])
    assert t.title == "Build the flow"


# --- ticket frontmatter extensions ------------------------------------------


def test_create_writes_declared_extension_fields(repo: Path) -> None:
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text()
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
    ref = create_task(
        cfg=cfg,
        title="With extensions",
        workflow_name=None,
        contexts=[],
        autonomy="interactive",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="draft",
    )
    t = Ticket.read(ref["path"])
    assert t.frontmatter["docket"] == ""
    assert t.frontmatter["priority"] == "P2"

    raw = ref["path"].read_text()
    assert "# --- extensions ---" in raw
    # Marker sits between canonical keys and extension keys.
    marker_pos = raw.index("# --- extensions ---")
    assert raw.index("docket:") > marker_pos
    assert raw.index("priority:") > marker_pos
    assert raw.index("workflow:") < marker_pos


def test_create_no_extensions_no_marker(repo: Path) -> None:
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Plain",
        workflow_name=None,
        contexts=[],
        autonomy="interactive",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="draft",
    )
    raw = ref["path"].read_text()
    assert "# --- extensions ---" not in raw


def test_extension_fields_round_trip(repo: Path) -> None:
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text()
        + '\n[ticket.fields.docket]\ndescription = "d"\n'
    )
    cfg = load_config(repo)
    ref = create_task(
        cfg=cfg,
        title="Round trip",
        workflow_name=None,
        contexts=[],
        autonomy="interactive",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="draft",
    )
    t = Ticket.read(ref["path"])
    t.frontmatter["docket"] = "55-12345"
    t.write(ref["path"])
    again = Ticket.read(ref["path"])
    assert again.frontmatter["docket"] == "55-12345"
    raw = ref["path"].read_text()
    assert "# --- extensions ---" in raw


def test_resolve_task_exact_then_prefix(repo: Path) -> None:
    """Resolve prefers exact slug match; falls back to unique prefix; errors on ambiguity."""
    from coga.tasks import resolve_task, TaskNotFoundError

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


def test_resolve_task_accepts_path_qualified_ref(repo: Path) -> None:
    """A nested task resolves by its full `<dir>/<leaf>` ref and by path prefix.

    This is the shared mechanism behind every resolving command — `delete`,
    `show`, `launch`, `bump`, `mark`, `retire`, `panic` all funnel through
    `resolve_task`, so `coga delete v2/build-the-flow` works the moment the
    nested task exists.
    """
    from coga.tasks import resolve_task

    cfg = load_config(repo)
    create_task(title="Build the flow", **_dir_kwargs(cfg, directory="v2"))

    # Exact path-qualified ref resolves.
    assert resolve_task(cfg, "v2/build-the-flow").id_slug == "v2/build-the-flow"
    # A unique path prefix resolves too (git-short-SHA style).
    assert resolve_task(cfg, "v2/build").id_slug == "v2/build-the-flow"
