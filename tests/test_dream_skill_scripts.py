from __future__ import annotations

import shutil
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.config import load_config
from relay.scaffold import scaffold_task
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


def _install_dream_skill_bootstrap(relay_os: Path, name: str) -> None:
    # Install into the bundled bootstrap root rather than the project-local
    # `skills/` tree. `relay skill update --all` scans `skills/`, so an empty
    # `skills/` keeps the update a true no-op (no `gh`, no git) — the worker
    # being tested must not look like an imported, gh-backed local skill.
    dst = relay_os / "bootstrap" / "skills" / "bootstrap" / "dream" / "tasks" / name
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
    scaffold_task(
        cfg=cfg,
        title="Validate Drift",
        workflow_name="validate-drift",
        contexts=[],
        mode="script",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
    )

    result = CliRunner().invoke(app, ["launch", "validate-drift"])

    assert result.exit_code == 0, result.output
    ref = list_tasks(cfg)[0]
    blackboard = (ref.path / "blackboard.md").read_text()
    assert "## Dream Skill: validate-drift" in blackboard
    assert "Task: `validate-drift`" in blackboard


def test_skill_update_runs_as_script_skill_and_reports_no_op(repo: Path) -> None:
    # No imported skills under `skills/`: `relay skill update --all --pr` finds
    # nothing clean to update, so it commits nothing and opens no PR (never
    # touching git), and the worker reports a clean no-op on the child
    # blackboard.
    _install_dream_skill_bootstrap(repo, "skill-update")
    _write_workflow(repo, "skill-update", "bootstrap/dream/tasks/skill-update")
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg,
        title="Skill Update",
        workflow_name="skill-update",
        contexts=[],
        mode="script",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
    )

    result = CliRunner().invoke(app, ["launch", "skill-update"])

    assert result.exit_code == 0, result.output
    ref = list_tasks(cfg)[0]
    blackboard = (ref.path / "blackboard.md").read_text()
    assert "## Dream Skill: skill-update" in blackboard
    assert "Task: `skill-update`" in blackboard
    assert "PR: none opened" in blackboard


def test_cleanup_orphan_markers_runs_as_script_skill_and_gates_delete(repo: Path) -> None:
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
        title: Processed Ticket
        status: done
        mode: interactive
        owner: marc
        assignee: marc
        ---

        ## Description

        Already processed.
        """,
    )
    _write(
        repo / "tasks" / "processed-ticket" / "blackboard.md",
        """
        Notes.

        ## Retro

        status: processed
        skill: retro/done-ticket
        result: knowledge-pr
        """,
    )
    _write(repo / "tasks" / "processed-ticket" / "log.md", "")

    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg,
        title="Cleanup Orphan Markers",
        workflow_name="cleanup-orphan-markers",
        contexts=[],
        mode="script",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
    )

    result = CliRunner().invoke(app, ["launch", "cleanup-orphan-markers"])

    assert result.exit_code == 0, result.output
    refs = {ref.slug: ref for ref in list_tasks(cfg)}
    blackboard = (refs["cleanup-orphan-markers"].path / "blackboard.md").read_text()
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
        title: Processed Ticket
        status: done
        mode: interactive
        owner: marc
        assignee: marc
        ---

        ## Description

        Already processed.
        """,
    )
    _write(
        repo / "tasks" / "processed-ticket" / "blackboard.md",
        """
        Notes.

        ## Retro

        status: processed
        skill: retro/done-ticket
        result: no-new-durable-knowledge
        """,
    )
    _write(repo / "tasks" / "processed-ticket" / "log.md", "")

    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg,
        title="Cleanup Orphan Markers",
        workflow_name="cleanup-orphan-markers",
        contexts=[],
        mode="script",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
    )

    result = CliRunner().invoke(app, ["launch", "cleanup-orphan-markers"])

    assert result.exit_code == 0, result.output
    refs = {ref.slug: ref for ref in list_tasks(cfg)}
    blackboard = (refs["cleanup-orphan-markers"].path / "blackboard.md").read_text()
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
        title: Documents The Marker
        status: done
        mode: interactive
        owner: marc
        assignee: marc
        ---

        ## Description

        Built the marker-detection skill.
        """,
    )
    _write(
        repo / "tasks" / "documents-the-marker" / "blackboard.md",
        """
        Notes on the design.

        It scans exact `status: done` task directories for a `## Retro` block
        with `skill: retro/done-ticket` and `status: processed`; if candidates
        exist it gates deletion through the public delete skill.
        """,
    )
    _write(repo / "tasks" / "documents-the-marker" / "log.md", "")

    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg,
        title="Cleanup Orphan Markers",
        workflow_name="cleanup-orphan-markers",
        contexts=[],
        mode="script",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
    )

    result = CliRunner().invoke(app, ["launch", "cleanup-orphan-markers"])

    assert result.exit_code == 0, result.output
    refs = {ref.slug: ref for ref in list_tasks(cfg)}
    blackboard = (refs["cleanup-orphan-markers"].path / "blackboard.md").read_text()
    assert "## Dream Skill: cleanup-orphan-markers" in blackboard
    assert "Result: no-op." in blackboard
    assert "`documents-the-marker`" not in blackboard
    assert (repo / "tasks" / "documents-the-marker").is_dir()
