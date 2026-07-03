---
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
