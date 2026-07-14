---
slug: cleanup-core-commands/launch-decomposition
title: Decompose launch into substrate plus ticket orchestration
status: in_progress
owner: nicktoper
human: nicktoper
agent: codex
assignee: codex
contexts:
- coga/principles
- coga/architecture
- coga/codebase
- coga/current-direction
- coga/extension-model
- coga/project-stage
- coga/cli
- dev/code
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
secrets: null
script: null
step: 1 (design)
---

## Description

Decompose `coga launch` so the irreducible executor substrate is explicit and
everything else is a candidate for bootstrap tickets, workflows, skills, or
script operations.

The command may need to remain the entrypoint that executes a ticket, composes
prompts, runs script/agent sessions, handles locks, injects secrets, and calls
state-write/sync/notification internals. It should not remain a dumping ground
for policy or orchestration that can live in editable Coga files.

## Context

Directory index: `cleanup-core-commands/README`.

Owner direction from the parent: keep `launch` and the things it truly depends
on, but challenge every other part of launch-shaped behavior. This ticket should
make the line concrete enough that other migration tickets do not accidentally
rebuild a large command surface around launch.

Design first. Inventory `src/coga/commands/launch.py` and adjacent modules.
Classify each responsibility as:

- executor substrate that must stay in Python;
- launch policy that can move to bootstrap ticket/workflow/skill text;
- lifecycle transition that belongs with the lifecycle migration ticket;
- compatibility sugar that can become an alias or a small wrapper.

Out of scope: moving `create`, moving `skill *`, or implementing lifecycle
verb migration unless it is required to prove the launch split.

## Acceptance Criteria

- [ ] The design step documents the exact minimal launch substrate.
- [ ] Movable launch policy/orchestration is either moved or split into
      concrete follow-up tickets.
- [ ] Launch behavior remains fail-loud for missing refs, broken contexts,
      secrets, script failures, git/sync failures, and blocked/done tickets.
- [ ] The decomposition coordinates with
      `cleanup-core-commands/lifecycle-verbs-to-ticket-operations` where launch
      currently calls lifecycle state writes.
- [ ] Tests cover changed launch behavior, and durable docs/contexts are updated.

<!-- coga:blackboard -->

Created under `cleanup-core-commands/` as part of the command-surface breakdown.

## Usage

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":null,"cli":"codex","input_tokens":null,"model":null,"output_tokens":null,"provider":"openai","schema":1,"session_id":null,"slug":"cleanup-core-commands/launch-decomposition","step":"design","title":"Decompose launch into substrate plus ticket orchestration","ts":"2026-07-09T22:08:16.330137Z","usage_status":"unknown"}

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":null,"cli":"codex","input_tokens":null,"model":null,"output_tokens":null,"provider":"openai","schema":1,"session_id":null,"slug":"cleanup-core-commands/launch-decomposition","step":"design","title":"Decompose launch into substrate plus ticket orchestration","ts":"2026-07-09T22:08:40.865905Z","usage_status":"unknown"}
