---
slug: coga-important/context
title: context
status: draft
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow: docs/with-review
secrets: null
script: null
---

## Description

This ticket is the unit of work to build a context block that describes how we
plan to handle important notifications and who's responsible for acting on them.
It's also meant to explain how it differs from coga-flow.

The deliverable is the context block itself — the routing convention any script
can follow to raise a human-action notification. The channel already exists; its
webhook and the coga.toml recipient field are separate tickets.

## coga-important

1. `coga-important` is our Slack channel strictly for notifications that need
   human action.

2. Coga's automatic state-transition broadcasts (create / bump / mark) stay in
   coga-flow.

3. We don't want to be inundated with notifications, but we don't want anything
   to fall through the cracks.

4. Notifications land here automatically — any script that detects an
   action-needed event runs `coga slack --important` to post it to
   `coga-important` (e.g. a patent sweep posting "maintenance fee due").

5. By default every `--important` notification @'s the user set in the coga.toml
   property field — the triage owner it all lands on.

6. That user either handles it, @'s someone in the Slack thread, or opens a ticket
   if it's real work.

7. Handing off stays a plain Slack @ and gets no Coga machinery — a thread reply
   keeps the alert's context, while a second `coga slack` post would land
   disconnected from it and add the channel noise point 3 rules out.

## Context

- Where the block lands is undecided and is the first thing to settle.
- Contexts resolve local-first from `coga/contexts/`, then the installed package's bundled `bootstrap/contexts/`; there is no cross-repo lookup.
- The first consumer is a script in the patents repo, so a block under `coga/contexts/` here never resolves for it.
- A bundled block under `src/coga/resources/templates/coga/bootstrap/contexts/` resolves in every repo with coga installed.
- A bundled block also ships to every coga user, so the channel name and the triage owner cannot live in it.
- That suggests a split — the `coga slack --important` mechanism bundles, and the FastJVM specifics stay repo-local or in coga.toml.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
