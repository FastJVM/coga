---
slug: install/improve-reinit-already-exists-message
title: Improve reinit already-exists message
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

Running `coga init` in an already-initialized repo prints only
"`/path/coga` already exists." with no next step. `--update` no longer
exists, so the user is left guessing what re-running init was supposed to do.
Extend the refusal with the actual remedies: upgrading the CLI is
`pip install --upgrade coga` (batteries resolve from the package, no re-init
needed); a broken/partial `coga/` is recovered by fixing the cause or
removing the dir; `coga uninstall` removes the footprint.

## Context

Found in the 2026-07-08 fresh-container retest. The old `--update` wedge
(`install/init-does-not-persist-user-then-blocks-on-reinit`) is fixed — init
is atomic with verified rollback — this is just the terse message left
behind. Touchpoint: `src/coga/commands/init.py` (`_do_init`, the
`coga_os.exists()` refusal).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
