---
title: Establish marketing area inside relay-os
status: draft
mode: interactive
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow: dev/with-self-review
---

## Description

Establish a marketing area inside relay-os: a `tasks/marketing/` group
directory where marketing and launch tickets will live going forward, and
a `skills/marketing/` namespace for marketing process skills
(`contexts/marketing/` already exists). Each new directory gets a short
README stating what belongs there, and the routing convention — new
marketing/launch work is created under these directories — is documented
in `relay-os/context.md` so every future composed prompt carries it.
Existing tickets stay where they are; the convention applies to new work
only.

## Context

- Task discovery already supports one-level group directories
  (`src/relay/tasks.py:70`): a group is any child of `tasks/` without its
  own `ticket.md`. Non-directory files inside a group (the README) are
  ignored, tasks keep their bare leaf-name slugs regardless of nesting,
  and groups don't nest. Duplicate leaf names across levels raise, so
  moving a task into the group never changes how it's referenced.
- `relay draft` / `relay ticket` always scaffold at the top level
  (`src/relay/scaffold.py:119`) — there is no way to scaffold directly
  into a group. New marketing tickets get scaffolded top-level and then
  `git mv`'d into `tasks/marketing/`; the README should state this so the
  convention survives. Teaching scaffold to target a group is out of
  scope (separate ticket if wanted).
- `relay-os/context.md` is the repo base context composed into every
  launch prompt (`src/relay/compose.py:200`) — it's currently template
  placeholder text. Replace the placeholder with a *minimal* base
  context: a sentence or two plus the marketing routing rule. Do not
  author a full repo description here — that's its own ticket if wanted.
  Diverging from the packaged template copy
  (`src/relay/resources/templates/relay-os/context.md`) is intentional
  (repo-specific vs. template); say so in the PR description to pre-empt
  the sync question from CLAUDE.md.
- Git doesn't track empty directories, so the READMEs are what make the
  area exist; `skills/marketing/` stays empty of skills until there's a
  real one to add.
- Do not move `launch-relay-product-launch-comms` or any other existing
  ticket.
- Run `relay validate --json` after creating the directories — an empty
  group dir (README only, no task children) is the one shape discovery
  hasn't been exercised on.