---
schedule: "0 9 * * 1"
schedule_comment: "Every Monday at 9am"
title: "Replace with the REM task title"
# `mode: auto` is temporarily disabled (auto runs produce no live console
# output). Use `mode: script` for unattended cron-driven runs, or
# `mode: interactive` if the run is meant to drop into a human terminal.
mode: script
workflow: namespace/your-workflow
owner: replace-with-human-name
assignee: replace-with-agent-type-or-human-name
---

## Description

REM is repo/user-specific recurring maintenance. It is the place for
operational checks that are meaningful to this repo, this team, or this user's
workflow.

REM is not Dream. Dream is Relay's generic ticket cleanup pass. REM owns its
own cadence, ticket scan, skill order, output conventions, and review gates.

Use this file as an inert starting point: copy or rename it to a non-underscore
filename under `relay-os/recurring/`, then replace the schedule, workflow,
owner, assignee, and process body.

## REM Process

Describe the repo-specific maintenance pass here.

Good REM candidates:

- product or operations health checks;
- customer, email, payment, or deployment follow-ups;
- repo-specific context audits;
- domain-specific recurring reports;
- reminders that depend on this repo's tasks and blackboards.

Do not put generic Relay cleanup here. Do not put branch hygiene here unless
this REM task is explicitly a dev maintenance loop.

## Output

Write one concise run summary to this task's blackboard. If the run opens PRs,
creates tickets, or needs human decisions, list those links and gates in the
summary.

`relay recurring check` creates a fresh task on each scheduled firing. Files in
`recurring/` whose name starts with `_` are skipped, so this template stays
inert until a human copies or renames it.
