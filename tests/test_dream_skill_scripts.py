from __future__ import annotations

import shutil
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.config import load_config
from relay.create import create_task
from relay.taskfile import read_blackboard
from relay.tasks import list_tasks


TEMPLATES = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "relay"
    / "resources"
    / "templates"
    / "relay-os"
    / "bootstrap"
    / "skills"
    / "bootstrap"
    / "dream"
    / "tasks"
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    relay_os = tmp_path / "relay-os"
    _write(
        relay_os / "relay.toml",
        """
        version = 1
        default_status = "draft"

        [slack]
        enabled = false

        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"

        """,
    )
    _write(relay_os / "relay.local.toml", 'user = "marc"\n')
    (relay_os / "tasks").mkdir(parents=True)
    monkeypatch.chdir(relay_os)
    return relay_os


def _install_dream_skill(relay_os: Path, name: str) -> None:
    dst = relay_os / "skills" / "bootstrap" / "dream" / "tasks" / name
    shutil.copytree(TEMPLATES / name, dst)


def _write_workflow(relay_os: Path, name: str, skill: str) -> None:
    _write(
        relay_os / "workflows" / f"{name}.md",
        f"""
        ---
        name: {name}
        description: script worker.
        steps:
          - name: run
            skills:
              - {skill}
        ---
        """,
    )


def test_validate_drift_runs_as_script_skill(repo: Path) -> None:
    _install_dream_skill(repo, "validate-drift")
    _write_workflow(repo, "validate-drift", "bootstrap/dream/tasks/validate-drift")
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Validate Drift",
        workflow_name="validate-drift",
        contexts=[],
        autonomy="interactive",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
    )

    result = CliRunner().invoke(app, ["launch", "validate-drift"])

    assert result.exit_code == 0, result.output
    ref = list_tasks(cfg)[0]
    # Single-file format: a script worker's RELAY_TASK_BLACKBOARD is its own
    # ticket.md, so its appended notes land in that ticket's blackboard region.
    blackboard = read_blackboard(ref.ticket_path)
    assert "## Dream Skill: validate-drift" in blackboard
    assert "Task: `validate-drift`" in blackboard


def test_cleanup_orphan_markers_runs_as_script_skill_and_gates_delete(repo: Path) -> None:
    _install_dream_skill(repo, "cleanup-orphan-markers")
    _write_workflow(
        repo,
        "cleanup-orphan-markers",
        "bootstrap/dream/tasks/cleanup-orphan-markers",
    )
    # A genuine cleanup-eligible orphan: a `status: done` ticket whose blackboard
    # region (below the `<!-- relay:blackboard -->` fence in ticket.md) carries a
    # `## Retro` marker recording a knowledge-PR processing pass (NOT
    # `no-new-durable-knowledge`). Single-file v2: the cleanup worker reads the
    # marker from the ticket.md blackboard region, not a sibling blackboard.md.
    _write(
        repo / "tasks" / "processed-ticket" / "ticket.md",
        """
        ---
        slug: processed-ticket
        title: Processed Ticket
        status: done
        autonomy: interactive
        owner: marc
        assignee: marc
        ---

        ## Description

        Already processed.

        <!-- relay:blackboard -->

        Notes.

        ## Retro

        status: processed
        skill: retro/done-ticket
        result: knowledge-pr
        """,
    )

    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Cleanup Orphan Markers",
        workflow_name="cleanup-orphan-markers",
        contexts=[],
        autonomy="interactive",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
    )

    result = CliRunner().invoke(app, ["launch", "cleanup-orphan-markers"])

    assert result.exit_code == 0, result.output
    refs = {ref.slug: ref for ref in list_tasks(cfg)}
    blackboard = read_blackboard(refs["cleanup-orphan-markers"].ticket_path)
    assert "## Dream Skill: cleanup-orphan-markers" in blackboard
    assert "Result: human-needed." in blackboard
    assert "Required delete skill is missing" in blackboard
    assert "`processed-ticket`: processed marker present; deletion skipped." in blackboard
    assert (repo / "tasks" / "processed-ticket").is_dir()


def test_cleanup_orphan_markers_skips_no_new_knowledge_markers(repo: Path) -> None:
    _install_dream_skill(repo, "cleanup-orphan-markers")
    _write_workflow(
        repo,
        "cleanup-orphan-markers",
        "bootstrap/dream/tasks/cleanup-orphan-markers",
    )
    _write(
        repo / "tasks" / "processed-ticket" / "ticket.md",
        """
        ---
        slug: processed-ticket
        title: Processed Ticket
        status: done
        autonomy: interactive
        owner: marc
        assignee: marc
        ---

        ## Description

        Already processed.

        <!-- relay:blackboard -->

        Notes.

        ## Retro

        status: processed
        skill: retro/done-ticket
        result: no-new-durable-knowledge
        """,
    )

    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Cleanup Orphan Markers",
        workflow_name="cleanup-orphan-markers",
        contexts=[],
        autonomy="interactive",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
    )

    result = CliRunner().invoke(app, ["launch", "cleanup-orphan-markers"])

    assert result.exit_code == 0, result.output
    refs = {ref.slug: ref for ref in list_tasks(cfg)}
    blackboard = read_blackboard(refs["cleanup-orphan-markers"].ticket_path)
    assert "## Dream Skill: cleanup-orphan-markers" in blackboard
    assert "Result: no-op." in blackboard
    assert "cleanup-eligible processed done tickets" in blackboard
    assert "Required delete skill is missing" not in blackboard
    assert "`processed-ticket`: processed marker present" not in blackboard
    assert (repo / "tasks" / "processed-ticket").is_dir()


def test_cleanup_orphan_markers_ignores_inline_retro_mentions(repo: Path) -> None:
    """A blackboard that only mentions the marker strings in prose — e.g. a
    ticket documenting the marker format — must not be detected as a candidate.
    `## Retro` counts only as a line-start heading."""
    _install_dream_skill(repo, "cleanup-orphan-markers")
    _write_workflow(
        repo,
        "cleanup-orphan-markers",
        "bootstrap/dream/tasks/cleanup-orphan-markers",
    )
    _write(
        repo / "tasks" / "documents-the-marker" / "ticket.md",
        """
        ---
        slug: documents-the-marker
        title: Documents The Marker
        status: done
        autonomy: interactive
        owner: marc
        assignee: marc
        ---

        ## Description

        Built the marker-detection skill.

        <!-- relay:blackboard -->

        Notes on the design.

        It scans exact `status: done` task directories for a `## Retro` block
        with `skill: retro/done-ticket` and `status: processed`; if candidates
        exist it gates deletion through the public delete skill.
        """,
    )

    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Cleanup Orphan Markers",
        workflow_name="cleanup-orphan-markers",
        contexts=[],
        autonomy="interactive",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
    )

    result = CliRunner().invoke(app, ["launch", "cleanup-orphan-markers"])

    assert result.exit_code == 0, result.output
    refs = {ref.slug: ref for ref in list_tasks(cfg)}
    blackboard = read_blackboard(refs["cleanup-orphan-markers"].ticket_path)
    assert "## Dream Skill: cleanup-orphan-markers" in blackboard
    assert "Result: no-op." in blackboard
    assert "`documents-the-marker`" not in blackboard
    assert (repo / "tasks" / "documents-the-marker").is_dir()
