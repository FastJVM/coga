from __future__ import annotations

from pathlib import Path


RETRO_SKILL = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "coga"
    / "resources"
    / "templates"
    / "coga"
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
    assert "delete every processed source task" in text
    assert "`pr-required` for knowledge edits and the source-task deletions" in text
    assert "`direct-delete` for no-durable-knowledge source tasks" in text
    assert "read every context file under local `coga/contexts/**/SKILL.md`" in text
    assert "package\n  `bootstrap/contexts/**/SKILL.md`" in text
    assert "read every skill file under local `coga/skills/**/SKILL.md`" in text
    assert "package\n  `bootstrap/skills/**/SKILL.md`" in text
    assert "from importlib.resources import files" in text
    assert "loaded once per run before ticket-by-ticket\n  extraction" in text
    assert "This skill is invoked with one or more parameters: exact done ticket slugs" in text
    assert "the skill partitions them into coherent PR" in text
    assert "Do not:" in text
    assert "running in-memory delta" in text
    assert "## Retro" in text
    assert "status: processed" in text
    assert "result: knowledge-pr" in text
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
    assert "Record the Retro markers for knowledge-bearing tickets." in text
    assert "The title should carry the new finding." in text
    assert "`New context: <finding>` or `New skill: <finding>`" in text
    assert "Tickets: deleted `<task-dir>`, ..." in text
    assert "Markers: PR history for each deleted ticket records its `## Retro`" in text
    assert "`<PR title>. PR: <url>`" in text


def test_retro_requires_subagent_worktree_isolation() -> None:
    """Retro branches and direct-deletes only inside an auto-cleaned worktree.

    Both callers own creating that boundary. The skill must fail loud when the
    boundary is missing instead of switching the operator's primary checkout.
    """
    text = RETRO_SKILL.read_text()
    norm = " ".join(text.split())

    assert "subagent with `isolation: worktree`" in norm
    assert "Stop immediately if the caller did not provide worktree isolation" in norm
    assert "primary checkout's branch, index, and uncommitted files" in norm
    assert "Every `git checkout` and `coga delete` command" in norm
    assert "automatic worktree cleanup" in norm
    assert "Work in the current checkout — do not create a `git worktree`." not in text


def test_retro_deletes_every_processed_done_ticket() -> None:
    """Every done ticket Retro processes is deleted, but by two different
    routes. A ticket that carries durable knowledge is deleted inside its
    theme's reviewable knowledge PR (the marker recorded in the same PR). A
    ticket with no durable knowledge has no PR to bundle the deletion into, so
    it is direct-deleted via `coga delete` — no PR, no marker, no `## Pruned`
    bookkeeping. A processed done ticket never survives the run on disk."""
    text = RETRO_SKILL.read_text()

    # Knowledge-bearing tickets stay bundled: extracted + deleted in one PR.
    assert "theme's knowledge PR" in text
    assert "delete its directory in the same knowledge" in text

    # Knowledge-less tickets are direct-deleted, not bundled into any PR.
    assert "A source task with no new durable knowledge is still deleted" in text
    assert "is direct-deleted via `coga delete`" in text
    assert "`coga delete <slug>`" in text
    assert "no marker, no PR" in text
    assert "gets **no** marker" in text
    assert "git restore" in text
    assert "leaves a processed done ticket on disk" in text
    assert "a processed done ticket should not\nsurvive the run." in text

    # Idempotency: a surviving marked directory is no longer "settled".
    assert "the task directory is gone, or an open PR" in text
    assert "processed `## Retro` marker on a still-present" in text
    assert "Retro re-picks it for deletion." in text

    # The forbidden moves: marker-only PR, and any PR for a no-knowledge ticket.
    assert "open a marker-only PR" in text
    assert "no `## Pruned` bookkeeping" in text
    assert "open any\n  PR at all for a no-durable-knowledge ticket" in text

    # The old bundled-deletion machinery is gone.
    assert "delete-only prune PR" not in text
    assert "folded into a knowledge PR" not in text
    assert "no-new-durable-knowledge" not in text
