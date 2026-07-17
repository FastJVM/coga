---
slug: marketing/launch-20-minutes-a-day
title: Launch 20 minutes a day
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
  - marketing/plan
  - marketing/positioning
skills: []
workflow: null
secrets: null
script: null
---

## Description

Run the "20 minutes a day" launch: a 2-week public experiment where megalaunch
drains the real backlog and the founder's entire human contribution is ~20
min/day, then publish the launch post built on its data.

Phases:

1. **Pre-registration (first, one commit, before any data).** Commit a short
   doc declaring: the window (starts when megalaunch holds up daily); inclusion
   rule = every task megalaunch *attempts* (intention-to-treat — completed /
   blocked / rescued / abandoned all reported); measurement = attention
   episodes from public timestamps (log.md human events + git commits filtered
   of coga auto-commits ("Sync coga state", "Log:", "Ticket:") + GitHub-side
   PR review/merge events), gap = 10 min, floor = 2 min per isolated event,
   sensitivity also reported at floor = 5 min; the task list and blocker
   answers will be published as-is.
2. **The run.** 2 weeks, megalaunch as default work mode, human work =
   answering the blocker queue + reviews, ~20 min/day. Blocker answers are the
   judgment exhibit — they're already recorded verbatim in log.md and on
   blackboards; nothing extra to capture. Daily diary is *derived* from the
   log by the metrics script, not hand-written.
3. **The post.** Title-shaped claim: "Two weeks. Twenty minutes a day. N
   shipped tasks." Contents: the morning-ritual scene (coffee → `coga status
   --blocked` → answer → sweep → close terminal); the table (task → minutes →
   artifact link where applicable → clean/needed-follow-up); the blocker-answer
   exhibit; a what-broke section; the flat-cost line (two subscriptions,
   ~$400/mo, nothing metered — reader does the division); repo link with
   "recompute it yourself" (the metrics script). Include the anchor paragraph:
   there is no such thing as "full autonomy" — autonomy is a function of spec
   quality + evaluability; the 20 min/day is the irreducible spec-and-judgment
   work no model upgrade removes; Coga is the machinery that makes 20 minutes
   of it enough.

Claim discipline (Devin-trap avoidance): descriptive claims only, no
multiplier, receipts per row, misses published, small claims. Trust comes from
recomputability (public timestamps, GitHub-held where possible), the
pre-registration being git-dated before the data, and modesty.

Depends on: megalaunch stable in daily use (proven empirically — the window
starts when it holds up daily; file narrow fix tickets as failures surface),
`metrics-human-minutes-script`.
Related: `marketing/add-killer-demo` (post/README gif),
`marketing/rewrite-readme-around-the-wedge`, `marketing/relay-discord`
(the post needs a "where to go" link).

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
