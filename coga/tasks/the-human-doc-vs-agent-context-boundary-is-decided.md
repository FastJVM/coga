---
slug: the-human-doc-vs-agent-context-boundary-is-decided
title: The human-doc vs agent-context boundary is decided per ticket and recorded
  nowhere
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
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
secrets: null
step: 1 (implement)
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

The blackboard is a notepad to be written to often as the human and agent works through a task.
