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

    assert "Dream is Relay's bootstrap maintenance feature" in text
    assert "## Step 1 - Run the known Dream skills" in text
    assert "`bootstrap/dream/tasks/validate-drift`" in text
    assert "`bootstrap/dream/tasks/retro-done-ticket`" in text
    assert "`bootstrap/dream/tasks/dev/stale-branches`" in text
    assert "Dream does not recursively discover skill files" in text
    assert "project-level plugin API" in text
    assert "for example `rem`" in text
    assert "plugged into bootstrap Dream" in text
    assert "## Known Skill Contract" in text
    assert "report-only | proposal-only | pr-required | direct-fix" in text
    assert "## Dream Run Summary" in text
    assert "relay-os/skills/dream/orchestrate/SKILL.md" not in text
    assert "tasks/**/SKILL.md" not in text


def test_validate_drift_worker_declares_contract() -> None:
    text = (TEMPLATES / "validate-drift" / "SKILL.md").read_text()

    assert "## Known Skill Contract" in text
    assert "- Purpose: deterministic repo-health validation" in text
    assert "- Action: `direct-fix`" in text
    assert "- May change: missing `blackboard.md` and `log.md` files only" in text
    assert "- Idempotency: `relay validate --fix`" in text
    assert "- Output: append `## Dream Skill: validate-drift`" in text


def test_stale_branch_worker_template_is_proposal_only() -> None:
    text = (TEMPLATES / "dev" / "stale-branches" / "SKILL.md").read_text()

    assert "name: bootstrap/dream/tasks/dev/stale-branches" in text
    assert "## Known Skill Contract" in text
    assert "- Purpose: produce reviewable stale-branch cleanup evidence" in text
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


def test_retro_done_ticket_worker_template_requires_one_done_ticket() -> None:
    text = (TEMPLATES / "retro-done-ticket" / "SKILL.md").read_text()
    run_py = (TEMPLATES / "retro-done-ticket" / "run.py").read_text()

    assert "name: bootstrap/dream/tasks/retro-done-ticket" in text
    assert "## Known Skill Contract" in text
    assert "accepts exactly one Relay" in text
    assert "Non-`done` tickets are a no-op" in text
    assert "`ticket.md`, `blackboard.md`, and `log.md`" in text
    assert "--commit-and-push --create-pr --blackboard relay-os/tasks/<dream-run-task>/blackboard.md" in text
    assert "Source ref" in text
    assert "context or skill artifacts" in text
    assert "The source task directory is never deleted" in text
    assert "Task branch cleanup belongs to separate Dream branch-cleanup skills" in text
    assert "def main(" in run_py
    assert "from relay.tasks import TaskNotFoundError" in run_py
    assert "relay.dream_retro_done_ticket" not in run_py
