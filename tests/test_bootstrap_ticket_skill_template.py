from __future__ import annotations

from pathlib import Path


BOOTSTRAP_TICKET_SKILL = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "coga"
    / "resources"
    / "templates"
    / "coga"
    / "bootstrap"
    / "skills"
    / "bootstrap"
    / "ticket"
    / "SKILL.md"
)


def test_bootstrap_ticket_context_selection_is_prompt_payload() -> None:
    text = BOOTSTRAP_TICKET_SKILL.read_text()

    assert "Treat `contexts:` as prompt payload, not labels." in text
    assert "Attach only context refs whose full body" in text
    assert "Do not attach broad orientation contexts by default." in text
    assert "copy that specific fact into\n  the ticket's `## Context` body" in text
    assert "create or propose a smaller\n  focused context" in text
    assert "Select them through the workflow's step\n  `skill:` refs" in text
    assert "If only a specific fact is needed, put\n   it in `## Context`" in text
    assert "only writes the draft bytes to disk and does **not** run this skill." in text
    assert "are you starting a\n> **new** ticket, or editing an **existing** one?" in text


def test_bootstrap_ticket_skill_mandates_a_workflow() -> None:
    """Guided authoring defaults to landing the ticket on a workflow — a
    workflow-less ticket can't be activated. The one exception is a deliberate
    concept-capture draft, which stays a draft until a workflow is added."""
    text = BOOTSTRAP_TICKET_SKILL.read_text()

    assert "A ticket carries a workflow" in text
    assert "A ticket with no workflow can't be\nactivated" in text
    assert "your default is to hand back a ticket\nwith one" in text
    # The concept-capture exemption is stated, not erased.
    assert "concept-capture" in text
    assert "This is required — a ticket with no workflow can't be activated." in text


def test_bootstrap_ticket_selects_workflow_without_autonomy_triage() -> None:
    text = BOOTSTRAP_TICKET_SKILL.read_text()
    lower = text.lower()

    assert "3. **Workflow**" in text
    assert "irreversible or outward-facing step" in text
    assert "pick a workflow with a human gate" in text
    assert "autonomy triage" not in lower
    assert "autonomy tier" not in lower
    assert "autonomy/" not in lower


def test_bootstrap_ticket_greets_off_kickoff_token_not_body() -> None:
    """Regression: the create-vs-edit greeting keys off the CLI-set kickoff
    token, not body-emptiness — so a `coga create`d empty draft opened for
    editing greets as an edit, never as a freshly-created ticket."""
    text = BOOTSTRAP_TICKET_SKILL.read_text()

    # The greeting keys off the kickoff token the CLI sets, per launch shape.
    assert "kickoff token" in text
    assert "`Begin (new ticket)`" in text
    assert "`Begin (editing existing ticket)`" in text
    # The old body-emptiness heuristic is gone.
    assert "an **empty**\n`## Description`/`## Context` body means new" not in text
    # The existing-but-empty edit path is spelled out: greet as an edit, fill
    # from scratch, don't announce a creation.
    assert "even if its body is" in text
    assert 'never announce it "has been created"' in text


def test_bootstrap_ticket_cleanup_preserves_non_draft_blackboards() -> None:
    text = BOOTSTRAP_TICKET_SKILL.read_text()

    assert "If the ticket is still `status: draft`, reset" in text
    assert "If editing an existing non-draft ticket" in text
    assert "preserve unrelated blackboard content such as blockers" in text
    assert "remove only the authoring\n   sections you used" in text


def test_bootstrap_ticket_skill_documents_script_backed_authoring() -> None:
    text = BOOTSTRAP_TICKET_SKILL.read_text()
    normalized = " ".join(text.split())

    workflow_question = text.index("**Workflow**")
    script_question = text.index("**Script execution (conditional)**")
    context_question = text.index("**Contexts to attach**")
    assert workflow_question < script_question < context_question
    assert "Only ask this when the task actually looks script-shaped" in normalized
    assert "4–6 questions" in text
    assert "it runs on **every** workflow step" in normalized
    assert (
        "compatible only with a workflow that has exactly one step and no "
        "`requires:` completion gate" in normalized
    )
    assert "put the script on a skill wired only to the intended workflow step" in normalized

    assert "`script: inline`" in text
    assert "`## Script`" in text
    assert "above the `<!-- coga:blackboard -->` fence" in normalized
    assert "keep the flat `coga/tasks/<slug>.md` draft in place" in normalized
    assert "Use `python`, `sh`, or `bash` as the fence language" in normalized
    assert "`coga validate` does not resolve or parse ticket-owned scripts" in normalized

    assert "`script: <filename>`" in text
    assert "`coga/tasks/<slug>.md`" in text
    assert "`coga/tasks/<slug>/ticket.md`" in text
    assert "The frontmatter `slug:` does not change" in normalized
    assert "`chmod +x`" in text
    assert "`coga validate --task <slug>`" in text
    assert "`test -f <actual-task-directory>/<filename>`" in text
    assert "Validation does not resolve the script reference" in normalized

    assert (
        "Execution: <agent | script: inline (<language>) | "
        "script: <filename> (sibling)>" in text
    )
