---
title: relay init doesn't persist user on first run, then wedges on re-init
status: draft
mode: llm
owner: zach
human: zach
agent: claude
assignee: zach
contexts: []
skills: []
workflow: null
secrets: null
---

## Description

Greg's first `relay init` failed partway without persisting his `user`. Re-running
`relay init` then reported the directory was already initialized and recommended
`--update`, but `--update` complained the user wasn't set — leaving him wedged
between "already initialized" and "user missing" with no clear path forward. Make
first-run user capture atomic/recoverable (or let `--update` set a missing user),
so a partially-failed init isn't a dead end requiring manual config editing.

## Context

Reported by Greg. The partial failure was triggered by the pip hash-checking
issue (`install/pip-hash-requirement-breaks-editable-install`). Related in-flight
init hardening: `marketing/relay-init-git-inits-a-fresh-dir` (fail loud when the
target isn't a git repo) and `fresh-repo-default-branch-mismatch-git-init-master`.
Name capture itself is `relay-init-captures-name-via-user-param` (done). Init code
is in `src/relay/commands/` (init) and `src/relay/config.py`.
