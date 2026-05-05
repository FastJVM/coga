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

Run the Dream maintenance pass for this Relay repo: scan the ticket set, run
the known maintenance skills in order, and look for knowledge gaps, broken
references, stale locks, done-ticket Retro cleanup needs, and workflow
patterns. Write skill results and proposals to this task's blackboard. Post a
one-line summary to Slack.

See the repo's `bootstrap/dream` instructions for the full process.
