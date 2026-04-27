---
schedule: "0 9 * * 1"
schedule_comment: "Every Monday at 9am"
title: "Weekly dream scan"
mode: auto
workflow: bootstrap/dream-run
assignee: claude1
owner: marc
---

## Description

Run the dream skill: scan the Relay repo for knowledge gaps, broken references,
stale locks, and workflow patterns. Write proposals to this task's blackboard.
Post a one-line summary to Slack.

See `skills/bootstrap/dream/SKILL.md` for the full instructions.
