from __future__ import annotations

from pathlib import Path


TEMPLATES = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "relay"
    / "resources"
    / "templates"
    / "relay-os"
    / "skills"
    / "bootstrap"
    / "dream"
    / "tasks"
)


def test_stale_branch_worker_template_is_proposal_only() -> None:
    text = (TEMPLATES / "dev" / "stale-branches" / "SKILL.md").read_text()

    assert "name: bootstrap/dream/tasks/dev/stale-branches" in text
    assert "git branch --merged <remote-default>" in text
    assert "git merge-base --is-ancestor <local-branch> <remote-default>" in text
    assert "git fetch --prune --dry-run origin" in text
    assert "### Merged Local Branches" in text
    assert "### Stale Remote-Tracking Refs" in text
    assert "### Old Topic Branches" in text
    assert "`main`" in text
    assert "git branch -D <branch>" in text
    assert "Direct deletion is not implemented in this template." in text
    assert "git push origin --delete" in text


def test_unit_test_worker_template_is_dev_only_and_project_configured() -> None:
    text = (TEMPLATES / "dev" / "unit-tests" / "SKILL.md").read_text()

    assert "name: bootstrap/dream/tasks/dev/unit-tests" in text
    assert "This is a project-specific Dream worker template for code repos" in text
    assert "Do not run this worker for non-engineering Dream work." in text
    assert "[dream.dev.unit_tests]" in text
    assert 'command = "python -m pytest"' in text
    assert "do not guess from files such as `pyproject.toml`, `package.json`" in text
    assert "Missing configured unit test command." in text
    assert "Do not run a default test command." in text
    assert "failing test name or runner heading" in text
    assert "classification: `known`, `new`, or `unknown`" in text
    assert "Do not call a failure new just" in text
    assert "because this worker has not seen it before." in text
    assert "do not open a PR just to" in text
