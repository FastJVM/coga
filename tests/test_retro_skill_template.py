from __future__ import annotations

from pathlib import Path


RETRO_SKILL = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "relay"
    / "resources"
    / "templates"
    / "relay-os"
    / "bootstrap"
    / "skills"
    / "retro"
    / "done-ticket"
    / "SKILL.md"
)


def test_retro_done_ticket_is_prompt_only_knowledge_extraction_skill() -> None:
    text = RETRO_SKILL.read_text()

    assert "name: retro/done-ticket" in text
    assert "prompt-only Codex skill" in text
    assert "knowledge-extraction gate for" in text
    assert "## Known Skill Contract" in text
    assert "`pr-required` for knowledge edits" in text
    assert "`direct-fix` for a\n  no-new-durable-knowledge marker only" in text
    assert "the source task is gone" in text
    assert "the source task blackboard contains a\n  `## Retro` section" in text
    assert "`skill: retro/done-ticket` and `status: processed`" in text
    assert "read every context file under `relay-os/contexts/**/SKILL.md`" in text
    assert "read every skill file under `relay-os/skills/**/SKILL.md`" in text
    assert "This skill is invoked with one parameter: the done ticket slug" in text
    assert "Do not:" in text
    assert "when new durable knowledge exists, delete the source ticket directory" in text
    assert "delete any task directory except the exact source ticket directory" in text
    assert "## Retro" in text
    assert "status: processed" in text
    assert "result: <knowledge-pr | no-new-durable-knowledge>" in text
    assert "delete local or remote git branches" in text
    assert "Repeatable process knowledge" in text
    assert "Inventory skills." in text
    assert "Update an existing skill, or create a focused skill if none fits." in text
    assert "Record the Retro marker." in text
    assert "status: processed" in text
    assert "result: <knowledge-pr | no-new-durable-knowledge>" in text
    assert "If no durable knowledge is found, write the marker" in text
    assert "leave `relay-os/tasks/<slug>/` in\n   place, and do not open a PR" in text
    assert "marker-only or delete-only PR" in text
    assert "Open the PR" in text
    assert "The title should carry the new finding." in text
    assert "Prefer\n   `New context: <finding>` or `New skill: <finding>`" in text
    assert "If the only change\n   would be the blackboard marker, do not open a PR." in text
    assert "Ticket: deleted `relay-os/tasks/<slug>/`" in text
    assert "Marker: PR history for `relay-os/tasks/<slug>/blackboard.md` records `## Retro`" in text
    assert "`<PR title>. PR: <url>`" in text
