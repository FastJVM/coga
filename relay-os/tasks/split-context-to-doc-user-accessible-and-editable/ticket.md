---
title: 'split context to doc: user accessible and editable'
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/architecture
- relay/principles
- relay/codebase
- relay/project-stage
skills: []
workflow: code/design-then-implement
---

## Description

The repo context (`relay-os/context.md`) is composed as layer 4 of every
launch prompt, living inside `relay-os/` next to agent-facing machinery
(tickets, workflows, skills). But it is really the project's living
documentation — what the repo is, who works on it, the defaults agents
should know — which a human reads and edits far more often than they touch
tickets, workflows, or skills. This ticket designs how to split that
human-owned documentation out to an accessible, editable location under
`docs/` while `relay launch` still composes it into the prompt. The right
boundary between "human-owned doc" and "agent-prompt context" is not yet
settled, so the first step is a design proposal for owner review before any
code is written.

## Context

- **Composition today:** `src/relay/compose.py:178` reads the repo context
  via `repo_context_path(cfg)` and emits the `"Repo context"` layer
  (`ref=context.md`). The resolver is `repo_context_path` in
  `src/relay/paths.py:84`, exported via `__all__` (`paths.py:120`) — both
  move together with any rename.
- **Two copies stay in sync:** the live `relay-os/context.md` and the
  packaged template `src/relay/resources/templates/relay-os/context.md`
  (see CLAUDE.md — keep both in sync unless intentionally divergent).
- **Docs that reference the path:** `relay/architecture` SKILL.md documents
  the 8-layer composition order and names `relay-os/context.md` at layer 4
  (~line 184). If the path moves, update that context in the same change.
- **Decision: `docs/` in repo** (alongside `docs/vision.md`) for the
  human-facing doc location. Exact filename (`docs/context.md` vs
  `docs/project.md`) is for the design step to recommend.
- **Open design questions for the proposal:** the exact filename; whether
  `relay launch` reads the new path directly or via a configurable pointer.
  Note: `relay/project-stage` says "No backwards-compat hacks" — so prefer a
  clean direct move over a compat shim unless the design surfaces a real
  reason. Markdown-first, git-backed, human-legible posture must hold (see
  `relay/principles`).
- **Template + seeding:** the packaged template
  `src/relay/resources/templates/relay-os/context.md` must move/rename in
  lockstep, and the design should confirm what reads it (the `relay init` /
  update seeding path and the `example/` fixture) before relocating — not
  just move the file.
- **Tension to resolve, not assume:** `relay/architecture` and
  `relay/codebase` frame `relay-os/` as the single tree relay operates on,
  with `context.md` as a composed layer inside it. Moving it to `docs/`
  splits that boundary; the design must justify why the human-doc framing
  outweighs keeping all composed layers under `relay-os/`.
- **Out of scope:** rewriting what the context *says*, and re-homing the
  broader `relay/*` contexts that also double as docs — this ticket is only
  about where the repo-level `context.md` lives and who owns it. The design
  may *note* the broader pattern but should not expand to it without owner
  sign-off.
