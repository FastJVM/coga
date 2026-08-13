---
slug: _template
title: Replace with a one-line task title
status: draft
owner: replace-with-human-name
human: replace-with-human-name
agent: replace-with-agent-nickname
assignee: replace-with-human-or-agent-nickname
contexts: []
skills: []
workflow: null
# Secrets this task needs, declared inline — one `- NAME: <ref>` list entry per
# secret, where `<ref>` is an `op://vault/item/field` 1Password reference or an
# `env:VAR` indirection. Absent / `null` / `[]` inject nothing; a list injects
# only those keys (and fails loud at launch if any ref is unset).
secrets: null
# --- extensions ---
# Repo-declared fields (see `[ticket.fields.<name>]` in coga.toml) are
# injected by `coga create` / `coga ticket` below this marker. No
# extensions configured → nothing here, marker is harmless.
---

## Description

What needs to happen and why. The agent reads the composed prompt at
launch time, not this body — these sections exist to help humans
organize their thinking.

## Context

Task-specific knowledge that isn't a reusable skill or context file.
One-off details: where in the codebase, what to watch out for, what not
to touch.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
