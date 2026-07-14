---
slug: install/improve-reinit-already-exists-message
title: Improve reinit already-exists message
status: active
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
