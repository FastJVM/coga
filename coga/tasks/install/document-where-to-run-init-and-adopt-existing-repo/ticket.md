---
slug: install/document-where-to-run-init-and-adopt-existing-repo
title: Document where to run relay init and how to adopt an existing project
status: draft
mode: agent
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

Greg didn't realize `relay init` is meant to be run inside the root of the repo
he wants to work on; he created a fresh empty directory to try it, then couldn't
figure out how to bring his actual project in. Getting Started should state
plainly that Relay is adopted into an existing project's git root — and what to
do if you started in an empty directory — so the mental model is clear before the
first command.

## Context

Reported by Greg. This is a docs/onboarding-clarity fix, not a behavior change.
Touchpoint: README Getting Started, under editorial revision in
`marketing/readme-and-docs`. Related behavior ticket:
`marketing/relay-init-git-inits-a-fresh-dir` (fail loud when the init target
isn't a git repo).

**Retest 2026-07-08 (fresh-container):** the behavior half is fixed — init in
a non-git dir fails loud with "Run `git init` … first". The docs half is
worse than before: the current README (73 lines) has **no Getting Started at
all** — it never mentions `coga init`, `--user`, running in the project's git
root, adopting an existing repo, or that git *and gh* are required at init
(no External CLI Tools section). Also: the "No coga.toml found" error tells
you to run coga "from inside a Coga repo" without naming `coga init` — add
the hint there too (`src/coga/cli.py`).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
