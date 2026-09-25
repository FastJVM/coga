---
title: Remove the twin check and the twin concept
status: draft
owner: nicktoper
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
step: 1 (design)
---

## Description

Placeholder: the goal is clear, but the design isn't ready to implement.

Goal: stop keeping two copies of Coga's shipped files. Today every packaged file under `src/coga/resources/templates/coga/` has a "twin" in this repo (`coga/...` for skills, workflows and recurring templates; `docs/contexts/...` for contexts). `tests/test_packaging.py::test_live_and_packaged_copies_stay_identical` requires each pair to match byte for byte. The test has three escape hatches: `INTENTIONALLY_DIVERGENT_TWINS` (3 entries), `LOCAL_ONLY_CONTEXT_REFS` (10) and `REQUIRED_BOOTSTRAP_CONTEXT_REFS` (66). The wheel ships only one copy. The duplication exists because this repo runs on its own `coga/` folder, the same way a user's repo does after `coga init`.

Why: every edit to a shipped file has to be made twice. The rule costs a long section in CLAUDE.md/AGENTS.md and in `coga/packaging`. Runtime state in a twinned file breaks the test: the phone-home ticket's `period_state:` fails it on `main` (PR #895 is a stopgap exemption).

End state: one copy of each shipped file. There are no byte-identity test, no divergence, local-only or required-ref lists, and no twin rules in CLAUDE.md, AGENTS.md or the topics.

Open questions for design:
- Which copy is canonical? One option: the repo's `coga/` and `docs/contexts/` stop holding copies of bundled items and resolve them from the package's bundled batteries, which lookup already falls back to (local-first, then bundled). Another option: the packaged tree is built from the repo copies at build time.
- How does this repo keep "dogfooding" what it ships without keeping a copy? That means editable-install resolution of bundled batteries.
- Where does runtime state in a shipped template, like the phone-home ticket's `period_state`, live once the template isn't copied into this repo?
- What replaces the drift protection, if anything? A missing-ref check through `coga validate` may be enough.
- Which docs change: CLAUDE.md, AGENTS.md, `coga/packaging`, `coga/codebase`, `coga/testing`, `coga/knowledge` and other topics that mention twins, plus `src/coga/logfile.py` and the packaged address-pr-comments ticket.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
