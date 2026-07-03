---
slug: allow-creation-of-coga-dir-in-subdir
title: allow creation of coga dir in subdir
status: draft
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow: dev/with-self-review
secrets: null
script: null
---

## Description

Allow `coga init` to scaffold `coga/` in a subdirectory of a host repo
(e.g. `coga init tools/ops` inside a monorepo) instead of assuming the git
root. The runtime already models nesting — `COGA_REPO_ROOT` is the host repo,
the parent when `coga/` is nested — so the work is making init, root
discovery, and `coga validate` resolve correctly when `coga/` lives below the
git root. Audit the commands that walk upward to find `coga/` (launch, status,
bump, etc.) for assumptions that break in the nested layout, add tests
covering it, and fail loud on layouts that can't work (e.g. nesting a `coga/`
inside an existing `coga/`).

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
