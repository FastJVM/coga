---
slug: fresh-repo-default-branch-mismatch-git-init-master
title: 'Fresh-repo default branch mismatch: git init master vs control_branch main'
status: draft
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
secrets: null
---

## Description

On a brand-new repo where `git init` produced a `master` branch (the default on
many setups), Relay's `[git].control_branch` defaults to `main`. Every
state-mutating command then runs `git fetch origin main` / pushes to
`refs/heads/main` against a branch that doesn't exist, so the git sync fails.
The failure is swallowed (`GitError` → stderr + `log.md`) and the command still
exits 0 — so a first-time user following the README's Getting Started sees a
confusing error but no actual failure.

## Context

Surfaced walking a first-time user through README Getting Started in a clean
repo. Default-branch mismatch: `git init` → `master` on many setups vs
`[git].control_branch` default `"main"` (`src/relay/config.py:138`, `:889`).
The non-fatal-by-design swallow is at `src/relay/git.py:148-159` (failure model
in the module docstring, `git.py:29-40`), which is why it exits 0 and is easy to
miss. Left to Nick to pick the direction (detect the actual default branch,
warn at init, document it, etc.).

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
