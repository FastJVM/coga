---
schedule: "0 9 * * *"
schedule_comment: "Every day at 9am — daily digest of commits merged to main"
title: "Relay dev update"
# `mode: auto` is temporarily disabled (no live console output from
# headless agent runs), so this template runs in `interactive` mode and
# requires a human terminal: `relay recurring launch relay-dev-update`.
# Flip back to `mode: auto` when streaming lands.
mode: interactive
owner: nick
assignee: claude
---

## Description

Post a short daily digest of what was committed to `main` to Slack.

Each run looks at every commit merged to `main` since the previous run,
summarizes it in a few lines, and posts that summary to the team Slack
channel. The point is a low-effort daily pulse on what is shipping in Relay
that nobody has to write by hand.

This task has no workflow — this body is the whole run instruction. When the
work below is done, finish with `relay mark done` on this task. If something
blocks the run, `relay panic` with a reason instead of stopping silently.

### Step 1 — Find where the last run stopped

Read the `### Dev Update State` section of the parent recurring task's
blackboard for the `last_commit:` line (the `relay/period-task` context
covers which file that is). If it is empty — the first run — fall back to
commits from the last 24 hours (`git log --since="24 hours ago"`).

### Step 2 — Collect the new commits

From the primary checkout (kept on `main`), run `git fetch`, then
`git log <last_commit>..origin/main` — or the 24h fallback. Read the commit
subjects, and the diffstat where it helps, so the digest describes what
actually changed.

### Step 3 — Write the digest

Summarize the range in a few lines of plain prose: what shipped, grouped by
theme — not a raw commit dump. Name merged PRs by number when the commit
messages carry them. Keep it short: a handful of lines a teammate reads in
ten seconds.

If there are no new commits since the last run, skip the Slack post in
Step 4 and just record state in Step 5.

### Step 4 — Post to Slack

Post the digest to the shared channel as a single FYI broadcast:

`relay slack --task <this-task> --message "<digest>"`

One post per run. Keep it to a few lines.

### Step 5 — Record state and finish

Overwrite the `### Dev Update State` section of the parent recurring task's
blackboard with the new high-water mark:

    ### Dev Update State

    last_commit: <current origin/main HEAD SHA>
    range: <last_commit>..<new SHA> (N commits)
    posted: <yes | skipped — no new commits>

`last_commit` is what tomorrow's run reads. Then run `relay mark done` on this
period task.
