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

Run Dream for this Relay repo: scan for knowledge gaps, broken references,
stale locks, done-ticket Retro cleanup needs, and workflow patterns. Write
worker results and proposals to this task's blackboard. Post a one-line summary
to Slack.

See the repo's Dream skill for the full instructions.
