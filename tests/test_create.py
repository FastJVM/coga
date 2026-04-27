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
    assert ref["id_slug"] == "001-fix-retry-logic"
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


def test_create_increments_counter(repo: Path) -> None:
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
    assert [r["id_slug"] for r in refs] == ["001-task-0", "002-task-1", "003-task-2"]


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


def test_resolve_task_prefers_exact_id_slug(repo: Path) -> None:
    """When two task dirs share an id, the full id-slug must win the lookup."""
    from relay.tasks import resolve_task, TaskNotFoundError

    cfg = load_config(repo)
    # Manually create two dirs with the same id but different slugs.
    for slug in ("test", "test-ticket"):
        d = repo / "tasks" / f"002-{slug}"
        d.mkdir(parents=True)
        (d / "ticket.md").write_text(f"---\ntitle: {slug}\n---\n")

    # Exact id-slug match returns the right one.
    assert resolve_task(cfg, "002-test").slug == "test"
    assert resolve_task(cfg, "002-test-ticket").slug == "test-ticket"

    # Bare numeric "002" is ambiguous → error with both slugs listed.
    with pytest.raises(TaskNotFoundError, match="Multiple tasks"):
        resolve_task(cfg, "002")


def test_create_skips_past_drifted_counter(repo: Path) -> None:
    """If the counter is behind reality, scaffold should bump past existing IDs
    rather than minting a duplicate. Covers dogfood/migrated repos where task
    dirs exist but the counter wasn't incremented for them."""
    cfg = load_config(repo)
    # Pretend 001 and 002 pre-existed without the counter being bumped.
    for slug in ("001-old-a", "002-old-b"):
        (repo / "tasks" / slug).mkdir(parents=True)
        (repo / "tasks" / slug / "ticket.md").write_text(f"---\ntitle: {slug}\n---\n")

    ref = scaffold_task(
        cfg=cfg,
        title="Fresh",
        workflow_name=None,
        contexts=[],
        mode="interactive",
        owner=None,
        assignee=None,
        watchers=[],
        status=None,
    )
    # Counter starts empty, returns 1 then 2 (both colliding), then 3 — clean.
    assert ref["id_slug"] == "003-fresh"
