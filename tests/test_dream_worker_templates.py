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
RECURRING_TEMPLATES = (
    RESOURCES / "templates" / "relay-os" / "recurring"
)
# Dream is a recurring task template, not a built-in command. Its body lives
# in the recurring template's `## Description` section.
DREAM_PROMPT = RECURRING_TEMPLATES / "dream.md"
REM_TEMPLATE = RECURRING_TEMPLATES / "_rem.md"


def test_dream_ships_as_a_recurring_template() -> None:
    """Dream is a recurring task template, not a built-in command. The body
    lives in the template's `## Description` section so `scaffold_task` picks
    it up the same way it does for any other recurring template."""
    text = DREAM_PROMPT.read_text()

    assert text.startswith("---\n")
    assert "schedule:" in text
    assert 'title: "Dream"' in text
    assert "mode: interactive" in text
    assert "\n## Description\n" in text


def test_dream_documents_decide_then_execute_phases() -> None:
    text = DREAM_PROMPT.read_text()

    assert not (DREAM / "SKILL.md").exists()
    assert not (DREAM / "scan.py").exists()
    assert not (TEMPLATES / "dev" / "stale-branches" / "SKILL.md").exists()
    assert "Run the Dream cleanup pass for this Relay repo" in text
    assert "Dream is Relay's generic cleanup pass" in text
    assert "Dream is not REM" in text
    assert "### Console Progress" in text
    assert "Write short progress updates to the console" in text
    assert "### Run order" in text
    assert "**decide**" in text
    assert "**execute**" in text
    assert "This body is the dispatch contract" in text
    assert "Do not auto-discover skills" in text
    assert "### Phase 1" in text
    assert "### Phase 2" in text
    assert "### Phase 3" in text
    assert "### Phase 4" in text
    assert "### Phase 5" in text
    assert "`bootstrap/dream/tasks/validate-drift`" in text
    assert "retro/done-ticket" in text
    assert "`bootstrap/dream/tasks/cleanup-orphan-markers`" in text
    assert "`bootstrap/dream/tasks/dev/stale-branches`" not in text
    assert "dev/stale-branches" not in text
    assert "### Skill: dev/stale-branches" not in text
    assert "knowledge scan" in text
    assert "`extract`" in text
    assert "`stale`" in text
    assert "`gap`" in text
    assert "relay create" in text
    assert "there is no per-run ticket cap" in text
    assert "status: processed" in text
    assert "skill: retro/done-ticket" in text
    assert "no-new-durable-knowledge" in text
    assert "Dream-owned scripts\nare skills attached to Relay tasks" in text
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
