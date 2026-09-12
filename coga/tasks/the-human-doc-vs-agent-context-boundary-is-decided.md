---
title: The human-doc vs agent-context boundary is decided per ticket and recorded
  nowhere
status: in_progress
owner: nicktoper
agent: claude
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 3 (open-pr)
---

## Description

Coga carries two overlapping explanation surfaces — `docs/*.md` for humans and
`coga/contexts/**/SKILL.md` for agents — and the question of which one a given piece of
knowledge belongs in is re-opened by ticket after ticket, with no durable answer.

Deliverable: state the boundary somewhere an author will find it — most likely
`coga/contexts/coga/architecture/SKILL.md`, which already owns what a context *is* and how
composition consumes it.

The rule needs to answer at least: what belongs in `docs/` only, what belongs in a context
only, what legitimately appears in both and therefore needs a sync rule, and how an author
decides for a new fact. Whether the answer is a rule or an explicit "these overlap and here
is how to choose" is itself the design question.

## Context

Citations name symbols and files, not line numbers.

Several open tickets are each a local instance of the same unresolved boundary:

- `coga/tasks/v2/split-context-to-doc-user-accessible-and-editable.md`
- `coga/tasks/v2/docs-and-contt-block-should-be-merged.md`
- `coga/tasks/redo-documentation-dir-and-merge-it-with-context-b.md`
- `coga/tasks/move-cogacontext-to-roodoc-so-its-easier-for-human.md` (done — it moved the
  contexts directory and added the `[layout] contexts` key, but did not settle what goes
  where)

Concrete evidence that the boundary is unsettled in the artifacts themselves: Dream
2026-W36 found the same prompt-composition rule stated in `docs/concepts.md` and in
`coga/contexts/coga/architecture/SKILL.md`, **both stale and stale differently** — the doc
had the layer order wrong, the context wrongly implied the whole ticket body composes. Two
copies of one fact, drifting independently, is the cost this ticket is about.

A second instance from the same run: `coga/contexts/coga/extension-model/SKILL.md` inlines
~450 words that `coga/contexts/coga/launch-internals/SKILL.md` owns, without referencing
it — the same duplication problem *within* the context layer.

Design inputs worth weighing:

- Contexts are **composed into prompts** and therefore cost tokens on every launch;
  `docs/` costs nothing until a human opens it. That asymmetry should drive the rule.
- `coga/contexts/coga/cli/SKILL.md` does not exist live; the `coga/cli` context is
  package-only and resolves through the bootstrap fallback in `paths.resolve_context_path`.
  So "every context has a live copy" is already false, and the rule must accommodate that.
- `docs/vision.md` is named by `CLAUDE.md` as the product thesis, and
  `docs/cli-extension-audit.md` is cited by both `CLAUDE.md` and the extension-model
  context as the live command inventory — so some docs are already load-bearing *for
  agents*, which complicates a clean "docs are for humans" split.

Filed by Dream 2026-W36, Phase 2 knowledge scan (shard `ks-12`), classified `gap`.

<!-- coga:blackboard -->

## Dev

pr: https://github.com/FastJVM/coga/pull/790
branch: doc-context-boundary
worktree: /home/n/Code/claude/coga-doc-context-boundary

## Findings (implement, 2026-09-11)

- Nothing today names an owner for a fact. `CLAUDE.md` says "update the
  matching context *or* source doc"; `docs/concepts.md` calls itself "the
  human-readable tour of the same ideas" — both license the duplication that
  drifted.
- The only mechanical sync rule (`tests/test_packaging.py` byte-identity) is
  live↔package. Docs↔context can never be byte-identical, so that boundary
  must be an authoring rule; Dream's knowledge scan is the backstop that found
  the drift in the first place.
- Markdown links are not composition: a context naming `docs/cli-extension-audit.md`
  does not load it; the agent reads it on disk. So a context is *eager*
  knowledge (paid on every launch) and a doc is *lazy* knowledge (paid when
  opened, by human or agent). That makes the "load-bearing docs" cases
  consistent with a docs/contexts split rather than exceptions to it.
- `coga/tasks/redo-documentation-dir-and-merge-it-with-context-b.md` is
  `in_progress` at its owner `review-design` gate and proposes collapsing the
  two surfaces into one `docs/contexts/**` library with a `coga/knowledge`
  context. If that lands, the rule written here re-homes there.

## Decisions (owner, attended session 2026-09-11)

- Write the rule for **today's layout** (`docs/` + `coga/contexts/`); do not
  presume the redo-documentation merge. The eager/lazy framing carries over if
  it lands.
- Overlap policy: a human doc may **summarize and link**, never carry
  specification-grade detail (ordered lists, exact names/numbers). One owner
  per fact; the same-PR grep is the sync rule.
- Home: new `## Where a fact lives: docs vs contexts` section in
  `coga/architecture` after `## Prompt composition`; pointer lines in
  `CLAUDE.md`/`AGENTS.md`, `coga/contexts/_template/SKILL.md`,
  `docs/README.md`, `docs/development.md`, and `coga/codebase`.

## What changed (commit `3860f406` on `doc-context-boundary`)

- `coga/contexts/coga/architecture/SKILL.md` (+ packaged twin): new section
  `## Where a fact lives: docs vs contexts` after `## Prompt composition`.
  Eager (context) vs lazy (doc) framing; one owner per fact; three-step
  decision procedure; "pointers and summaries, never the specification" as
  the only legitimate overlap, applied within the context layer too; same-PR
  grep as the sync rule with Dream's scan as backstop; package-only contexts
  (`coga/cli`) and `CLAUDE.md`/`AGENTS.md` placed explicitly. Frontmatter
  `description` widened so the section is discoverable.
- Pointers: `CLAUDE.md`/`AGENTS.md` Read First, `coga/contexts/_template`
  (+ twin), `docs/README.md` (new `## Docs versus contexts`),
  `docs/development.md`, `coga/codebase` file list (+ twin).
- Rule applied to the cited drift: `docs/concepts.md` prompt-composition
  section is now a summary + link; its "tour of the same ideas" framing now
  says the contexts own the rules.
- Verification: `python -m pytest` → 2435 passed; `coga validate --json`
  issues are the same pre-existing task-state warnings as on `main`
  (none touch changed files).

## Follow-ups (not done here)

- `coga/contexts/coga/extension-model/SKILL.md` still inlines material
  `coga/launch-internals` owns (ticket's second instance). Rewriting it to a
  pointer is a separate cleanup now that the rule names the fix.
- `coga/tasks/redo-documentation-dir-and-merge-it-with-context-b.md` (owner
  gate) proposes a `coga/knowledge` context; if approved, this section moves
  there. `coga/tasks/v2/document-contexts-as-prompt-payload-not-tags-princ`
  overlaps with the eager/lazy framing and may be closable against it.

## Peer review

- `codex review --base main` **returned** successfully against `3860f406` in
  the recorded feature worktree. The first attempt could not initialize its
  app-server on the sandbox's read-only filesystem; the escalated rerun
  completed. It reported one P2: the starter names a repo-local architecture
  path that is absent after normal initialization.
- Fixed the P2 in both starter copies: name the logical `coga/architecture`
  context and explain how attaching it resolves the local or packaged owner.
  Manual review also removed the full layer enumeration still present in the
  `docs/concepts.md` prose, linked its summary to the owning section, and
  corrected `docs/README.md` to say contexts compose when attached.
- Ran `git fetch origin main && git rebase FETCH_HEAD` unconditionally in the
  feature worktree; it completed without conflicts onto `f85c0e40`, rewriting
  the implementation commit as `56a4df24`. All three changed live/package
  pairs and `AGENTS.md`/`CLAUDE.md` still match byte-for-byte. A fresh-scaffold
  smoke check confirmed that the starter's logical ref resolves the packaged
  ownership rule while the repo-local architecture file is absent.
- `coga validate --task the-human-doc-vs-agent-context-boundary-is-decided
  --json` passed with no issues. The review's targeted tests had 130 passes
  and one environment failure because the ambient Python lacks `hatchling`.
  The full suite with the repo's declared test tools supersedes that failure:
  `PYTHONPATH=/home/n/Code/claude/coga-doc-context-boundary/src /home/n/Code/claude/coga/.venv/bin/python -m pytest`
  passed **2435 tests**, including the wheel build, after the rebase and fixes.
- Committed the corrections as `e90557b9` (`peer-review: apply documentation
  findings`). The feature worktree is clean, `git diff --check` passes, and the
  branch has two commits ahead of `origin/main`. No must-fix findings remain.

## PR

`coga/architecture` now defines one owner per fact: contexts carry knowledge
needed in the prompt, while docs hold material read on demand. The rule covers
permitted summaries and links, same-PR synchronization, overlap between
contexts, and package-only owners.

Author entrypoints and the context starter point to this rule, and
`docs/concepts.md` links to the canonical prompt-composition specification
instead of maintaining a layer list. The starter works with packaged contexts;
all changed live and packaged copies stay synchronized.

Test plan: `PYTHONPATH=/home/n/Code/claude/coga-doc-context-boundary/src /home/n/Code/claude/coga/.venv/bin/python -m pytest` (2435 passed); `coga validate --task the-human-doc-vs-agent-context-boundary-is-decided --json` (no issues); fresh-scaffold fallback and byte-identity checks passed.
