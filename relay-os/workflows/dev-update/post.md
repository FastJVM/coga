---
name: dev-update/post
description: One-step workflow for the daily dev-update digest. A single agent step runs the whole digest — collect new commits on `main`, post one Slack summary, record the new high-water state — then finishes with `relay mark done`.
steps:
  - name: digest
    assignee: agent
---

## digest

Single agent step. Follow the ticket body's `## Description` end to end: read
the parent recurring task's `### Dev Update State` for the last high-water
commit, collect the new commits on `main`, post one short Slack digest (skip
the post when there are no new commits), then overwrite `### Dev Update State`
with the new high-water mark.

This workflow has exactly one step, so there is nothing to `relay bump` to —
finish the run with `relay mark done` on this task once the digest is posted
and the state is recorded. If the run is blocked, `relay panic` with a reason
instead of stopping silently.
