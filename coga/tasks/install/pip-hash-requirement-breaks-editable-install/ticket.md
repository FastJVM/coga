---
title: pip hash-checking mode breaks editable install
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

A new user whose pip has global hash-checking mode enabled (a common managed
work-machine setting) can't run `pip install -e .` — editable installs carry no
hashes, so pip aborts. It's only workaroundable via an env var the user had to
dig to find. Make the documented install path either not depend on an editable
install for first-run, or detect the hash-checking failure and surface the exact
remediation instead of a raw pip traceback.

## Context

Reported by Greg, an external new user, on a managed work machine. The
documented quickstart leads with `pip install -e .` (CLAUDE.md "Build, Test,
and Development Commands"). This is the first domino in his install attempt — it
also caused the partial `relay init` failure tracked by
`install/init-does-not-persist-user-then-blocks-on-reinit`. Broader install
robustness is the umbrella `install/harden-packaging-and-install-before-launch`.
