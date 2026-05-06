from __future__ import annotations

from pathlib import Path


BOOTSTRAP_TICKET_SKILL = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "relay"
    / "resources"
    / "templates"
    / "relay-os"
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
