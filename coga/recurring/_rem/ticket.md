---
schedule: "0 9 * * 1"
schedule_comment: "Every Monday at 9am"
title: "Replace with the REM task title"
# Pick a mode: `script` runs a skill script directly with no agent;
# `auto` is a one-shot headless agent run whose output is buffered to the
# task log; `interactive` drops into a human terminal with live output.
autonomy: auto
workflow: namespace/your-workflow
owner: replace-with-human-name
assignee: replace-with-agent-type-or-human-name
---

## Description

REM is repo/user-specific recurring maintenance. It is the place for
operational checks that are meaningful to this repo, this team, or this user's
workflow.

REM is not Dream. Dream is Coga's generic ticket cleanup pass. REM owns its
own cadence, ticket scan, skill order, output conventions, and review gates.

A recurring task is a ticket-format directory under `coga/recurring/`:
`ticket.md` (this file), `blackboard.md` (persists state across runs), and
`log.md` (run history). Use this `_rem/` directory as an inert starting
point: copy or rename it to a non-underscore name, then replace the schedule,
workflow, owner, assignee, and process body.

## REM Process

Describe the repo-specific maintenance pass here.

Good REM candidates:

- product or operations health checks;
- customer, email, payment, or deployment follow-ups;
- repo-specific context audits;
- domain-specific recurring reports;
- reminders that depend on this repo's tasks and blackboards.

Do not put generic Coga cleanup here. Do not put branch hygiene here unless
this REM task is explicitly a dev maintenance loop.

## Output

Write one concise run summary to this task's blackboard. If the run opens PRs,
creates tickets, or needs human decisions, list those links and gates in the
summary.

`coga recurring` get-or-creates the current period's task for each recurring
task when its schedule is due. Directories in `recurring/` whose name starts
with `_` are skipped, so this template stays inert until a human copies or
renames it.

<!-- coga:blackboard -->

This blackboard persists across every run of this recurring task. A run reads
it at the start to pick up where the last run left off, and updates it at the
end with whatever the next run needs.

If your REM task carries state between runs — a last-processed commit, a
high-water mark, a cursor — record it here in a clearly named section, and
say in `ticket.md` that runs read and update it.
