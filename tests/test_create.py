from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from relay.commands.create import scaffold_task
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
        default_status = "ready"

        [agents.claude]
        cli = "claude"
        interactive = "--append-system-prompt-file"
        auto = "-p"
        file = "CLAUDE.md"
        mode = "local"

        [assignees.marc]
        agents = {"claude1" = "claude"}
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
            skill: infra/testing-conventions
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
    assert ticket.status == "ready"
    assert ticket.mode == "interactive"
    assert ticket.owner == "marc"
    assert ticket.assignee == "marc"
    assert ticket.workflow is None


def test_create_with_workflow_and_contexts(repo: Path) -> None:
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg,
        title="Task A",
        workflow_name="code/with-review",
        contexts=["email/payment-flow", "email/payment-flow"],  # dupe ignored
        mode="auto",
        owner="marc",
        assignee="claude1",
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
