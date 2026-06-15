---
title: Establish marketing area inside relay-os
status: done
mode: interactive
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: dev/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
---

## Description

Establish a marketing area inside relay-os: a `tasks/marketing/` group
directory where marketing and launch tickets will live going forward,
with a short README stating what belongs there and how tickets land in
it. Existing tickets stay where they are; the convention applies to new
work only.

Scope narrowed 2026-06-11 (after PR #338 was closed unmerged): the
`skills/marketing/` namespace and the `relay-os/context.md` routing
write-up were dropped — `skills/marketing/` gets created whenever there's
a real first skill to put in it. `contexts/marketing/` already exists.

## Context

- A nested `relay init` subdirectory for marketing was considered and
  rejected (2026-06-11): a second relay-os would be invisible to the
  main one — separate `relay status`, separate digest, no shared
  contexts — while its task churn still commits into relay-cli's git
  history, because the git layer resolves the enclosing repo via
  `git rev-parse --show-toplevel` (`src/relay/git.py`).
- Task discovery already supports one-level group directories
  (`src/relay/tasks.py:70`): a group is any child of `tasks/` without its
  own `ticket.md`. Non-directory files inside a group (the README) are
  ignored, tasks keep their bare leaf-name slugs regardless of nesting,
  and groups don't nest. Duplicate leaf names across levels raise, so
  moving a task into the group never changes how it's referenced.
- `relay draft` / `relay ticket` always create at the top level
  (`src/relay/create.py:119`) — there is no way to create directly
  into a group. New marketing tickets get created top-level and then
  `git mv`'d into `tasks/marketing/`; the README should state this so the
  convention survives. Teaching create to target a group is out of
  scope (separate ticket if wanted).
- Git doesn't track empty directories, so the README is what makes the
  group exist until its first ticket moves in.
- Do not move `launch-relay-product-launch-comms` or any other existing
  ticket.
- Run `relay validate --json` after creating the directory — an empty
  group dir (README only, no task children) is the one shape discovery
  hasn't been exercised on.
