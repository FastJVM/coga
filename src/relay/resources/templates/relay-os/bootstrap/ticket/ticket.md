---
title: Create a new ticket
mode: interactive
skill: bootstrap/ticket
assignee: claude1
---

## Description

Persistent launch shim. Run with `relay launch --task bootstrap/ticket` to
start the `bootstrap/ticket` skill, which interviews the human and scaffolds
a new task directory under `relay-os/tasks/<NNN>-<slug>/`.

This ticket is stateless. It has no status and acquires no lock — every
launch is a fresh authoring session. Don't edit the ticket itself except to
swap the `assignee` to whichever agent nickname you have configured in
`relay.toml`.
