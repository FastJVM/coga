---
name: browser/build-automation
description: Router that turns a described browser task into a concrete autonomy-tier automation ticket.
steps:
  - name: understand-task
    assignee: agent
  - name: choose-approach
    assignee: agent
  - name: triage-tier
    assignee: agent
  - name: emit-and-launch
    assignee: agent
---

## understand-task

Restate the task as a concrete goal, a target (site/URL or system), and an
explicit success check — "done" = what is observably true afterward. If the task
is genuinely ambiguous, ask once; otherwise proceed.

## choose-approach

Apply `browser/api-first`: is there an API/SDK that does this without a browser?
If yes, say so and stop; this isn't a browser-automation ticket. If no or
partial, commit to DOM-backed (`browser/dom-backed`) so the emitted ticket
attaches the right context. This is a routing decision, not a deep probe; the
emitted ticket's prerequisites step does the real verification against the
target.

## triage-tier

Classify the end action's failure radius from what the task is asking for:
read-only or idempotent → `autonomy/fully-automated`; irreversible or
high-radius (send, submit, pay, post, delete) → `autonomy/human-verify`; not
machine-feasible → `autonomy/human-only`. Triage from intent, not deep
exploration; the tier confirms feasibility in its own prerequisites step.

## emit-and-launch

Scaffold a concrete automation ticket bound to the chosen `autonomy/<tier>`
workflow and write the goal / target / success-check into its body.

Attach the browser context + runner only when the agent will drive the browser:
for `autonomy/fully-automated` or `autonomy/human-verify`, attach
`browser/dom-backed` + `browser/playwright`; for `autonomy/human-only`, attach
neither because the human performs it end to end and the agent only supports
read-only. The tier workflows are domain-generic — also used for connector and
script tasks — so these browser-specific attachments are decided here, per task,
not baked into the tiers.

Then launch it. From here the tier owns the work: `prerequisites-and-handoff`
explores the target and surfaces human-only gaps (login walls, scopes, missing
inputs), `dry-run-or-downgrade` runs it repeatedly until reliable against the
real ticket, and the run / prepare-to-brink / human steps execute. The
exploration and repeated dry-run-to-reliable happen there, not here.
