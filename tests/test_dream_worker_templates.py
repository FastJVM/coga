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
RESOURCES = Path(__file__).resolve().parents[1] / "src" / "relay" / "resources"
WEEKLY_DREAM = RESOURCES / "recurring" / "weekly-dream.md"
BOOTSTRAP_DREAM_RUN = RESOURCES / "workflows" / "bootstrap" / "dream-run.md"


def test_dream_documents_ordered_skill_pass() -> None:
    text = WEEKLY_DREAM.read_text()
    workflow = BOOTSTRAP_DREAM_RUN.read_text()

    assert not (DREAM / "SKILL.md").exists()
    assert not (DREAM / "scan.py").exists()
    assert "skill: bootstrap/dream" not in workflow
    assert "Run the Dream maintenance pass described directly" in workflow
    assert "Run the Dream maintenance pass for this Relay repo" in text
    assert "Dream is this recurring task, not a workflow" in text
    assert "### Ordered Skill Pass" in text
    assert "`bootstrap/dream/tasks/validate-drift`" in text
    assert "`retro/done-ticket`" in text
    assert "`bootstrap/dream/tasks/dev/stale-branches`" in text
    assert "That table is the dispatch contract" in text
    assert "Do not auto-discover skills" in text
    assert "another recurring task with its own\nbody and ordered skill list" in text
    assert "### Skill: validate-drift" in text
    assert "### Skill: retro/done-ticket" in text
    assert "### Skill: dev/stale-branches" in text
    assert "status: processed" in text
    assert "skill: retro/done-ticket" in text
    assert "An open\n   PR counts as in flight" in text
    assert "Absence of the marker on an existing done ticket" in text
    assert "git history for the deleted `blackboard.md`" in text
    assert "## Dream Run Summary" in text
    assert "relay slack --task <this-dream-task>" in text
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
