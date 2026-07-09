---
slug: install/warn-loud-when-init-commit-is-skipped
title: Warn loud when init commit is skipped
status: draft
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
  - dev/code
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

On a machine with no git identity (`user.email` unset — every truly fresh
machine), `coga init` reports full success but the "commit coga/" step
silently fails: `_git_commit_coga_os` swallows `CalledProcessError` and
returns None, so the "Committed coga/ as …" line is simply absent. Files sit
staged, and the user's first `coga create` then surfaces a raw
`fatal: ambiguous argument 'HEAD'` git error (no HEAD exists yet). This is a
fail-loud violation (principle 6). Fix: warn loudly when the commit is
skipped/fails, naming the cause and remedy (`git config user.email …`), or
check git identity up front next to the git/gh dependency check.

## Context

Found in the 2026-07-08 fresh-container retest: verified init exit 0 with
staged-but-uncommitted tree and no warning, then the raw `git rev-parse HEAD`
error on first `coga create`; with identity set the commit works. Touchpoint:
`src/coga/commands/init.py` (`_git_commit_coga_os`, its caller in `_do_init`,
and `_check_external_dependencies` if going the up-front-check route).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
