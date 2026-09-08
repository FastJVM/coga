---
slug: redo-documentation-dir-and-merge-it-with-context-b
title: redo documentation dir and merge it with context blocks
status: active
owner: nicktoper
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (design)
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
   without loading the entire documentation set. Define representative
   file-size and composed-prompt checks during design, including which task
   selections will demonstrate selective loading.
3. **Review the pitch and cuts.** Bring the owner a concise proposed pitch,
   the proposed tree, a gap list, and a reasoned removal/merge list. Review
   README, vision, market-thesis, and marketing contexts together. Repeated
   philosophy, obsolete history, and competitor discussion are candidates to
   assess, not preapproved deletions. The `review-design` gate settles the
   pitch and migration design before implementation: the destination and
   topic/ref map, old-ref and bundled-fallback treatment, distribution/pairing
   contract, and publication/cutover sequence must all be explicit.
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
  This repo currently has `[layout] contexts` unset.
- **Config cutover has an existing ownership boundary.** Coga launch
  instructions prohibit agents from editing `coga.toml` or `coga.local.toml`.
  The design must give the owner the exact edit to `coga/coga.toml` and its
  place in the migration sequence, then verify the applied configuration.
  The configured directory participates in Coga Git sync and is removed by
  `coga uninstall`;
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
- **Pitch inputs and authority.** `docs/concepts.md` defers to the principles
  and architecture contexts; `docs/vision.md` defers to principles, while
  `marketing/positioning` defers to vision and market-thesis. README emphasizes
  parallel agent operations and owned state; vision covers the company OS and
  its philosophy; market-thesis covers taste and operations-as-code; positioning
  pins the internal OSS/field-report direction. Reconcile these inputs and
  their authority claims through the owner pitch review.
- **Splitting is central.** At authoring, architecture was 1,179 lines, sync
  1,058, and recurring 868; market-thesis was about 60 KB and vision 31 KB.
  Avoid replacing those with equally large manuals
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
  No broad contexts are attached: the corpus is the subject of the audit and
  should be read by topic.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
