---
title: test autobimp
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- dev/code
skills: []
workflow:
  name: dev/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

Throwaway test ticket to confirm that `relay launch`'s auto-relaunch
supervisor chains correctly through the `dev/with-self-review` workflow.
The first three steps — `implement`, `self-qa`, `pr` — are all agent
(`claude`) steps, so a single `relay launch test-autobimp` should
**auto-relaunch twice** (`implement → self-qa`, then `self-qa → pr`)
with no human `relay launch` in between, then **stop** at the human
`review` gate. "Done" for this test = the supervisor tore down each REPL
cleanly and respawned the next agent step in a fresh process on its own.

## Context

- **Not a real feature.** The `implement` step's only job is to add one
  small, self-contained, *passing* test under `tests/` (e.g. asserting a
  trivial existing behavior) so the chain has a real diff to carry through
  self-QA and PR. No source change — keep it green so CI passes and the PR
  is mergeable.
- **Expected boundary behavior** (the prediction under test):
  - `implement → self-qa` (claude → claude): **auto-relaunch**
  - `self-qa → pr` (claude → claude): **auto-relaunch**
  - `pr → review` (claude → owner): **stop** at the human gate
- After each agent step, watch that the supervisor respawns the next step
  automatically — no manual `relay launch` should be needed until the
  human review gate. A mismatch (e.g. a stop where auto-relaunch was
  expected) is the finding; note it on the blackboard.
- Record the branch and PR under a `## Dev` section on the blackboard per
  the `dev/code` context.
