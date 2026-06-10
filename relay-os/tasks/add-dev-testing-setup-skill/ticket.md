---
title: Add dev testing setup skill
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/codebase
- relay/project-stage
- dev/code
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

Add a minimal `dev/testing-setup` skill whose only output is a project-local
**testing contract**: a small declared document recording how this repo runs
and judges its tests. The contract declares:

- the unit-test command (and narrower affected-test commands, if any)
- broader validation commands (lint, typecheck, repo validators)
- fixture/data setup rules and external-service boundaries
- known-failure/baseline policy, worded so new failures must be surfaced,
  never silently baselined
- CI parity: how the local commands map to what CI runs

The skill discovers existing conventions first (CI config, manifests,
Makefile, README/docs) and records them; it does not invent commands or
impose a framework. The contract is the durable artifact — the skill is just
the establishment procedure, not generic "how to test" prose.

There is no standalone `dev/test-run` runner skill. That draft is merged
into this ticket; its durable requirements survive as consumption rules: any
dev step that runs tests reads the contract instead of guessing commands,
and reports exact results (command, exit code, pass/fail/skip counts when
available, failing test names).

## Context

Merged from `add-dev-test-run-skill` (draft, deleted 2026-06-10) — its prior
art pointers for result reporting were `sanity-labs/test` and
`ingpoc/SKILLS/testing`, useful as reference but optional.

Decision trail: sibling `add-dev-unit-test-writing-skill` (done, PR #331)
concluded that generic test-process skills are boilerplate a strong agent
already follows, and folded the one non-obvious piece (suite conformance)
into `code/implement`'s Test step. The residue that survives that logic is
repo-specific *declared state* — the contract — not process prose. Keep this
ticket that lean.

Shape hint: the contract is domain knowledge (facts about this repo), so per
the skill/context split it likely lands as a context (e.g.
`dev/testing`) or a documented top-level file, with its location and shape
documented well enough that other skills/steps can find it. Don't hard-code
Relay's own Python test command into the generic skill.

## Acceptance criteria

- [ ] A `dev/testing-setup` skill exists; its output is the testing
      contract, not generic how-to-test process prose.
- [ ] It discovers existing project conventions (CI config, manifests, docs)
      before proposing anything, and never hard-codes a language or
      framework.
- [ ] The contract shape covers: unit-test command, validation commands,
      fixture/data rules and external-service boundaries, known-failure
      policy, CI parity.
- [ ] Known-failure policy is worded so new failures must be surfaced, never
      silently baselined.
- [ ] The contract's location and shape are documented so other skills and
      workflow steps read it instead of inventing commands.
- [ ] Test-running consumers report exact results: command, exit code,
      pass/fail/skip counts when available, failing test names.
