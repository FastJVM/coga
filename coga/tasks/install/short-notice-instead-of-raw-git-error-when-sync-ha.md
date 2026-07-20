---
slug: install/short-notice-instead-of-raw-git-error-when-sync-ha
title: Short notice instead of raw git error when sync has no origin remote
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
  - coga/codebase
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

In a repo with no `origin` remote — exactly the state `coga init` leaves a new
user in (`git init` → `coga init`, "push when ready") — every state-changing
command prints a raw two-paragraph git fatal, twice:

```
[git] sync failed: `git push origin main` failed: fatal: 'origin' does not
appear to be a git repository
fatal: Could not read from remote repository. …
```

Sync is correctly non-fatal (the GitError handler in `src/coga/git.py` makes
the miss visible without blocking the transition), and `git.py` already prints
calm one-liners for the "git disabled" and "not a git repo" cases. "No remote
named `origin` (or the configured `git_remote`)" is just as detectable and
just as expected on first run — it should get the same short, actionable
notice (e.g. "no `origin` remote yet — state committed locally; add a remote
to sync") instead of a scary fatal dump on a new user's first ticket.

## Context

Found during `install/retest-ssh-https-and-init-reclone-on-fresh-machine`
(finding 6 on its blackboard): fresh-container onboarding, `coga create` right
after `coga init` in a local-only repo. Touchpoints: the GitError fallbacks in
`src/coga/git.py` (lines ~287/353/436) and `src/coga/recurring_runner.py`
(~548); consider detecting the missing remote up front next to the existing
`_control_branch_present` check rather than pattern-matching stderr.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
