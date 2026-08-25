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
    assert "`coga run validate-drift`" in text
    # The skill updater is a standalone recurring task now, not a Dream phase.
    assert "skill-update" not in text
    assert "retro/done-ticket" in text
    assert "`bootstrap/dream/tasks/cleanup-orphan-markers`" in text
    assert "`coga run cleanup-orphan-markers`" in text
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
    assert "Extract durable knowledge from done tickets, then delete every eligible one." in text
    assert "its resolved task directory under `coga/tasks/` still exists" in text
    assert "has no real `branch:` or `worktree:` value" in " ".join(text.split())
    assert "leave the ticket and its `## Dev` evidence on disk" in " ".join(text.split())
    assert "do not invoke `coga retire` from Dream" in " ".join(text.split())
    assert "Retro never leaves a processed done ticket on" in " ".join(text.split())
    assert "Delegate the entire Retro pass to one subagent in a dedicated" in text
    assert "`isolation: worktree`" in text
    assert "`git worktree add`" in text
    assert "`git clone --no-hardlinks`" in text
    assert "primary `.git` metadata read-only" in " ".join(text.split())
    assert "Fetch the configured remote control branch first" in text
    assert "unique temporary branch on that fresh tip" in " ".join(text.split())
    assert "Do not run Retro in Dream's checkout" in " ".join(text.split())
    assert "gitignored `coga.local.toml`" in text
    assert "same repo-relative path" in " ".join(text.split())
    assert "never symlink, snapshot, stage, or commit it" in " ".join(text.split())
    assert "read-only temporary\nevidence snapshot" in text
    assert "including sibling attachments" in " ".join(text.split())
    assert "current `## Findings`" in text
    assert "`coga delete <slug> --keep-control-checkout`" in text
    assert "ordinary `coga delete <slug>` from an independent clone" in " ".join(text.split())
    assert "delete the exact independent-clone" in " ".join(text.split())
    assert "auto-clean" not in text
    # Knowledge-less tickets are direct-deleted, not bundled into a prune PR.
    assert "is direct-deleted with" in text
    assert "`coga delete <slug> --keep-control-checkout`" in text
    assert "with no PR and no marker" in " ".join(text.split())
    assert "delete-only prune PR" not in text
    assert "## Pruned" not in text
    assert "Do not create child worker tasks" in text
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
    # Direct-delete is the default, not the rule: the blackboard decides. Both
    # halves are asserted so neither can drift away on its own.
    assert (
        "Retro normally direct-deletes them via `coga delete recurring/<name>`"
        in norm
    )
    assert "never direct-delete on the ticket's class alone" in norm

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
    # The scan covers the whole corpus, but as bounded shards: a single
    # full-corpus read is larger than a subagent can hold, and the run that
    # tried it returned no findings at all.
    assert "It is the single full-corpus read of the run" not in skill_norm
    assert "bounded shards, not one sweep" in skill_norm
    assert "every ticket body and blackboard" in skill_norm
    assert "every context, skill, and workflow file" in skill_norm
    assert "`bootstrap/dream/scan/scan-protocol`" in skill_text
    # The de-duplication tradeoff the sharding costs is stated, while the
    # required ticket-vs-knowledge comparison is preserved inside area shards.
    assert "merge-time de-duplication compares titles, targets, and paragraphs" in skill_norm
    assert "both sides of the comparison in each shard" in skill_norm
    assert "Do not create disjoint ticket-only and knowledge-only shard groups" in skill_norm
    assert "For every ticket it includes path, bytes, slug, title, status" in skill_norm
    assert "the index entry alone is not evidence" in skill_norm
    assert "at least two independent tickets" in skill_norm
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
    # The audit shards too, and copy divergence checks explicit counterpart
    # pairs instead of diffing intentionally different trees.
    assert "bounded shards, not one sweep" in skill_norm
    assert "`bootstrap/dream/scan/scan-protocol`" in skill_text
    assert "`IDENTICAL_LIVE_PACKAGED_PAIRS`" in skill_text
    assert "compare each pair with `cmp`" in skill_norm
    assert "recursive diff" in skill_norm
    assert "diff -r coga/ src/coga/resources/templates/coga/" not in skill_text
    assert "never read it whole" in skill_norm
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
    assert "coga run validate-drift" in text
    assert "script: run.py" not in text
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
    assert "coga run cleanup-orphan-markers" in text
    assert "script: run.py" not in text


def test_dream_scans_stream_durable_findings_and_report_completion() -> None:
    """Both decide-half scans deliver findings through an on-disk file and end
    with an explicit per-shard completion line, so Dream can tell "scan ran,
    found nothing" from "scan never returned"."""
    protocol = (SCAN_TEMPLATES / "scan-protocol" / "SKILL.md").read_text()
    norm = " ".join(protocol.split())

    assert protocol.startswith("---\n")
    assert "name: bootstrap/dream/scan/scan-protocol" in protocol
    assert "## Known Skill Contract" not in protocol
    assert "script:" not in protocol

    # Findings land on disk as they are decided, never only in a final message.
    assert "the moment you decide it" in norm
    assert "Never accumulate findings in context to emit at the end" in norm
    assert "`findings.md`" in protocol
    assert "`progress.md`" in protocol
    assert "It does not parse your final message" in norm
    assert "Dream initializes all four as empty regular files" in norm
    assert (
        "`findings.md` therefore exists even when every shard reports zero findings"
        in norm
    )

    # An explicit zero is a result; a missing line is not.
    assert "<shard-id> complete — <N> findings" in protocol
    assert "`0 findings` is a real result" in norm
    assert "A shard that writes no line at all is treated as a shard that never returned" in norm
    assert "<shard-id> incomplete —" in protocol

    # Bounded reading is what makes a shard finishable.
    assert "150 KB" in protocol
    assert "owned and evidence paths together" in norm
    assert "Never read a file over 60 KB whole" in norm
    assert "Never read `coga/log.md` whole" in norm
    assert "find <paths> -type f -name '*.md' -exec wc -c {} \\;" in protocol
    assert "find -printf" in protocol

    # Retry children supersede an incomplete parent, so successful leaves can
    # reconcile without waiting for the failed parent to complete.
    assert "supersede <parent-id> -> <child-id>" in protocol
    assert "leaf assignments" in norm
    assert "reconciliation checks only those leaves" in norm.lower()
    assert "A superseded parent's late completion" in norm
    assert "phase's finding total comes from the de-duplicated `findings.md`" in norm
    assert "including durable findings written by a parent" in norm
    assert "Supersession changes coverage expectations, never delivery" in norm


def test_dream_shards_and_reconciles_the_scan_phases() -> None:
    """Dream sizes the corpus, shards it, and reconciles launched shards
    against completion lines before believing a scan's result."""
    text = DREAM_PROMPT.read_text()
    norm = " ".join(text.replace("**", "").split())

    assert "### Decide-half scan mechanics (Phases 2 and 3)" in text
    assert "bounded shards writing durable findings to disk" in norm
    assert "`bootstrap/dream/scan/scan-protocol`" in text
    assert "mktemp -d" in text
    assert "manifest.md" in text and "index.md" in text
    assert "Immediately create all four as empty regular files" in norm
    assert (
        "`findings.md` must exist even when every shard reports zero findings" in norm
    )
    assert "no more than 150 KB across at most 40 distinct files" in norm
    assert "Compare the active leaf shard rows" in norm
    assert "Do not treat a missing line as zero findings" in norm
    assert "supersede <parent> -> <children>" in norm
    assert "retry those leaves once" in norm
    assert "de-duplicated findings across all attempts total zero" in norm
    assert "the phase result is `partial`" in norm
    assert "de-duplicating across shards" in norm
    # `partial` joins the run-summary vocabulary so an incomplete scan is
    # visible in the summary instead of reading as a clean run.
    assert "`no-op`, `reported`, `partial`, `proposed`" in norm
    assert "how many shards were launched and how many wrote a completion line" in norm
    # A sharded scan still covers the whole corpus before Phase 4 deletes
    # done-ticket evidence.
    assert "sharded corpus read; classifies every finding" in text


def test_dream_sharding_updates_the_architecture_contract() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    live = repo_root / "coga" / "contexts" / "coga" / "architecture" / "SKILL.md"
    packaged = (
        RESOURCES
        / "templates"
        / "coga"
        / "bootstrap"
        / "contexts"
        / "coga"
        / "architecture"
        / "SKILL.md"
    )
    text = live.read_text()
    norm = " ".join(text.split())

    assert live.read_bytes() == packaged.read_bytes()
    assert "two sharded subagent scans" in norm
    assert "retry-supersession rules" in norm
    assert "reconciles only active leaf assignments" in norm
    assert "`no-op`, `reported`, `partial`, `proposed`" in norm
