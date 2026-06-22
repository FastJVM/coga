---
title: Replace with a one-line task title
status: draft
mode: interactive
owner: replace-with-human-name
human: replace-with-human-name
agent: replace-with-agent-nickname
assignee: replace-with-human-or-agent-nickname
contexts: []
skills: []
workflow: null
# Secrets this task needs (keys from [secrets] in relay.local.toml). Omit or
# `null` = legacy blanket-inject all secrets; `[]` = inject none; a list =
# inject only those keys (and fail loud at launch if any is unset).
secrets: null
# --- extensions ---
# Repo-declared fields (see `[ticket.fields.<name>]` in relay.toml) are
# injected by `relay create` / `relay ticket` below this marker. No
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
