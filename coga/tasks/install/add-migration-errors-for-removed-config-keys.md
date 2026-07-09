---
slug: install/add-migration-errors-for-removed-config-keys
title: Add migration errors for removed config keys
status: draft
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow: null
secrets: null
script: null
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
