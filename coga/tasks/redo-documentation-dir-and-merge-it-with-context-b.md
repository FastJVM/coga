---
slug: redo-documentation-dir-and-merge-it-with-context-b
title: redo documentation dir and merge it with context blocks
status: draft
owner: nicktoper
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/design-then-implement
secrets: null
---

## Description

Rebuild Coga's documentation from the ground up by auditing and consolidating
the current documentation and context blocks. Contexts are generally the more
accurate starting material, but duplication, drift, missing explanations, and
oversized files all need review. Make the `docs/` tree the shared source of
knowledge for humans and agents, using the existing TOML setting to point Coga
at it and splitting the material into small, focused files. Agree the pitch,
proposed structure, and removal list with the owner before the rewrite.

### Required sequence and outcomes

1. **Audit before restructuring.** Inventory `docs/`, README, live contexts,
   and bundled contexts (including package-only entries). Map each topic to its
   current sources, contradictions, missing coverage, proposed canonical home,
   and disposition: retain, merge, split, rewrite, or remove. Check behavioral
   claims against current source/tests and distinguish shipped behavior from
   proposals, historical decisions, and marketing claims.
2. **Design for selective reading.** Propose a browsable documentation tree
   and index with one authoritative home per fact. Split long contexts by
   coherent topic; keep the essential explanation short and link to detailed
   internals when needed. Preserve useful contracts and edge cases through
   the split. Tickets must be able to load the particular files they need
   without loading the entire documentation set.
3. **Review the pitch and cuts.** Bring the owner a concise proposed pitch,
   the proposed tree, a gap list, and a reasoned removal/merge list. Review
   README, vision, market-thesis, and marketing contexts together. Repeated
   philosophy, obsolete history, and competitor discussion are candidates to
   assess, not preapproved deletions. The `review-design` gate settles the
   pitch and migration design before implementation.
4. **Rebuild and repoint.** Rewrite and consolidate the approved material in
   the documentation tree. Use the existing `[layout] contexts` setting and
   supported context file/ref format. Update navigation, agent instructions,
   task/template context refs, and other maintained consumers to the new
   canonical locations. Remove superseded explanations after their useful
   content and references have been accounted for.
5. **Verify the resulting knowledge path.** Check coverage against the audit,
   links and refs, and that representative task prompts resolve the new split
   files with the intended contents and reasonable prompt sizes. Keep shipped
   context/template counterparts and their packaging checks consistent with
   the new layout. Record actual validation commands and any remaining gaps.

### Scope

This is a documentation consolidation and adoption of an existing configuration
capability in Coga's own repo. A new Markdown loader, new context primitive,
global default change for other repos, and general CLI/feature cleanup are
outside scope. Skills retain their role as process knowledge. If the audit
finds a product defect or work too large for one reviewed change, propose
focused follow-up work instead of silently expanding this ticket.

## Context

- **Use the existing relocation feature.** `docs/concepts.md`, "Contexts and
  skills", documents `[layout] contexts = "docs/contexts"`. The path is
  relative to the Git checkout root. `config.Config.contexts_root` and
  `config._parse_layout` implement it; `paths.context_path` currently expects
  `<contexts_root>/<ref>/SKILL.md`, and `paths.resolve_context_path` resolves
  local-first with bundled fallback. Pick the exact directory during design;
  a human-readable documentation tree does not require changing this format.
- **Config cutover has an existing ownership boundary.** Coga launch
  instructions prohibit agents from editing `coga.toml` or `coga.local.toml`.
  The design must give the owner the exact TOML edit and its place in the
  migration sequence, then verify the applied configuration. The configured
  directory participates in Coga Git sync and is removed by `coga uninstall`;
  choose its scope deliberately rather than treating it as just a read path.
  Explain how automatic state sync affects publication relative to owner PR
  review when scheduling the cutover.
- **Starting corpus.** `docs/README.md` is the current index;
  `coga/contexts/coga/` holds the behavioral explanations;
  `coga/contexts/marketing/` holds positioning and launch material. Inspect
  other live context namespaces when classifying the complete corpus.
  `src/coga/resources/templates/coga/bootstrap/contexts/` includes shipped
  copies and package-only `coga/cli`. `docs/vision.md` and
  `docs/market-thesis.md` are pitch inputs. Preserve current behavioral rules
  while resolving conflicting explanations; the owner settles product intent.
- **Splitting is central.** At authoring, architecture was 1,179 lines, sync
  1,058, and recurring 868. Avoid replacing those with equally large manuals
  or duplicating a short agent version beside a long human version. Use small
  topic files and links. Attachments are prompt payload, so update ticket
  selections when a broad context becomes several narrow ones.
- **Consumers and distribution.** Inspect `compose.py`, `paths.py`,
  `validate.py`, `authoring.py`, Git state sync, init/uninstall behavior,
  `AGENTS.md`, `CLAUDE.md`, repo/base prompts, workflows, skills, recurring
  templates, and task context refs for affected assumptions. `tests/test_packaging.py`
  derives live/package pairs from their paths; moving a live copy can remove
  it from that comparison without a failure. Preserve a verifiable pairing or
  another explicit distribution/sync contract for relocated shipped material.
  Update affected `example/` fixtures. These are migration touchpoints, not a
  mandate to redesign those components.
  The old-to-new topic/ref map must account for automatic attachments and
  bundled fallback so maintained consumers do not silently load stale content.
- **Related work to reconcile.** The completed
  `move-cogacontext-to-roodoc-so-its-easier-for-human` delivered the setting.
  `the-human-doc-vs-agent-context-boundary-is-decided`,
  `v2/docs-and-contt-block-should-be-merged`, and
  `v2/split-context-to-doc-user-accessible-and-editable` overlap this effort;
  the last still describes Relay and only the base context file. Audit their
  remaining requirements rather than treating old proposals as current design.
  `no-context-records-the-ci-posture-publish-only-rel` is a concrete gap input:
  release CI builds/publishes without running pytest, a distinction missing
  from the current codebase context. Check related tickets again at launch.
- **Verification scope.** Use `coga validate --json`, targeted prompt reports
  and composed-prompt inspection, and link/ref checks for the migration.
  Run the relevant packaging/fixture tests and any tests needed by actual code
  changes; prose alone does not require a full Python test run.
- **Workflow and payload.** `code/design-then-implement` supplies design,
  independent evaluation, an owner design gate, implementation, PR creation,
  and owner review. Use the seeded agent `claude` for the first design step.
  No broad contexts are
  attached: the corpus is the subject of the audit and should be read by topic.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Ticket authoring notes

### Interview and initial audit (2026-09-08)

- Human intent: rebuild the documentation from the ground up, using existing
  context blocks as the generally more accurate starting material. Audit first,
  find missing knowledge, remove stale material, and merge the explanation into
  documentation that agents can discover directly. Repoint Coga to consume that
  documentation. Discuss the pitch and what to cut before settling the rewrite.
- Human correction: use the existing TOML relocation feature; splitting the
  files is essential. The ticket now scopes this to rebuilding this repo's
  documentation with the supported format, not a new loader or global default.
- Two competing explanation surfaces are explicit: `docs/concepts.md` defers to
  the principles and architecture contexts; `docs/vision.md` defers to principles;
  `marketing/positioning` instead defers to vision and market-thesis. Audit each
  claim against source/tests and current owner decisions; contexts are useful
  inputs, not assumed infallible.
- Size snapshot: 13 pages in `docs/`; architecture is 1,179 lines, sync 1,058,
  recurring 868. `docs/market-thesis.md` is about 60 KB and vision about 31 KB.
  A move alone will preserve duplication and costly prompt payloads. Candidate
  shape: small topic pages with one authoritative home per fact and a clear index.
- Repointing uses existing behavior: `[layout] contexts` is unset in this repo.
  Retain `<contexts_root>/<ref>/SKILL.md`. Account for consumer refs, packaged
  twins, and the directory's existing sync/uninstall ownership when planning
  the move. No source/config changes are made during ticket authoring.
- Related work to reconcile in the eventual audit: completed
  `move-cogacontext-to-roodoc-so-its-easier-for-human`; draft
  `the-human-doc-vs-agent-context-boundary-is-decided`; deferred
  `v2/docs-and-contt-block-should-be-merged` and
  `v2/split-context-to-doc-user-accessible-and-editable`. The last still describes
  Relay paths and only the base `context.md`, so it is historical input.
- Concrete coverage gap already ticketed: `no-context-records-the-ci-posture-publish-only-rel`.
  The checked-in release workflow builds/publishes without running pytest;
  the codebase context's test instructions omit that distinction.
- Pitch inputs: README leads with parallel agent operations and owned state;
  vision with company OS/philosophy/field report; market-thesis with taste and
  operations-as-code; positioning pins the internal OSS field-report direction.
  Candidate cuts include repeated philosophy, competitor discussion, and obsolete
  history, but preserve active behavioral contracts and obtain the human's
  editorial direction before deciding.
- Selected workflow: `code/design-then-implement` (design, independent
  evaluation, owner design gate, implement, open-pr, owner review). Agents:
  claude and codex; draft assignee set to the seeded agent claude to run the
  first design step (activation freezes the workflow but does not resolve a
  human draft assignee to its first agent role). No extension fields configured.
  Owner/human/agent fields preserved; no implementation or lifecycle transition.

## Evaluator review

No must-fix authoring defects remain in the updated draft. The first design step is actionable: audit the named corpus, reconcile behavioral claims, propose a topic tree and dispositions, and prepare the pitch and migration for owner review. `code/design-then-implement` fits this sequence; its bundled workflow provides independent evaluation and an owner gate before implementation (`src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md`). Setting `assignee: claude` makes the first assignment explicit.

The relocation feature is accurately described. `src/coga/config.py::Config.contexts_root` and `_parse_layout` implement checkout-relative `[layout] contexts`; `src/coga/paths.py::context_path` retains `<root>/<ref>/SKILL.md`, and `resolve_context_path` uses local-first bundled fallback. The ownership consequences are real: `src/coga/git.py::_coga_state_pathspecs` includes the relocated directory, and `src/coga/commands/uninstall.py::_execute_plan` removes it. The config-edit restriction appears in `src/coga/resources/prompt.md`.

The empty context attachment list is appropriate: the material being audited is large, and the body supplies concrete reading pointers. No necessary broad context attachment is missing. The packaging warning is also correct: `tests/test_packaging.py::_live_counterparts` maps to `coga/`, so relocated copies can disappear from twin comparison. The release-workflow observation matches `.github/workflows/release.yml`.

Decisions intentionally deferred to design should remain explicit gate outputs: the exact destination, canonical topic/ref map, owner-approved pitch and cuts, treatment of existing task refs and bundled fallback, and the replacement pairing contract. The migration sequence should explain when owner configuration changes occur and how automatic state sync affects publication relative to PR review. These are design responsibilities, not reasons to block authoring. The scope is substantial but coherent; the existing requirement to propose follow-ups if it exceeds one reviewed change is sufficient.

No supplied prompt layer exceeds roughly 40%: the largest is the base prompt at approximately 32.6%. Recheck after design composition and required authoring-blackboard cleanup; this draft report omits the workflow-step payload.
