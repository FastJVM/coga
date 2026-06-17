---
title: Single-file task format + section-aware compose filter
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
  - relay/architecture
  - relay/codebase
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (design)
---

## Description

Replace the three-file-per-task layout (`ticket.md` + `blackboard.md` +
`log.md`) with a **single file per task** that holds frontmatter plus
delimited sections, and add a **section-aware compose filter** so the prompt
composer loads only the working sections and never the append-only audit
history.

Today the three-file split encodes the composition boundary for free: compose
does a plain read of `blackboard.md` and simply never reads `log.md`, so the
unbounded audit trail never enters a prompt. Merging into one file removes that
free boundary — the composer must now parse the file and pull only the working
sections, skipping the (still unbounded) log section **without loading it into
memory or the prompt**. That section-aware reader is the crux of this work.

Scope:

1. **Format** — define the single-file layout: YAML frontmatter, the body
   sections (`## Description`, `## Context`), the working/blackboard section,
   and the append-only audit/log section, each with stable, machine-findable
   delimiters the filter can split on.
2. **Compose filter** — `compose.py` reads only frontmatter + body + working
   section; the audit section is excluded. The reader must be able to skip the
   audit section cheaply even as it grows large (stream/seek to the section,
   don't read-then-discard).
3. **Writers** — every command that writes ticket/blackboard/log today
   (`draft`, `bump`, `mark`, `launch`-time transitions, `panic`, `slack`,
   recurring/retire creating) moves to section-scoped writes/appends in the
   one file.
4. **Reads / surfaces** — `relay show`, `validate`, and task discovery read the
   new format.
5. **Migration** — a one-shot migration for all existing task directories
   (~96) and recurring/bootstrap dirs into the new format. Bootstrap shims have
   no blackboard/log, so handle their reduced shape.
6. **Docs** — rewrite every place that teaches the three-file model:
   `relay/architecture` (primitives, prompt composition, "log never composed"),
   the base prompt, `relay/cli`, README, and `docs/spec.md`. Behavior change
   and its context must land in the same PR.

Accepted tradeoff (owner decision): the audit history now lives inside the
composed file, so the filter — not a separate file — is what keeps it out of
the prompt. This trades the "dumbest legible version" (read one file, ignore
another) for a section parser; the design step must keep that parser legible
and fail-loud (a malformed/unsplittable file must error, never silently drop
the working section).

**Likely splits into siblings.** Treat format-definition+migration, the
compose filter, the writer migration, and the docs rewrite as candidate
sibling tickets if the design step shows they're separable. Settle the shape in
design/review-design before touching the migration.

## Context

This reverses a deliberate part of the current architecture, so read
`relay/architecture` (the three-file model, the two state planes, and the
prompt-composition layer list — note that `log.md` is explicitly *never* a
composition layer) before designing. The single-file format must preserve every
invariant that split bought: the working section stays small and is composed;
the audit section can grow unbounded and is never composed; status/step remain
CLI-owned; hand-edits to frontmatter and body stay safe.

Source layout and test expectations are in `relay/codebase`. Keep the live
`relay-os/` copy and the packaged `src/relay/resources/templates/relay-os/`
copy of any touched contexts/templates in sync (see CLAUDE.md).
