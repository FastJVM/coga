---
title: Nightly auto-drain run for ready tickets
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
  - relay/architecture
  - relay/cli
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (design)
---

## Description

Make spare overnight token budget (e.g. an unused Max allotment) useful: a
scheduled run that, at night, executes the backlog of tickets the team has
**flagged ready for autonomous execution** — running them unattended until the
budget is spent or the ready queue drains.

This is mostly an **assembly + sequencing** ticket, not new mechanism. The
pieces already exist as separate tickets; this one orders them, owns the
end-to-end "nightly drain" behavior, and avoids duplicating their scope:

- **Blocker — auto mode is disabled.** `mode: auto` currently buffers stdout
  with no live signal, so scheduled auto runs would sit silently. Depends on
  `auto/stream-agent-progress-in-auto-mode-and-recurring-launches`. Until that
  lands, the only unattended path is `mode: script`.
- **"Ready for execution" flag** — depends on
  `represent-autonomy-tier-in-ticket-mode-field` (and the shipped
  `automation-triage` tiers + `wire-autonomy-triage`) to mark which tickets are
  safe to run unattended.
- **Token budget awareness** — depends on `track-usage-of-llm` (the usage
  primitive) and `drain-pending-auto-tickets-with-leftover-session-budget`
  (the "keep launching ready tickets while budget remains" loop). This ticket
  should not redefine usage capture or the drain loop — it consumes them.
- **Scheduling** — Relay deliberately does not manage cron ("nothing runs
  unless you invoke it"). The seam is `relay-os/scripts/cron.sh`; this ticket
  documents/wires it into the user's own scheduler rather than adding a daemon.
- **Blocked behavior** — pairs with the sibling "Async park-and-continue on
  block": a blocked ticket parks cleanly and the drain moves on to the next
  ready ticket instead of stalling the night.

Deliverable: a documented nightly-drain entry point that respects the autonomy
flag, stops at the token budget, parks blockers without stalling, and surfaces
results to Slack in the morning. Keep new code thin — the heavy lifting belongs
to the dependencies above.

## Context

This ticket sits on top of several in-flight tickets; confirm their state
before starting so it doesn't duplicate or front-run them. The hard gate is
auto-mode streaming — if that hasn't shipped, scope this to `mode: script`
drains or hold. Relay's no-implicit-cron stance (see `relay/cli`,
`relay/architecture`) is intentional: the scheduling half is "wire `cron.sh`
into *your* scheduler," not "Relay starts running on a timer."
