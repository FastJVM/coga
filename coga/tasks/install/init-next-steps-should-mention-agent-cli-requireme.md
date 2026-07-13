---
slug: install/init-next-steps-should-mention-agent-cli-requireme
title: Init next steps should mention agent CLI requirement
status: active
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
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
secrets: null
script: null
step: 1 (implement)
---

## Description

Init's "Next steps" tells a fresh user to run `coga build` without mentioning
that an agent CLI (Claude Code or Codex) must be installed and authenticated
first. The eventual failure is clear ("Agent CLI 'claude' not found in PATH")
but arrives after the user has committed to the flow. Add a line to the
next-steps output (and the README Getting Started, once it exists) naming the
agent-CLI prerequisite and where to get one. Consider whether agent CLIs
belong in the `coga.dependencies` manifest as `required_at_init=False`
entries so the point-of-need error carries an install hint too.

## Context

Found in the 2026-07-08 fresh-container retest (launch with pseudo-TTY, no
claude installed). Touchpoints: `src/coga/commands/init.py` (next-steps
block), `src/coga/dependencies.py`, README. Related:
`install/document-where-to-run-init-and-adopt-existing-repo` (the wider
Getting Started gap).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
