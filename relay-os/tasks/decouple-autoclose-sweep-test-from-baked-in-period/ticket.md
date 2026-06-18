---
title: Decouple autoclose sweep test from baked-in period date
status: draft
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
secrets: null
step: 1 (implement)
---

## Description

Found by the Dream run on 2026-06-18 (knowledge scan, gap finding G-NEW-1).

`tests/test_autoclose_sweep.py:159` asserts the committed autoclose blackboard
ends with `last_serviced_period: 2026-06-11`, but the live committed value in
`relay-os/recurring/autoclose-merged/blackboard.md` has since advanced (e.g.
`2026-06-17`). As a result `test_autoclose_live_and_packaged_copies_stay_in_sync`
and `test_autoclose_recurring_template_creates_idempotently` fail
deterministically on any run where "today" differs from the baked-in period.

This recurs: the same "2 pre-existing failures, NOT mine" was independently
re-diagnosed in at least four separate dev-task blackboards
(`1password-…`, `fail-loud-…-secret`, `first-run-works-without-slack-configured`,
`marketing/relay-build-command`), each agent burning time rediscovering it — a
recurring verification tax.

Fix direction: decouple the test from the live, mutating blackboard value —
e.g. use a fixture/temp copy, assert structure rather than a hardcoded date, or
freeze the period. Human design judgment needed on the right approach.

## Context

