---
title: Recurring scan
assignee: system
secrets: null
script: run.py
---

## Description

Stateless bootstrap script target for the bare `coga recurring` command.
It has no schedule, workflow, status, or high-water mark of its own. The
public command head owns Typer parsing for `--interactive`, `--all`, and
`--agent`, writes those values into `COGA_RECURRING_INTERACTIVE`,
`COGA_RECURRING_FORCE`, and `COGA_RECURRING_AGENT`, and launches this target.
The `--all` parent also sets the private
`COGA_RECURRING_REQUIRE_FRESH_CONTROL` marker so a child refuses to scan when
its control checkout cannot first incorporate the fetched remote tip.

The script loads the current Coga config, scans `coga/recurring/`, creates or
reuses due period tasks, syncs recurring creates, prints/broadcasts scan
results, and launches due tasks sequentially through the normal launch path.
An agent override applies only to agent-backed tasks; script tasks keep their
deduced execution path and ticket assignees remain unchanged.
The recurring state it reads and writes remains the template files and
instantiated task directories, not this bootstrap target.
