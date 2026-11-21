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
    text = RETRO_SKILL.read_text(encoding="utf-8")
    norm = " ".join(text.split())

    assert "name: retro/done-ticket" in text
    assert "prompt-only Codex skill" in text
    assert "knowledge-extraction gate for" in text
    assert "every eligible done ticket Dream passes in a" in text
    assert "## Known Skill Contract" in text
    assert "delete every processed source task" in text
    assert "`pr-required` for knowledge edits and the source-task deletions" in text
    assert "`direct-delete` for\n  unreferenced no-durable-knowledge source tasks" in text
    assert "resolve `<contexts-dir>` once from `[layout] contexts`" in text
    assert "local `<contexts-dir>/**/SKILL.md`" in text
    assert "snapshot-local `<contexts-dir>/**/SKILL.md`" in text
    assert "local `coga/contexts/**/SKILL.md`" not in text
    assert "package\n  `bootstrap/contexts/**/SKILL.md`" in text
    assert "read every skill file under local `coga/skills/**/SKILL.md`" in text
    assert "package\n  `bootstrap/skills/**/SKILL.md`" in text
    assert "from importlib.resources import files" in text
    assert "Load the snapshot and\n  packaged corpus once before ticket-by-ticket extraction" in text
    assert "This skill is invoked with one or more parameters: exact done ticket slugs" in text
    assert "the skill partitions them into coherent PR" in norm
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


def test_retro_repoints_inbound_references_before_deleting() -> None:
    text = RETRO_SKILL.read_text(encoding="utf-8")
    norm = " ".join(text.split())

    # A durable link to a deleted ticket must not land on the control branch.
    assert "### Inbound references" in text
    assert "git grep -n -F -e '<tasks-root>/<slug>'" in text
    assert "':!<tasks-root>' ':!<coga-os>/log.md'" in text
    assert "-e '<task-leaf>'" in text
    assert "../tasks/<task-leaf>.md" in text
    assert "resolve relative targets from the referring file" in norm
    assert "Honor the repository's search restrictions" in norm
    assert "Existing commit permalinks already preserve the source" in norm
    assert "commit permalink of the fresh control-branch tip" in norm
    assert "Never add a new live-tree link to a source task you are deleting" in norm
    assert "land a deletion that leaves a live-tree reference to the deleted task" in norm

    # Knowledge-bearing sources repoint in their knowledge PR; referenced
    # no-knowledge sources leave in one reference-pin PR, not by direct delete.
    assert "Repointed files do not count toward the per-PR knowledge-file limit" in norm
    assert "it does not take the direct delete" in norm
    assert "one reference-pin PR" in norm
    assert "`codex/retro-pin-references-<run-id>`" in text
    assert "pr <theme | pin-references>" in text
    assert "- Repointed references:" in text
    assert "Re-run the inbound-reference search against each branch" in norm


def test_retro_reference_pin_route_has_no_markers_or_shared_run_branch() -> None:
    norm = " ".join(RETRO_SKILL.read_text(encoding="utf-8").split())

    assert "Never reuse another run's branch" in norm
    assert "its Source omits the Markers bullet (there are no markers)" in norm
    assert "direct-deleted tickets and any reference-pin PR" in norm
    assert "otherwise it leaves in the reference-pin PR" in norm
