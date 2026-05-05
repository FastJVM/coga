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
REM_TEMPLATE = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "relay"
    / "resources"
    / "templates"
    / "relay-os"
    / "recurring"
    / "_rem.md"
)


def test_dream_documents_ordered_skill_pass() -> None:
    text = WEEKLY_DREAM.read_text()
    workflow = BOOTSTRAP_DREAM_RUN.read_text()

    assert not (DREAM / "SKILL.md").exists()
    assert not (DREAM / "scan.py").exists()
    assert not (TEMPLATES / "dev" / "stale-branches" / "SKILL.md").exists()
    assert "skill: bootstrap/dream" not in workflow
    assert "Run the Dream maintenance pass described directly" in workflow
    assert "Run the Dream cleanup pass for this Relay repo" in text
    assert "Dream is Relay's generic cleanup pass" in text
    assert "Dream is not REM" in text
    assert "### Ordered Skill Pass" in text
    assert "`bootstrap/dream/tasks/validate-drift`" in text
    assert "`retro/done-ticket`" in text
    assert "`bootstrap/dream/tasks/dev/stale-branches`" not in text
    assert "dev/stale-branches" not in text
    assert "That table is the dispatch contract" in text
    assert "Do not auto-discover skills" in text
    assert "another recurring task with its own\nbody and ordered skill list" in text
    assert "### Skill: validate-drift" in text
    assert "### Skill: retro/done-ticket" in text
    assert "### Skill: dev/stale-branches" not in text
    assert "### Done-Ticket Cleanup" in text
    assert "status: processed" in text
    assert "skill: retro/done-ticket" in text
    assert "An open\n   PR counts as in flight" in text
    assert "Absence of the marker on an existing done ticket" in text
    assert "git history for the deleted `blackboard.md`" in text
    assert "## Dream Run Summary" in text
    assert "relay slack --task <this-dream-task>" in text
    assert "stale branch" not in text.lower()
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


def test_rem_template_documents_user_specific_recurring_maintenance() -> None:
    text = REM_TEMPLATE.read_text()

    assert "REM is repo/user-specific recurring maintenance" in text
    assert "REM is not Dream" in text
    assert "Dream is Relay's generic ticket cleanup pass" in text
    assert "copy or rename it to a non-underscore" in text
    assert "product or operations health checks" in text
    assert "domain-specific recurring reports" in text
    assert "Do not put generic Relay cleanup here" in text
