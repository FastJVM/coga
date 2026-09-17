---
title: 'split context to doc: user accessible and editable'
status: draft
owner: nicktoper
agent: claude
contexts:
- coga/architecture
- coga/principles
- coga/codebase
- coga/project-stage
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

The repo context (`coga/context.md`) is composed as the "Repo context" layer
of every launch prompt, living inside `coga/` next to agent-facing machinery
(tickets, workflows, skills). But it is really the project's living
documentation — what the repo is, who works on it, the defaults agents
should know — which a human reads and edits far more often than they touch
tickets, workflows, or skills. This ticket designs how to split that
human-owned documentation out to an accessible, editable location under
`docs/` while `coga launch` still composes it into the prompt. The right
boundary between "human-owned doc" and "agent-prompt context" is not yet
settled, so the first step is a design proposal for owner review before any
code is written.

**Do not pull this forward until `redo-documentation-dir-and-merge-it-with-context-b`
has passed its owner gate.** That live ticket is rebuilding `docs/` as the
knowledge library and explicitly leaves this repo-context relocation deferred
("this ticket does not satisfy it by relocating reusable contexts"). Its
approved `docs/` layout decides where a relocated `context.md` would land and
whether a separate move is still wanted; a design written before that gate
would be a narrow move against a layout the owner is about to settle.

## Context

Premise re-checked 2026-09-16 (`adjudicate-parked-and-active-tickets-whose-premise`):
the subject is still unbuilt and every surface below resolves on `main`.

- **Composition today:** `src/coga/compose.py` reads the repo context via
  `paths.repo_context_path(cfg)` and emits the `Repo context` layer. The
  resolver is `repo_context_path` in `src/coga/paths.py`, hardcoded to
  `<repo_root>/context.md` and exported via `__all__` — both move together
  with any rename.
- **Precedent for a relocation knob:** `move-cogacontext-to-roodoc-so-its-easier-for-human`
  (done, PR #704) made the *contexts directory* tunable in `coga.toml` for the
  same human-ergonomics reason. It deliberately did not touch the repo-level
  `context.md`; the design should decide whether this move is a second knob of
  the same shape or a fixed relocation, and reuse that ticket's git-sync
  findings (the state sweep must track the new path).
- **Two copies stay in sync:** the live `coga/context.md` and the packaged
  template `src/coga/resources/templates/coga/context.md` (CLAUDE.md — keep
  both in sync unless intentionally divergent).
- **Docs that reference the path:** `coga/architecture` documents the prompt
  composition order and names `coga/context.md` as the repo-context layer. If
  the path moves, update that context in the same change.
- **Decision: `docs/` in repo** (alongside `docs/vision.md`) for the
  human-facing doc location, subject to the `redo-documentation` layout.
  Exact filename is for the design step to recommend.
- **Open design questions for the proposal:** the exact filename; whether
  `coga launch` reads the new path directly or via a configurable pointer.
  `coga/project-stage` says "No backwards-compat hacks" — prefer a clean
  direct move over a compat shim unless the design surfaces a real reason.
  Markdown-first, git-backed, human-legible posture must hold (`coga/principles`).
- **Template + seeding:** the packaged template must move/rename in lockstep,
  and the design should confirm what reads it (the `coga init` seeding path
  and the `example/` fixture) before relocating — not just move the file.
- **Tension to resolve, not assume:** `coga/architecture` and `coga/codebase`
  frame `coga/` as the single tree Coga operates on, with `context.md` as a
  composed layer inside it. Moving it to `docs/` splits that boundary; the
  design must justify why the human-doc framing outweighs keeping all
  composed layers under `coga/`.
- **Out of scope:** rewriting what the context *says*, and re-homing the
  broader `coga/*` contexts that also double as docs — that larger question
  is `redo-documentation-dir-and-merge-it-with-context-b`, not this ticket.

<!-- coga:blackboard -->

## Production notes

- 2026-05-28 bootstrap: framed as a design ticket (`code/design-then-implement`)
  because the human-doc / agent-context boundary is unsettled; scope locked
  to the repo-level `context.md`; `coga/project-stage` attached after the
  evaluator review so the shim question is answered by the stage posture.
  The evaluator's findings (resolver is `paths.py`, not `config.py`; attach
  project-stage; template/seeding caveat; boundary tension) were all folded
  into `## Context`.
- 2026-09-16 adjudication: still alive on both v2 README questions; body
  rewritten from Relay-era paths to current `coga/` surfaces and guarded on
  the `redo-documentation` owner gate rather than canceled.
