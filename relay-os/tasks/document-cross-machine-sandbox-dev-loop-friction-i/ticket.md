---
slug: document-cross-machine-sandbox-dev-loop-friction-i
title: Document cross-machine/sandbox dev-loop friction in relay/codebase
status: draft
autonomy: interactive
owner: nick
human: nick
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

Across roughly 15 code-ticket blackboards, the same cross-machine / sandbox
dev-loop frictions get re-discovered each time. Capture them once in the
`relay/codebase` context (`relay-os/contexts/relay/codebase/SKILL.md`, as a new
block) so future agents don't have to rederive them:

- (a) The checked-in `.venv` is Python 3.9, but Relay needs 3.11+ (it imports
  `tomllib`). Run the suite as
  `PYTHONPATH=<worktree>/src python3.12 -m pytest` instead of the venv python.
- (b) `codex review --base main` fails in-sandbox (the app-server is read-only)
  and must be rerun unsandboxed.
- (c) `relay validate` / `relay draft` fail when `.git` can't create
  `index.lock` inside a restricted sandbox.
- (d) Repo-wide `relay validate` reports pre-existing unrelated drift, so
  `relay validate --task <slug>` is the meaningful per-ticket check.

This is a doc task for a human to design and place the wording.

## Context

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
