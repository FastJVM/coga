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
DREAM_PROMPT = RECURRING_TEMPLATES / "dream" / "ticket.md"
DREAM_BLACKBOARD = RECURRING_TEMPLATES / "dream" / "blackboard.md"
REM_TEMPLATE = RECURRING_TEMPLATES / "_rem" / "ticket.md"


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
    assert "### Phase 6" in text
    assert "### Phase 7" in text
    assert "Dream runs seven phases in order" in text
    assert "`bootstrap/dream/tasks/validate-drift`" in text
    assert "`bootstrap/dream/tasks/skill-update`" in text
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
    assert "no per-run ticket cap" in text
    assert "Extract durable knowledge from done tickets, then delete every one of them." in text
    assert "its directory `relay-os/tasks/<slug>/` still exists" in text
    assert "Retro never leaves a processed done ticket on" in text
    # Knowledge-less tickets are direct-deleted, not bundled into a prune PR.
    assert "is direct-deleted with" in text
    assert "`relay delete <slug>`" in text
    assert "with no PR and no marker" in text
    assert "delete-only prune PR" not in text
    assert "## Pruned" not in text
    assert "Dream-owned scripts\nare skills attached to Relay tasks" in text
    assert "--blackboard" not in text
    assert "Dream Run Summary" in text
    assert "relay slack --task <this-dream-task>" in text
    assert "stale branch" not in text.lower()
    assert "relay-os/skills/dream/orchestrate/SKILL.md" not in text
    assert "tasks/**/SKILL.md" not in text


def test_dream_is_the_single_deleter_of_done_recurring_tickets() -> None:
    """Stage 3 of the recurring-lifecycle redesign: Dream's Phase 5 retro pass
    is the single deleter of done `recurring-*` period tickets, and Dream no
    longer self-deletes mid-run — the next run's retro pass cleans it up."""
    text = DREAM_PROMPT.read_text()
    # Prose wraps across lines; normalize whitespace and bold markers so phrase
    # assertions don't depend on where the line breaks fall.
    norm = " ".join(text.replace("**", "").split())

    # Phase 5 explicitly owns done recurring period-ticket cleanup: a
    # `recurring-<name>-<period>` ticket is an eligible done ticket like any
    # other and, carrying nothing durable, is direct-deleted.
    assert "A done `recurring-<name>-<period>` ticket is an eligible done ticket" in norm
    assert "The recurring command does not delete real done period tasks" in norm
    assert "the previous Dream run's own `recurring-dream-<period>` ticket" in norm

    # Phase 7 marks the Dream task done and STOPS — it must not self-delete.
    assert "do not delete this task" in norm
    assert "cleaned up by the next Dream run's Phase 5 retro pass" in norm
    assert "Dream is the single deleter of done recurring tickets" in norm
    # The old self-delete instruction is gone.
    assert "relay delete <this-dream-task>" not in text
    assert "Dream cleans up after itself in the same run" not in text

    blackboard = DREAM_BLACKBOARD.read_text()
    blackboard_norm = " ".join(blackboard.split())
    assert "Dream's per-period task is disposable after it is marked done" in blackboard_norm
    assert "Dream keeps no durable state here" in blackboard_norm
    assert "not delete itself mid-run" in blackboard_norm
    assert "deletes itself" not in blackboard
    assert "self-deleted" not in blackboard


def test_dream_documents_the_contract_audit_phase() -> None:
    """Phase 3 is a dedicated consistency audit: a subagent checks the living
    contract surface (contexts, skills, recurring templates, shipped docs)
    against code reality, missing artifacts, and live/packaged copy drift,
    and classifies each finding as `drift` for Phase 7 to route."""
    text = DREAM_PROMPT.read_text()

    assert "### Phase 3 — contract audit" in text
    assert "contract audit" in text
    assert "decide-half complement to Phase 1" in text
    assert "living contract surface" in text
    assert "`drift`" in text
    # The three sources of truth the audit checks claims against.
    assert "code reality" in text
    assert "referenced artifacts" in text
    assert "copy divergence" in text
    # Frozen task artifacts are not contracts.
    assert "Frozen task artifacts under `relay-os/tasks/` are historical" in text
    # Phase 7 disposition routes `drift` findings to a proposal PR.
    assert "Every Phase 2 and Phase 3 finding gets a durable home" in text
    assert "- `drift` — open a proposal PR" in text


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
    norm = " ".join(text.split())

    assert "## Known Skill Contract" in text
    assert "- Purpose: detect already-processed done tickets" in text
    assert "- Action: `pr-required`" in text
    assert "`bootstrap/delete-task`" in text
    assert "exact `status: done`" in text
    assert "`skill: retro/done-ticket`" in text
    assert "`status: processed`" in text
    assert "`result: no-new-durable-knowledge`" in text
    assert "not a prefix match" in text
    assert "reports eligible candidates as `human-needed`" in norm


def test_skill_update_worker_declares_contract() -> None:
    text = (TEMPLATES / "skill-update" / "SKILL.md").read_text()
    norm = " ".join(text.split())

    assert "## Known Skill Contract" in text
    assert "- Purpose: update clean imported skills" in text
    assert "- Action: `pr-required`" in text
    assert "relay skill update --all --pr" in text
    assert "`relay/skill-update` branch" in norm
    assert "never the caller's branch" in norm
    assert "Bundled (package-backed) skills are not updated here" in norm
    assert "- Output: append `## Dream Skill: skill-update`" in text
    assert "RELAY_TASK_BLACKBOARD" in text
    assert "--blackboard" not in text


def test_rem_template_documents_user_specific_recurring_maintenance() -> None:
    text = REM_TEMPLATE.read_text()

    assert "REM is repo/user-specific recurring maintenance" in text
    assert "REM is not Dream" in text
    assert "Dream is Relay's generic ticket cleanup pass" in text
    assert "copy or rename it to a non-underscore" in text
    assert "product or operations health checks" in text
    assert "domain-specific recurring reports" in text
    assert "Do not put generic Relay cleanup here" in text
