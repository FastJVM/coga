---
title: Detect recurring runs that mark done without advancing declared state
status: active
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

A recurring task whose body declares persistent state in the parent
recurring task's blackboard (a high-water mark, cursor, last-processed SHA,
"posted/skipped" flag) can `relay mark done` / `relay bump` to completion
*without ever writing that state back*. The run looks successful — it
finishes, it may even post its output — but the next firing reads the same
stale cursor and redoes the same range. Nothing in the current flow notices
that a declared state key didn't move.

We want Relay to detect this: a recurring run that declares persistent state
but completes without advancing it should be flagged (a warning at
`mark done`/`bump`, surfaced in `relay validate`, and/or an FYI broadcast),
not silently accepted.

### Worked example (observed 2026-06-05)

`relay-dev-update` keeps a high-water mark in
`relay-os/recurring/relay-dev-update/blackboard.md`:

    ### Dev Update State
    last_commit: <SHA>

On 2026-06-05 a debug run read `last_commit: 29dc3c1` (dated **2026-05-30**)
and summarized the full `29dc3c1..HEAD` range — 6 days, 158 commits. But
within that exact range, multiple dev-update runs had already completed:

- `relay-dev-update-2026-06-03` — done (scheduled run, 6/3)
- `relay-dev-update-dbg-20260603T161005` — done (6/3)
- `relay-dev-update-dbg-20260603T211208` — done (6/3)

Each finished cleanly, yet **none advanced `last_commit`** — it sat at the
5/30 value the whole time. The 6/5 run therefore re-summarized and re-posted
work those earlier runs had already reported (a duplicate digest). The cursor
only moved once a run happened to record it correctly; until then every
firing re-covered the same range.

### Why it's hard to catch today

- `mark done` / `bump` don't know which blackboard keys a task *promised* to
  update, so they can't tell a state-advancing finish from a no-op finish.
- A run that fails *only* at the record-state step still exits 0 and looks
  identical to a healthy run.
- The damage (stale cursor → duplicate/blank output next time) shows up a
  firing later, decoupled from the run that caused it.

### Sketch of a fix (to refine in implement)

- Let a recurring task declare the state keys it owns (the body already names
  them informally, e.g. `last_commit`). Make that contract machine-readable —
  a frontmatter field on the recurring task, or a parsed marker in its body.
- On `mark done` / final `bump` of a period task, diff the parent blackboard:
  if a declared key is unchanged from the value the run started with, warn
  (and/or broadcast an FYI) rather than silently completing.
- Optionally surface the same check in `relay validate` so a stuck cursor is
  visible without waiting for the next firing.

Decisions to settle during implement: where the declared-keys contract lives;
warn vs. hard-block on a non-advancing finish; whether "no new work this
period" (legitimately unchanged cursor) is distinguishable from "forgot to
record" — likely needs the task to explicitly record a skip rather than
leaving the key untouched.

## Context

