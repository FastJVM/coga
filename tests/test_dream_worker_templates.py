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

DREAM = TEMPLATES.parent


def test_dream_orchestrator_documents_worker_contract() -> None:
    text = (DREAM / "SKILL.md").read_text()

    assert "Dream is the repo's recurring maintenance orchestrator" in text
    assert "relay-os/skills/dream/orchestrate/SKILL.md" in text
    assert "tasks/**/SKILL.md" in text
    assert "## Worker Contract" in text
    assert "report-only | proposal-only | pr-required | direct-fix" in text
    assert "If it does not contain the" in text
    assert "## Dream Run Summary" in text


def test_validate_drift_worker_declares_contract() -> None:
    text = (TEMPLATES / "validate-drift" / "SKILL.md").read_text()

    assert "## Worker Contract" in text
    assert "- Scope: relay-core" in text
    assert "- Action: `direct-fix`" in text
    assert "- May change: missing `blackboard.md` and `log.md` files only" in text
    assert "- Idempotency: `relay validate --fix`" in text
    assert "- Output: append `## Dream Worker: validate-drift`" in text


def test_stale_branch_worker_template_is_proposal_only() -> None:
    text = (TEMPLATES / "dev" / "stale-branches" / "SKILL.md").read_text()

    assert "name: bootstrap/dream/tasks/dev/stale-branches" in text
    assert "## Worker Contract" in text
    assert "- Scope: dev/code" in text
    assert "- May change: none" in text
    assert "- Action: `proposal-only`" in text
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
