from __future__ import annotations

from pathlib import Path


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

DREAM = TEMPLATES.parent
RESOURCES = Path(__file__).resolve().parents[1] / "src" / "relay" / "resources"
DREAM_PROMPT = RESOURCES / "dream.md"
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
    text = DREAM_PROMPT.read_text()

    assert not (DREAM / "SKILL.md").exists()
    assert not (DREAM / "scan.py").exists()
    assert not (TEMPLATES / "dev" / "stale-branches" / "SKILL.md").exists()
    assert "Run the Dream cleanup pass for this Relay repo" in text
    assert "Dream is Relay's generic cleanup pass" in text
    assert "Dream is not REM" in text
    assert "### Console Progress" in text
    assert "Write short progress updates to the console" in text
    assert "### Ordered Skill Pass" in text
    assert "`bootstrap/dream/tasks/validate-drift`" in text
    assert "`retro/done-ticket`" in text
    assert "`bootstrap/dream/tasks/cleanup-orphan-markers`" in text
    assert "`bootstrap/dream/tasks/dev/stale-branches`" not in text
    assert "dev/stale-branches" not in text
    assert "That table is the dispatch contract" in text
    assert "Do not auto-discover skills" in text
    assert "make another task with its own body and\nordered skill list" in text
    assert "### Skill: validate-drift" in text
    assert "### Skill: retro/done-ticket" in text
    assert "### Skill: cleanup-orphan-markers" in text
    assert "### Skill: dev/stale-branches" not in text
    assert "status: processed" in text
    assert "skill: retro/done-ticket" in text
    assert "Batched knowledge extraction" in text
    assert "processes up to five coherent done tickets with a running delta" in text
    assert "max source tickets per batch PR: 5" in text
    assert "max knowledge files touched: 3" in text
    assert "max new context or skill files created: 1" in text
    assert "need \"and\" in the PR title" in text
    assert "Do not force a monster Retro PR" in text
    assert "`no-new-durable-knowledge` markers are terminal no-ops" in text
    assert "An open\n   PR counts as in flight" in text
    assert "Absence of the marker on an existing done ticket" in text
    assert "git history for the deleted `blackboard.md`" in text
    assert "Dream-owned scripts are skills attached to Relay tasks" in text
    assert "--blackboard" not in text
    assert "Dream Run Summary" in text
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
    assert "RELAY_TASK_BLACKBOARD" in text
    assert "--blackboard" not in text


def test_cleanup_orphan_markers_declares_contract() -> None:
    text = (TEMPLATES / "cleanup-orphan-markers" / "SKILL.md").read_text()

    assert "## Known Skill Contract" in text
    assert "- Purpose: detect already-processed done tickets" in text
    assert "- Action: `pr-required`" in text
    assert "`bootstrap/delete-task`" in text
    assert "exact `status: done`" in text
    assert "`skill: retro/done-ticket`" in text
    assert "`status: processed`" in text
    assert "`result: no-new-durable-knowledge`" in text
    assert "not a prefix match" in text
    assert "reports eligible candidates as `human-needed`" in text


def test_rem_template_documents_user_specific_recurring_maintenance() -> None:
    text = REM_TEMPLATE.read_text()

    assert "REM is repo/user-specific recurring maintenance" in text
    assert "REM is not Dream" in text
    assert "Dream is Relay's generic ticket cleanup pass" in text
    assert "copy or rename it to a non-underscore" in text
    assert "product or operations health checks" in text
    assert "domain-specific recurring reports" in text
    assert "Do not put generic Relay cleanup here" in text
