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


def test_dream_documents_ordered_skill_pass() -> None:
    text = (DREAM / "SKILL.md").read_text()

    assert "Dream is the recurring maintenance pass" in text
    assert "run a small fixed list of known maintenance skills in order" in text
    assert "## Step 1 - Run the ordered maintenance skills" in text
    assert "`validate-drift`" in text
    assert "`retro/done-ticket`" in text
    assert "`dev/stale-branches`" in text
    assert "retro-first, delete-second cleanup rule" in text
    assert "Dream does not auto-discover skills" in text
    assert "project-level plugin API" in text
    assert "another recurring task with its\nown instructions" in text
    assert "separate from this Dream pass" in text
    assert "## Known Skill Contract" in text
    assert "report-only | proposal-only | pr-required | direct-fix" in text
    assert "source-task blackboard `## Retro` marker with `skill: retro/done-ticket`" in text
    assert "## Known skill - retro/done-ticket" in text
    assert "status: processed" in text
    assert "skill: retro/done-ticket" in text
    assert "An open\n   PR counts as in flight" in text
    assert "Absence of the marker on an existing done ticket" in text
    assert "git history for the deleted `blackboard.md`" in text
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
