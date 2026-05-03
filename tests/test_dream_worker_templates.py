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
