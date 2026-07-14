---
slug: marketing/README
title: Marketing tasks directory index
status: draft
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

Group directory for marketing and launch work — launch plans, comms,
positioning tickets, and anything pre/post-launch promotional. New
marketing or launch tickets belong here.

How tickets land here: `relay create` / `relay ticket` always create at
the top level of `tasks/`, so create the ticket normally and then
`git mv relay-os/tasks/<slug> relay-os/tasks/marketing/<slug>`. Slugs are
leaf-name based, so the move doesn't change how the ticket is referenced.

The bar for membership: the work itself is marketing (comms, community,
positioning, adoption tracking, launch assets) — not product work that
merely helps the launch.

<!-- coga:blackboard -->
