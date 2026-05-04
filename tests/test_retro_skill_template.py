from __future__ import annotations

from pathlib import Path


RETRO_SKILL = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "relay"
    / "resources"
    / "templates"
    / "relay-os"
    / "skills"
    / "retro"
    / "done-ticket"
    / "SKILL.md"
)


def test_retro_done_ticket_is_prompt_only_context_extraction_skill() -> None:
    text = RETRO_SKILL.read_text()

    assert "name: retro/done-ticket" in text
    assert "prompt-only Codex skill" in text
    assert "read every context file under `relay-os/contexts/**/SKILL.md`" in text
    assert "Do not:" in text
    assert "create or edit skills" in text
    assert "delete the source ticket directory" in text
    assert "delete local or remote git branches" in text
    assert "Process knowledge" in text
    assert "Open the PR" in text
    assert "Retro <ticket-slug>: extracted context PR <url>" in text
