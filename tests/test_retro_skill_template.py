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
    assert "every eligible done ticket Dream passes in a" in text
    assert "## Known Skill Contract" in text
    assert "delete every processed source task directory through a reviewable PR" in text
    assert "`pr-required` — every knowledge edit and every source-task deletion" in text
    assert "read every context file under `relay-os/contexts/**/SKILL.md` and" in text
    assert "`relay-os/bootstrap/contexts/**/SKILL.md`" in text
    assert "read every skill file under `relay-os/skills/**/SKILL.md` and" in text
    assert "`relay-os/bootstrap/skills/**/SKILL.md`" in text
    assert "loaded once per run before ticket-by-ticket\n  extraction" in text
    assert "This skill is invoked with one or more parameters: exact done ticket slugs" in text
    assert "the skill partitions them into coherent PR" in text
    assert "Do not:" in text
    assert "running in-memory delta" in text
    assert "## Retro" in text
    assert "status: processed" in text
    assert "result: <knowledge-pr | no-new-durable-knowledge>" in text
    assert "delete local or remote git branches" in text
    assert "Repeatable process knowledge" in text
    assert "Inventory skills once." in text
    assert "Maintain the running delta." in text
    assert "Partition the run into coherent PR batches." in text
    assert "there is no per-run ticket cap" in text
    assert "five source tickets" in text
    assert "touch at most three knowledge files" in text
    assert "need \"and\" in the PR title" in text
    assert "Update an existing skill, or create a focused skill if none fits." in text
    assert "Record the Retro markers." in text
    assert "The title should carry the new finding." in text
    assert "Prefer\n   `New context: <finding>` or `New skill: <finding>`" in text
    assert "Tickets: deleted `relay-os/tasks/<slug>/`, ..." in text
    assert "Markers: PR history for each deleted `blackboard.md` records `## Retro`" in text
    assert "`<PR title>. PR: <url>`" in text


def test_retro_deletes_every_processed_done_ticket() -> None:
    """Every done ticket Retro processes is deleted via a reviewable PR — the
    ones that carry durable knowledge in a knowledge PR, the ones that do not
    folded into a knowledge PR or pruned in a single delete-only PR. A
    processed done ticket never survives the run on disk."""
    text = RETRO_SKILL.read_text()

    # No processed ticket is left on disk; no marker-only PR is ever opened.
    assert "A source task with no new durable knowledge is still deleted" in text
    assert "leaves a processed done ticket on disk and never opens a marker-only PR" in text
    assert "a processed done ticket should not survive the run." in text
    assert "delete every processed source task directory" in text
    assert "Delete every processed source task." in text

    # Idempotency: a surviving marked directory is no longer "settled".
    assert "for each source task, the task directory is gone" in text
    assert "processed `## Retro` marker on a still-present directory does not settle the" in text
    assert "task — Retro re-picks it for deletion." in text

    # No-durable tickets are folded into a knowledge PR, or pruned in one PR.
    assert "## Pruned" in text
    assert "Tickets with no new durable knowledge are not a batch theme" in text
    assert "delete each no-new-durable-knowledge source task by folding its directory" in text
    assert "inside a single delete-only prune PR" in text
    assert "open exactly one delete-only prune PR carrying" in text
    assert "That task is still deleted — its" in text
    assert "one delete-only prune PR titled `Prune done tickets with no durable" in text
    assert "Delete-only prune PR (opened only when the run produced no knowledge PR)" in text

    # The forbidden move is a marker-only PR; prunings are never split.
    assert "open a marker-only PR — a PR whose only change is a blackboard `## Retro`" in text
    assert "split no-new-durable-knowledge prunings across more than one PR" in text

    # The old "leave the directory in place / open no PR" rule is gone.
    assert "do not open a PR solely for that marker" not in text
    assert "leave the\n   source task directory in place" not in text
