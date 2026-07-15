---
slug: install/add-migration-errors-for-removed-config-keys
title: Add migration errors for removed config keys
status: in_progress
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

Current main rejects the `coga.toml` that released 0.2.0 itself scaffolds:
`[agents.claude] auto = "-p"` (and `[agents.codex] auto = "exec"`) hit the
generic `unknown key(s) ['auto']` error on every command including `--help`,
with no hint that the key was removed or what to do. Upgrading the CLI thus
bricks every existing repo until a hand-edit. Removed/renamed config keys need
tailored migration errors that run before the generic unknown-key check —
exactly the treatment `skip_permissions` / `[assignees]` already get — saying
the key is gone and to delete the line.

## Context

Found in the 2026-07-08 fresh-container retest (HEAD CLI against a
0.2.0-initialized repo). Touchpoint: `src/coga/config.py` (`load_config`
fixed-schema validation and its existing deprecated-key carve-outs — see the
"Config loading fails loud on unknown keys" section of the `coga/architecture`
context). Sibling: `install/cut-release-to-realign-pypi-with-main` (the skew
only bites because main is unreleased).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Usage

{"agent":"claude","cache_creation_input_tokens":null,"cache_read_input_tokens":null,"cli":"claude","input_tokens":null,"model":null,"output_tokens":null,"provider":"anthropic","schema":1,"session_id":"a7e5253b-e8a3-4dce-9aa2-54c6d76f7dbc","slug":"install/add-migration-errors-for-removed-config-keys","step":"implement","title":"Add migration errors for removed config keys","ts":"2026-07-15T19:03:34.690748Z","usage_status":"unknown"}
