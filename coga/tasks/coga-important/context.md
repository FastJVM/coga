---
slug: coga-important/context
title: context
status: in_progress
owner: zach
human: zach
agent: claude
assignee: codex
contexts: []
skills: []
workflow:
  name: docs/with-review
  steps:
  - name: implement
    skills: []
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills: []
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 2 (peer-review)
---

## Description

This ticket is the unit of work to build a context block that describes how we
plan to handle important notifications and who's responsible for acting on them.
It's also meant to explain how it differs from coga-flow.

The deliverable is the context block itself — the routing convention any script
can follow to raise a human-action notification. The channel already exists; its
webhook and the coga.toml recipient field are separate tickets.

## coga-important

1. `coga-important` is our Slack channel strictly for notifications that need
   human action.

2. Coga's automatic state-transition broadcasts (create / bump / mark) stay in
   coga-flow.

3. We don't want to be inundated with notifications, but we don't want anything
   to fall through the cracks.

4. Notifications land here automatically — any script that detects an
   action-needed event runs `coga slack --important` to post it to
   `coga-important` (e.g. a patent sweep posting "maintenance fee due").

5. By default every `--important` notification @'s the user set in the coga.toml
   property field — the triage owner it all lands on.

6. That user either handles it, @'s someone in the Slack thread, or opens a ticket
   if it's real work.

7. Handing off stays a plain Slack @ and gets no Coga machinery — a thread reply
   keeps the alert's context, while a second `coga slack` post would land
   disconnected from it and add the channel noise point 3 rules out.

## Context

<!-- coga:blackboard -->

## Dev

branch: important-context
worktree: ../coga-important-context
commit: 2a3d7adf

## What changed

New context `coga/important` — the ticket's seven points rewritten as domain
knowledge. Two byte-identical copies:

- `coga/contexts/coga/important/SKILL.md` (live)
- `src/coga/resources/templates/coga/bootstrap/contexts/coga/important/SKILL.md` (packaged)
- `tests/test_packaging.py` — registers the packaged copy in
  `EXPECTED_BOOTSTRAP_RESOURCES` and the pair in `IDENTICAL_LIVE_PACKAGED_PAIRS`.

The ticket body's `## coga-important` points are left untouched:
`add-toml-property-for-notification-recipient` cites "point 5" by number, so
renumbering or deleting them would break that reference.

## Decisions

Packaged, not live-only. `bootstrap/contexts/` resolves at runtime for every
repo (`paths.py:91`, local-first then bundled), so shipping it there is what
lets the patents repo — `--important`'s first consumer per
`add-coga-slack-important` — read the convention without a local copy.
`coga/sync`, the adjacent notification context, is packaged the same way and is
the precedent. The cost: this becomes shipped OS knowledge, and point 1's "*our*
Slack channel" phrasing is team-specific. Reworded as convention rather than as
this team's channel. Flagged for the owner at review; live-only is a one-line
revert of the packaged copy plus its two test entries.

Own section on the blocker boundary. A blocker needs a human but is not an
`--important` post — `coga block` posts through the normal owner path
(`commands/block.py:52-66`, no important flag). Verified in source rather than
assumed, because it is the first question a reader hits: the distinction is that
an alert has no ticket, while a blocker is already attached to one.

Separate context rather than a section in `coga/sync`. `coga/sync` is 606 lines
already, and the `_template` rule is to split at a page.

## Verification

- `python -m pytest tests/test_packaging.py tests/test_paths.py` — 10 passed.
- `coga validate --json` — no new findings (pre-existing idle-task warns only).
- Drove `resolve_context_path(cfg, 'coga/important')` with the worktree's own
  `src` on `PYTHONPATH`: resolves to the live copy, bundled twin exists for the
  no-local-copy case.
- Drove `compose_prompt` with `contexts: ['coga/important']`: the context inlines
  (14331 chars). Confirmed via the heading "The bar, and why it holds", which is
  absent from the ticket body — so the text is coming from the context file and
  not from the ticket. A naive substring probe would have passed either way.

## Notes

The context documents `coga slack --important` and
`[notification.slack].important_recipient`. Neither is on `main` yet:
`--important` is on PR #553 (`support-second-webhook`, at step 4 review) and
`important_recipient` is unimplemented in
`add-toml-property-for-notification-recipient`. This is expected — the ticket
scopes this to the convention and the webhook/recipient work to siblings — but
the context describes the intended end state, so it reads slightly ahead of main
until those two land. Worth a sequencing check at review if the merge order
matters.

## Usage

{"agent":"claude","cache_creation_input_tokens":145839,"cache_read_input_tokens":4474969,"cli":"claude","input_tokens":144,"model":"claude-opus-4-8","output_tokens":46893,"provider":"anthropic","schema":1,"session_id":"5eb690c3-4775-41e0-b737-52a5b8bf430e","slug":"coga-important/context","step":"implement","title":"context","ts":"2026-07-16T00:56:09.529638Z","usage_status":"ok"}
