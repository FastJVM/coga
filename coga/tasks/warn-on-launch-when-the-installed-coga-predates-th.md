---
slug: warn-on-launch-when-the-installed-coga-predates-th
title: Warn on launch when the installed coga predates the source tree
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

Add a warn-only version-skew guard: when a coga command operates on a repo
that is itself a coga source checkout (contains `src/coga/`), and the
*running* installed package was built before the latest commit touching
`src/coga/`, print a loud stderr warning naming both sides and the remedy
(`uv tool upgrade coga` / reinstall from the checkout).

Scope decisions to settle during implementation:

- **Where the guard fires.** `coga launch` entry is the minimum (that's
  where a stale binary burns hours of agent work); consider also `coga
  validate` as the diagnostic surface. Keep it out of read-only commands'
  hot path if it costs a subprocess.
- **How skew is detected.** Cheapest deterministic option: at build/install
  time the package already knows its vendored/built commit SHA (`coga
  --version` prints it). Compare that SHA's commit date against
  `git log -1 --format=%ct -- src/coga/` of the repo being operated on;
  warn when the source tree is newer. Must degrade silently when the repo
  is not a coga source checkout, has no git, or the package carries no
  build SHA — the guard is for coga developers and must never bother normal
  users.
- **Warn, never refuse.** Running a slightly stale coga is usually fine;
  the guard exists to make the skew *visible*, not to block work.

## Why

2026-07-01/02: three launch sessions in a row silently lost `log.md` audit
lines from detached isolation worktrees. The bug (detached-HEAD sync had no
landing path for `merge=union` files) was fixed in source at 11:02
(419dcdff), yet the 11:31 session still failed — the running `coga` was a
uv tool build from 21:06 the previous night, installed from a sibling
checkout. Nothing surfaced that the binary predated the fix; the skew was
only found by diffing the installed package's `git.py` against source.
Recovery cost a manual salvage session (PR #500).

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
