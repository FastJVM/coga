---
title: Establish marketing area inside relay-os
status: draft
mode: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts: [relay/architecture, marketing/positioning]
skills: []
workflow: null
---

## Description

Establish marketing as a first-class area inside the existing relay-os:
a `tasks/marketing/` group directory for launch and pre-launch marketing
tasks, the `contexts/marketing/` namespace for marketing knowledge, and
a durable write-up of this structure under `contexts/marketing/` so
future marketing work lands here rather than in a separate relay repo.

## Context

Marketing for the Relay product (launch plans, pre-launch task tracking)
should live inside relay-cli itself. A nested `relay init` subdirectory
was considered and rejected (2026-06-11): a second relay-os would be
invisible to the main one — separate `relay status`, separate digest, no
shared contexts — while its task churn still commits into relay-cli's
git history, because the git layer resolves the enclosing repo via
`git rev-parse --show-toplevel` (`src/relay/git.py`).

Facts the agent needs:

- Task discovery already supports group directories: a child of `tasks/`
  without its own `ticket.md` whose children are tasks, e.g. the
  existing `tasks/auto/` (`list_tasks` in `src/relay/tasks.py`). Task
  slugs must stay unique across the whole tree, including groups.
- Marketing toeholds already exist: `contexts/marketing/positioning/`
  and the `launch-relay-product-launch-comms` task; both should fold
  into or align with the new structure.
- Per repo guidelines, the durable explanation belongs in a context,
  not only in this ticket or chat.
