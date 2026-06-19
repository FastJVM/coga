---
title: relay-ticket-creates
status: active
mode: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts: []
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

`relay ticket` is the create-or-edit authoring entry point; `relay create` is
the quick placeholder; `relay draft` is removed. `relay ticket <title>` creates
a draft and immediately runs the `bootstrap/ticket` authoring interview, which
**opens with one scripted question — "What are you trying to do, and why?" —
then is fully agent-led** (the agent draws out the rest with its own judgment;
no further scripted questions), ending in a launchable ticket. No yes/no prompt:
running `relay ticket` *is* the signal you're ready to author (for a bare stub,
use `relay create`). `relay ticket <slug>` on an
existing ticket re-enters authoring (edit).

## Context

`relay ticket <title>` already creates a draft and launches the
`bootstrap/ticket` interview (`src/relay/commands/ticket.py`), and re-running it
on an existing slug already re-enters authoring — so the create-or-edit behavior
largely exists today, with no yes/no gate (running `relay ticket` is the intent
signal). The remaining work is removing `relay draft` — a thin wrapper over
`create_task` (`src/relay/commands/create.py`, `src/relay/create.py`);
`relay create` stays as the quick stub (owner decision). nick owns these
primitives.

Bootstrap opener (nick's idea, designed 2026-06-19): the `bootstrap/ticket`
prompt opens with one scripted question — **"What are you trying to do, and
why?"** — and is agent-led from there, with no further scripted questions.
Chosen by testing three openers against a single held-constant task: the
intent+why phrasing pulled the fullest first answer (deliverable + outcomes +
quality bars + the *why*/Context) at no extra friction; plain "what do you want
done?" missed the why, and an outcome frame ("what should be true once done?")
dropped the deliverable. Deliberately one question only — the agent derives
scope/acceptance/etc. with judgment, not a scripted flow. This touches the
`bootstrap/ticket` prompt itself — cohesive with, but separable from, the
command/`relay draft` work above.

Open for the design step: whether `relay create` shares the creation code path
with `relay ticket`; the exact re-run/edit UX; and whether the `relay ticket
<slug>` edit path opens with the same question or lets the agent adapt to the
existing ticket.

