---
slug: v2/add-dev-testing-setup-skill
title: Add dev testing setup skill
status: paused
mode: agent
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- coga/codebase
- coga/project-stage
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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: dev-testing-contract
worktree: /home/n/Code/codex/relay-dev-testing-contract

## Implement plan (2026-06-10, confirmed by nick)

1. New skill `relay-os/skills/dev/testing-setup/SKILL.md` — establishment
   procedure only: discover conventions (CI config, manifests, Makefile,
   docs), never invent commands, write the contract as a project-local
   context `dev/testing` with five declared sections (unit-test command,
   validation commands, fixture/external-service rules, known-failure
   policy with must-surface wording, CI parity) plus consumption rules.
2. Dogfood: write Relay's own contract at
   `relay-os/contexts/dev/testing/SKILL.md` (nick: yes).
3. Update consumers `code/implement`, `code/implement-and-pr`,
   `code/self-qa` to read the contract instead of hard-coded
   `python -m pytest`, with exact-results reporting (nick: yes).

Discovery findings for Relay's contract: pytest (ini `pythonpath=["src"]`),
`relay validate --json`, packaging test skips without hatchling (dev/test
extra), seeded `example/` fixture, **no CI exists** — local commands are the
only gate. Python 3.11+ required (tomllib).


## Rescope + merge (2026-06-10)

Nick asked whether this ticket was stale. Findings: no `dev/` skill ever
shipped; sibling `add-dev-unit-test-writing-skill` (done, PR #331) decided
generic test-process skills are boilerplate and folded suite-conformance into
`code/implement`; the "imported testing skills" premise never materialized.

Decision (nick): rescope this ticket to the testing-contract piece and merge
the `add-dev-test-run-skill` draft into it.

- Ticket body rewritten: scope is now a minimal `dev/testing-setup` skill
  whose only output is a project-local testing contract (declared commands,
  fixture rules, known-failure policy, CI parity). No standalone runner
  skill; test-run's durable requirements survive as consumption rules
  (read the contract, report exact results).
- `add-dev-test-run-skill` deleted via `relay delete` (recovery: git
  restore). Its prior-art pointers are preserved in this ticket's Context.
- Dropped `relay/current-direction` from contexts — broad; nothing from it
  is needed for this scope.
