---
title: relay init git-inits a fresh dir
status: draft
mode: interactive
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

`relay init` never runs `git init`. When its target isn't already a git repo it
silently skips committing `relay-os/` — no error, no warning — leaving a
git-backed tool in a half-set-up, untracked state. It should `git init` a
fresh/non-repo target (or fail loud per principle 6), closing the silent skip.
Surfaced by the fresh-directory onboarding path (`marketing/readme-and-docs`).

## Context

- The silent skip lives in `src/relay/commands/init.py` — `_git_commit_relay_os`
  returns early when `target/.git` is absent, so `relay-os/` is never committed
  and no "Committed relay-os/" line prints.

