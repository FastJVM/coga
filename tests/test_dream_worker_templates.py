from __future__ import annotations

from pathlib import Path


TEMPLATES = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "coga"
    / "resources"
    / "templates"
    / "coga"
    / "bootstrap"
    / "skills"
    / "bootstrap"
    / "dream"
    / "tasks"
)

DREAM = TEMPLATES.parent
SCAN_TEMPLATES = DREAM / "scan"
RESOURCES = Path(__file__).resolve().parents[1] / "src" / "coga" / "resources"
RECURRING_TEMPLATES = (
    RESOURCES / "templates" / "coga" / "recurring"
)
# Dream is a recurring task template, not a built-in command. Its body lives
# in the recurring template's `## Description` section.
DREAM_PROMPT = RECURRING_TEMPLATES / "dream" / "ticket.md"
# Single-file format: the recurring template's blackboard is the region of
# `ticket.md` below the `<!-- coga:blackboard -->` fence (no separate file).
DREAM_BLACKBOARD = DREAM_PROMPT
REM_TEMPLATE = RECURRING_TEMPLATES / "_rem" / "ticket.md"


def test_dream_ships_as_a_recurring_template() -> None:
    """Dream is a recurring task template, not a built-in command. The body
    lives in the template's `## Description` section so `create_task` picks
    it up the same way it does for any other recurring template."""
    text = DREAM_PROMPT.read_text()

    assert text.startswith("---\n")
    assert "schedule:" in text
    assert 'title: "Dream"' in text
    assert "mode:" not in text
    assert "\n## Description\n" in text


def test_dream_documents_decide_then_execute_phases() -> None:
    text = DREAM_PROMPT.read_text()

    assert not (DREAM / "SKILL.md").exists()
    assert not (DREAM / "scan.py").exists()
    assert not (TEMPLATES / "dev" / "stale-branches" / "SKILL.md").exists()
    assert "Run the Dream cleanup pass for this Coga repo" in text
    assert "Dream is Coga's generic cleanup pass" in text
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
    assert "Dream runs six phases in order" in text
    assert "`bootstrap/dream/tasks/validate-drift`" in text
    # The skill updater is a standalone recurring task now, not a Dream phase.
    assert "skill-update" not in text
    assert "retro/done-ticket" in text
    assert "`bootstrap/dream/tasks/cleanup-orphan-markers`" in text
    assert "`bootstrap/dream/tasks/dev/stale-branches`" not in text
    assert "dev/stale-branches" not in text
    assert "### Skill: dev/stale-branches" not in text
    assert "knowledge scan" in text
    assert "`bootstrap/dream/scan/knowledge-scan`" in text
    assert "`bootstrap/dream/scan/contract-audit`" in text
    assert "`extract`" in text
    assert "`stale`" in text
    assert "`gap`" in text
    assert "coga create" in text
    assert "no per-run ticket cap" in text
    assert "Extract durable knowledge from done tickets, then delete every one of them." in text
    assert "its resolved task directory under `coga/tasks/` still exists" in text
    assert "Retro never leaves a processed done ticket on" in text
    assert "Delegate the entire Retro pass to one subagent with" in text
    assert "`isolation: worktree`" in text
    assert "Do not run Retro in Dream's checkout" in text
    # Knowledge-less tickets are direct-deleted, not bundled into a prune PR.
    assert "is direct-deleted with" in text
    assert "`coga delete <slug>`" in text
    assert "with no PR and no marker" in text
    assert "delete-only prune PR" not in text
    assert "## Pruned" not in text
    assert "Dream-owned scripts\nare skills attached to Coga tasks" in text
    assert "--blackboard" not in text
    assert "Dream Run Summary" in text
    assert "coga slack --task <this-dream-task>" in text
    assert "stale branch" not in text.lower()
    assert "coga/skills/dream/orchestrate/SKILL.md" not in text
    assert "tasks/**/SKILL.md" not in text


def test_dream_and_scheduler_cleanup_done_recurring_tickets() -> None:
    """Dream cleans this sweep; the scheduler replaces stale completed runs."""
    text = DREAM_PROMPT.read_text()
    # Prose wraps across lines; normalize whitespace and bold markers so phrase
    # assertions don't depend on where the line breaks fall.
    norm = " ".join(text.replace("**", "").split())

    # Phase 4 cleans completed recurring tasks produced earlier in this sweep.
    assert "A done `recurring/<name>` ticket from this sweep is eligible" in norm
    assert "Retro direct-deletes them via `coga delete recurring/<name>`" in norm

    # The scanner is the liveness fallback: it deletes an unreaped completed
    # artifact before creating the next period's fresh task. Dream therefore
    # never needs to reactivate or self-delete its predecessor.
    assert "the recurring scanner deletes it before creating" in norm
    assert "The previous Dream run is removed by that scanner fallback" in norm

    # Phase 6 marks the Dream task done and STOPS — it must not self-delete.
    assert "do not delete this task" in norm
    assert "the recurring scanner deletes that prior-period artifact" in norm
    assert "creates a fresh Dream task from this template" in norm
    # The old self-delete instruction is gone.
    assert "coga delete <this-dream-task>" not in text
    assert "Dream cleans up after itself in the same run" not in text

    from coga.taskfile import read_blackboard

    blackboard = read_blackboard(DREAM_BLACKBOARD)
    blackboard_norm = " ".join(blackboard.split())
    assert "Dream's per-period task is disposable after it is marked done" in blackboard_norm
    assert "Dream keeps no durable state here" in blackboard_norm
    assert "not delete itself mid-run" in blackboard_norm
    assert "deletes itself" not in blackboard
    assert "self-deleted" not in blackboard


def test_dream_documents_the_knowledge_scan_skill() -> None:
    """Phase 2 delegates the reusable taxonomy/corpus/output contract to a
    prompt-only Dream scan skill."""
    text = DREAM_PROMPT.read_text()
    skill_text = (SCAN_TEMPLATES / "knowledge-scan" / "SKILL.md").read_text()
    skill_norm = " ".join(skill_text.split())

    assert "### Phase 2 — knowledge scan" in text
    assert "`bootstrap/dream/scan/knowledge-scan`" in text
    assert "Classify each finding as exactly one of:" not in text
    assert "single full-corpus read of the run" in skill_norm
    assert "every ticket body and blackboard" in skill_norm
    assert "every context, skill, and workflow file" in skill_norm
    assert "`extract`" in skill_text
    assert "`stale`" in skill_text
    assert "`gap`" in skill_text
    assert "raw ticket and blackboard contents stay inside the subagent" in skill_norm
    assert "Group the `extract` findings" in skill_norm
    assert "script:" not in skill_text
    assert "## Known Skill Contract" not in skill_text


def test_dream_documents_the_contract_audit_phase() -> None:
    """Phase 3 is a dedicated consistency audit: a subagent checks the living
    contract surface (contexts, skills, recurring templates, shipped docs)
    against code reality, missing artifacts, and live/packaged copy drift,
    and classifies each finding as `drift` for Phase 6 to route."""
    text = DREAM_PROMPT.read_text()
    skill_text = (SCAN_TEMPLATES / "contract-audit" / "SKILL.md").read_text()
    skill_norm = " ".join(skill_text.split())

    assert "### Phase 3 — contract audit" in text
    assert "contract audit" in text
    assert "`bootstrap/dream/scan/contract-audit`" in text
    assert "decide-half audit complements" in text
    assert "decide-half complement to Phase 1" in skill_norm
    assert "living contract surface" in skill_norm
    assert "`drift`" in skill_text
    # The three sources of truth the audit checks claims against.
    assert "code reality" in skill_text
    assert "referenced artifacts" in skill_text
    assert "copy divergence" in skill_text
    # Frozen task artifacts are not contracts.
    assert "Frozen task artifacts under `coga/tasks/` are historical" in skill_text
    assert "script:" not in skill_text
    assert "## Known Skill Contract" not in skill_text
    # Phase 6 disposition routes `drift` findings to a proposal PR.
    assert "Every Phase 2 and Phase 3 finding gets a durable home" in text
    assert "- `drift` — open a proposal PR" in text


def test_validate_drift_worker_declares_contract() -> None:
    text = (TEMPLATES / "validate-drift" / "SKILL.md").read_text()

    assert "## Known Skill Contract" in text
    assert "- Purpose: deterministic repo-health validation" in text
    assert "- Action: `direct-fix`" in text
    assert "- May change: a missing `<!-- coga:blackboard -->` fence + blackboard region" in text
    assert "- Idempotency: `coga validate --fix`" in text
    assert "- Output: append `## Dream Skill: validate-drift`" in text
    assert "COGA_TASK_BLACKBOARD" in text
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


def test_rem_template_documents_user_specific_recurring_maintenance() -> None:
    text = REM_TEMPLATE.read_text()

    assert "REM is repo/user-specific recurring maintenance" in text
    assert "REM is not Dream" in text
    assert "Dream is Coga's generic ticket cleanup pass" in text
    assert "copy or rename it to a non-underscore" in text
    assert "product or operations health checks" in text
    assert "domain-specific recurring reports" in text
    assert "Do not put generic Coga cleanup here" in text
