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
    assert "read-only `evidence/` snapshot" in " ".join(text.split())
    assert "writable `progress.md` alongside `evidence/`, not inside it" in " ".join(text.split())
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
    assert (
        "Every Phase 1 `pr-proposal` or `human-needed` issue and every Phase 2 "
        "and Phase 3 finding gets a durable home"
    ) in " ".join(text.split())
    assert "- `drift` — open a proposal PR" in text


def test_dream_routes_every_finding_class_to_a_durable_home() -> None:
    """Phase 6 closes the three routing holes the 2026-W36 run hit: Phase 1
    `human-needed` issues had no route past the blackboard, `extract` findings
    whose source ticket is not Retro-eligible fell through, and nothing stopped
    a shard from refiling a gap an earlier run had already ticketed."""
    text = DREAM_PROMPT.read_text()
    norm = " ".join(text.replace("**", "").split())
    scan_text = (SCAN_TEMPLATES / "knowledge-scan" / "SKILL.md").read_text()
    scan_norm = " ".join(scan_text.split())
    drift_text = (TEMPLATES / "validate-drift" / "SKILL.md").read_text()
    drift_norm = " ".join(drift_text.split())

    # Phase 1 tells the reader its buckets are Phase 6 inputs, not results.
    assert "`human-needed` issues are routed to hygiene draft tickets" in norm
    assert "an issue left only there was never reported" in norm

    # Hole 1: one ticket per validator kind, deduplicated by a greppable tag,
    # with machine-local kinds kept out of the ticket corpus.
    assert "one draft ticket per systematic class, never one per issue" in norm
    assert "`validate-drift: <kind>`" in text
    assert "--workflow brief-for-human" in text
    assert "`missing-user`, `unset-secret-env`, `slack-*`, `github-*`" in norm
    assert "They get no ticket" in norm
    assert "`coga validate --json` is the live member list" in norm
    assert "Membership is not copied from run to run" in norm
    assert "## Where `human-needed` goes" in drift_text
    assert "`human-needed` is a classification, not a destination" in drift_norm
    assert "`validate-drift: <kind>`" in drift_text

    # Hole 2: `extract` routes on the source ticket's Retro standing, which
    # the shard records, and retirement debt is reported, not re-copied.
    for source in ("`source: done`", "`source: done+checkout`", "`source: canceled`"):
        assert source in scan_text
    assert "`done+checkout` — the source ticket is retirement debt" in norm
    assert "Open no PR and file no carrier ticket" in norm
    assert "retirement is its consumer" in norm
    assert "`canceled` — Retro refuses a ticket that is not `done`" in norm
    assert "Open a proposal PR that edits the target context or skill" in norm
    assert "a done or canceled ticket holds durable knowledge" in scan_norm
    assert "abandoned design is not durable knowledge" in scan_norm

    # Hole 3: both halves — the shard searches for an owner before emitting a
    # gap, and Phase 6 reconciles again with the whole corpus in view.
    assert "check whether the gap already has an owner" in scan_norm
    assert "not only your shard's paths" in scan_norm
    assert "`owner: <slug>`" in scan_text
    assert "Still write the finding" in scan_norm
    assert "reconcile against open tickets before creating anything" in norm
    assert "Phase 6 repeats the search with the whole corpus in view" in norm
    assert "already ticketed as `<slug>`" in text
    assert "Dream does not edit another ticket's body or blackboard" in norm

    # Filing rules: top level only, greppable provenance, and the summary
    # carries what was not filed and why.
    assert "Dream never files under `coga/tasks/v2/`" in norm
    assert "so a later run can find the owner by grep" in norm
    assert "every `already ticketed as` line" in norm
    assert "the retirement-debt list with the `extract` findings each retirement unlocks" in norm


def test_dream_re_validates_parked_drafts_every_run() -> None:
    """The v2 parking area's premise check used to fire only when a human
    pulled a draft forward. Dream's knowledge scan owns every ticket in-shard,
    so it asks the README's four questions of every parked draft each run and
    Phase 6 batches the failures into one adjudication draft — a question for
    the human, never a cancellation by Dream."""
    repo_root = Path(__file__).resolve().parents[1]
    text = DREAM_PROMPT.read_text()
    norm = " ".join(text.replace("**", "").split())
    scan_text = (SCAN_TEMPLATES / "knowledge-scan" / "SKILL.md").read_text()
    scan_norm = " ".join(scan_text.split())
    protocol_text = (SCAN_TEMPLATES / "scan-protocol" / "SKILL.md").read_text()
    readme_text = (repo_root / "coga" / "tasks" / "v2" / "README.md").read_text()
    readme_norm = " ".join(readme_text.replace("**", "").split())
    lifecycle_text = (
        repo_root / "docs" / "contexts" / "coga" / "lifecycle" / "SKILL.md"
    ).read_text()
    lifecycle_norm = " ".join(lifecycle_text.split())

    # The README owns the four questions and names Dream as the standing owner.
    assert "Four questions, in this order:" in readme_text
    assert "Does the draft carry the substance it depends on?" in readme_norm
    assert "a draft must carry the substance it depends on in its own body" in readme_norm
    assert "Has something else already delivered it?" in readme_norm
    assert "### Who runs the check while a draft sits" in readme_text
    assert "The standing owner is Dream" in readme_norm

    # A delivered duplicate can be canceled directly from draft, even without
    # a workflow. The CLI refuses `mark done` from draft.
    assert 'coga mark canceled v2/<slug> --message "already delivered by' in readme_norm
    assert "coga mark done v2/<slug>" not in readme_norm

    # The shard runs the check and records a `premise` finding, never a verdict.
    assert "## Parked drafts: the standing premise pass" in scan_text
    assert "If `coga/tasks/v2/README.md` is absent, skip this pass" in scan_norm
    assert "continue the rest of the knowledge scan" in scan_norm
    assert "A terminal (`done` or `canceled`) ticket is no longer a parked draft" in scan_norm
    assert "every parked draft your shard owns" in scan_norm
    assert "`premise`" in scan_text
    assert "`question: <subject | surfaces | citations | delivered>`" in scan_text
    assert "Write findings, never verdicts" in scan_norm
    assert "emit nothing for it here" in scan_norm
    assert "- class: <extract | stale | gap | premise | drift>" in protocol_text

    # Required external substance is flagged before Retro deletes a live
    # source; self-contained drafts may keep retired provenance.
    assert "Provenance-only citations are not premise failures" in readme_norm
    assert "required substance absent from the draft's own body" in readme_norm
    assert "even while the source ticket still exists" in readme_norm
    assert "even when the source ticket still exists" in scan_norm
    assert "before Phase 4 can delete it in this same run" in scan_norm
    assert "provenance-only citations are not failures" in scan_norm
    assert "must not make the finding recur" in scan_norm

    # Phase 6 routes the class to one brief-for-human draft per run and
    # reconciles against earlier runs' adjudication drafts first.
    assert "each `premise` finding's `target:`, `question:`, and `owner:` lines" in norm
    assert "`premise` — a parked draft under `coga/tasks/v2/` failed" in norm
    assert "The verdict is the author's, never Dream's" in norm
    assert "never one ticket per draft" in norm
    assert '`coga create "Premise check <period>: <N> parked drafts need a verdict"' in norm
    assert "the run's premise adjudication draft included" in norm

    # coga/lifecycle owns the green-validate guard; the parking README links
    # to it and applies it without maintaining a second specification.
    guard = '"Clears a validate error" is not a cancellation reason'
    assert guard not in readme_norm
    assert "### The green-validate guard" in readme_text
    assert (
        "../../../docs/contexts/coga/lifecycle/SKILL.md#status-whether-work-happens"
        in readme_text
    )
    assert lifecycle_norm.count(guard) == 1
    assert "A terminal transition is a verdict about the ticket" in lifecycle_norm


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
    # `progress.md` is append-only and shared, so a duplicated completion line
    # must not inflate coverage; reconciliation is over the id set, and it
    # happens only once every shard has returned.
    assert "set of distinct shard ids" in norm
    assert "Count distinct shard ids, never completion lines" in norm
    assert "a shard can append its completion line more than once" in norm
    assert "the number of lines in the file is not the number of shards" in norm
    assert "Reconcile at the barrier, never while shards are still reporting" in norm
    assert "A shard that goes idle after writing its completion line has finished" in norm
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
    assert "Reconcile only at the barrier" in norm
    assert "set of distinct shard ids" in norm
    assert "Count distinct shard ids, never completion lines" in norm
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


def test_dream_sharding_updates_the_dream_contract() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    live = repo_root / "docs" / "contexts" / "coga" / "dream" / "SKILL.md"
    packaged = (
        RESOURCES
        / "templates"
        / "coga"
        / "bootstrap"
        / "contexts"
        / "coga"
        / "dream"
        / "SKILL.md"
    )
    text = live.read_text()
    norm = " ".join(text.replace("**", "").split())

    assert live.read_bytes() == packaged.read_bytes()
    assert "bounded shard subagents" in norm
    assert "set of distinct shard ids" in norm
    assert "never by counting lines" in norm
    assert "One retry, then `partial`" in norm
    assert "`no-op`, `reported`, `partial`, `proposed`" in norm


def test_dream_keeps_coga_owned_files_out_of_a_client_repo_scan() -> None:
    """In a client repo Dream must not audit the installed Coga OS files as if
    they were the client's own knowledge: identity is decided once, Rule A is
    applied while writing `index.md`, and a Coga-owned conclusion from a
    client file goes upstream instead of becoming a local edit."""
    protocol_text = (SCAN_TEMPLATES / "scan-protocol" / "SKILL.md").read_text()
    protocol = " ".join(protocol_text.split())
    knowledge = " ".join(
        (SCAN_TEMPLATES / "knowledge-scan" / "SKILL.md").read_text().split()
    )
    audit = " ".join(
        (SCAN_TEMPLATES / "contract-audit" / "SKILL.md").read_text().split()
    )
    dream_text = DREAM_PROMPT.read_text()
    dream = " ".join(dream_text.replace("**", "").split())

    # Repo identity: one test, evaluated once, recorded in the index.
    assert "## Repo identity" in protocol_text
    assert "`<checkout-root>/src/coga/resources/templates/coga/` is a directory" in protocol
    assert "repo-identity: client | coga-source" in protocol_text
    assert "Nothing re-derives it" in protocol
    for skill in (knowledge, audit):
        assert "Repo identity" in skill
        assert "re-derive" in skill
        assert "templates/coga/` is a directory" not in skill

    # Rule A: the derivation is the packaging test's twin mapping, per file,
    # applied once at index time, under the interpreter that backs `coga`.
    assert "### Rule A — path ownership in a client repo" in protocol_text
    assert "per file, not per directory" in protocol
    assert "`templates/coga/<rel>` → `coga/<rel>`" in protocol
    assert (
        "`templates/coga/bootstrap/<contexts|skills|workflows>/<rel>` → "
        "`coga/<contexts|skills|workflows>/<rel>`"
    ) in protocol
    assert "must not exclude a client's own sibling under `coga/skills/direct/`" in protocol
    for seed in (
        '"coga/coga.toml"', '"coga/log.md"', '"coga/context.md"', '"coga/.gitignore"',
        '"coga/.gitattributes"', '"coga/contexts/.gitignore"',
        '"coga/recurring/digest/spool.md"',
    ):
        assert seed in protocol_text
    assert 'parts[0] == "tasks"' in protocol_text
    assert 'files("coga.resources").joinpath("templates", "coga")' in protocol_text
    assert "COGA_PY=$(python3 -c 'from pathlib import Path; from shutil import which;" in protocol_text
    assert "A non-zero exit is a failed scan, never an empty owned set" in protocol
    assert "as it writes `index.md`" in protocol
    assert "excluded-coga-owned: <N>" in protocol_text
    assert "When `repo-identity: coga-source`, Rule A is not applied" in protocol
    assert "repo-identity: client | coga-source" in dream_text
    assert "subtract the Rule A owned-path list from the corpus as you write the index" in dream
    assert "excluded-coga-owned: <N>" in dream_text
    assert "In the Coga source repo apply no exclusion" in dream
    assert "add no filter of your own" in knowledge

    # Rule B: code reality is the client's own code; Coga claims are not local
    # findings, and `owner: coga` never proposes a local edit anywhere.
    assert "### Rule B — source-of-truth ownership" in protocol_text
    assert "- owner: <local | coga>" in protocol_text
    assert "defaults to `local`" in protocol
    assert "`coga` is a reserved value" in protocol
    assert "code reality means the client's own code" in " ".join(audit.replace("**", "").split())
    assert "not checkable there and not a local finding" in " ".join(audit.replace("**", "").split())
    assert "Do not invent a `drift` from a Coga claim you cannot verify" in audit
    for skill in (protocol, knowledge, audit):
        assert "never proposes a local edit" in skill

    # Phase 4: the mark reaches Retro and stops only the Coga-owned fact.
    assert "Pass `## Findings` to Retro as it stands, `owner: coga` lines included" in dream
    assert "must not write that fact into a local context or skill" in dream
    assert "contributes the local one and still gets deleted" in dream
    retro = " ".join(
        (DREAM.parents[1] / "retro" / "done-ticket" / "SKILL.md").read_text().split()
    )
    assert "### Coga-owned findings are not local knowledge" in retro
    assert "Do not write that fact into a local context or skill" in retro
    assert "contributes the local fact and is deleted like any other" in retro

    # Phase 6: upstream capture with a parseable, append-only entry shape.
    assert "Coga-owned findings go upstream, whatever their class" in dream
    assert "<checkout-root>/coga/upstream-coga.md" in dream_text
    assert "not routed to a proposal PR, a draft ticket, or a local knowledge edit" in dream
    assert "# Upstream Coga findings" in dream_text
    for line in (
        "- id: 2026-09-09-phase-6-names-a-dead-recipe",
        "- repo: multiply",
        "- date: 2026-09-09",
        "- class: drift",
        "- target: coga/recurring/dream/ticket.md",
        "- evidence: coga/contexts/multiply/developer-flow/SKILL.md:44",
    ):
        assert line in dream_text
    assert "`id` is `<YYYY-MM-DD>-<slug-of-title>`, suffixed `-2`, `-3`" in dream
    assert "The file is append-only: never reorder, rewrite, or remove an entry" in dream
    assert "`upstream-captured`" in dream_text
    assert "the number of entries appended to `coga/upstream-coga.md`" in dream
    assert "In the Coga source repo no `owner: coga` finding arises" in dream
    # The example entry is indented so its `## <title>` cannot end the
    # template's `## Description` section under compose's plain `^##` regex.
    assert "\n## <title>" not in dream_text
    assert "\n  ## <title>" in dream_text
    # The live twin is enforced by test_packaging; the vocabulary reaches the
    # coga/dream contract too.
    dream_contract = " ".join(
        (RESOURCES.parents[2] / "docs" / "contexts" / "coga" / "dream" / "SKILL.md")
        .read_text()
        .split()
    )
    assert "`human-needed`, `upstream-captured`" in dream_contract
    assert "`coga/upstream-coga.md`" in dream_contract


def test_retro_checks_a_done_tickets_scope_reached_the_control_branch() -> None:
    retro = " ".join(
        (DREAM.parents[1] / "retro" / "done-ticket" / "SKILL.md").read_text().split()
    )
    assert "### Done is a status, not a receipt" in retro
    assert "against the current files of the isolated checkout" in retro
    assert "do not extract its claimed fix, and do not cite it as delivered" in retro
    assert "| Unshipped scope |" in retro
    assert "- Unshipped scope: <ticket, missing scope, and target context" in retro
    assert "every unshipped scope is preserved as required above" in retro
    lifecycle = " ".join(
        (RESOURCES.parents[2] / "docs" / "contexts" / "coga" / "lifecycle" / "SKILL.md")
        .read_text()
        .split()
    )
    assert "`retro/done-ticket` checks the scope against the tip" in lifecycle
